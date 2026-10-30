# -*- coding: utf-8 -*-
# ==============================================================================
# v19.py
# Description: 
# ==============================================================================
import os

# 💡 CRITICAL: Lock underlying NumPy/C-library threads to prevent contention 
# when utilizing outer Python multi-processing.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import glob
import math
import gc
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.prepared import prep
from shapely.geometry import LineString, Point, box
from pyproj import Transformer
import rasterio
from rasterio.mask import mask
from rasterio.transform import rowcol, xy
from rasterio.warp import reproject, Resampling
from rasterio.merge import merge
import rasterio.features
from skimage.graph import route_through_array
from skimage.measure import label as sk_label
from shapely.ops import unary_union
import concurrent.futures

# =====================================================================
# 0. Global Configuration Console
# =====================================================================
BLOCK_ID = "06"            

# 🌟 Parameter Matrices 🌟
SCENARIO_LIST = ["ssp585"]  
MR_LIST = ["MR1"] 
CONF_LIST = ["High_Prob", "Mid_Prob", "Low_Prob"]
THRESH_LIST = [0.20, 0.15, 0.25]

# 🌟 Workspace Paths (Easily configurable for other users) 🌟
BASE_DIR = "./SLR_Project_Workspace"
INPUT_DIR = os.path.join(BASE_DIR, f"WDPA_grid4.1_block/Block_{BLOCK_ID}")
OUTPUT_ROOT = os.path.join(BASE_DIR, "PA_Results")
EXCEL_PATH = os.path.join(OUTPUT_ROOT, f"Master_Statistics_Block_{BLOCK_ID}.xlsx")

CLIMATE_DIR = os.path.join(BASE_DIR, "WorldClim")
SLR_RESULTS_DIR = os.path.join(BASE_DIR, "Upload_Blocks_Result")
ID_FIELD = "myWDPAID3"

# Global Cache for Multi-Processing memory optimization
GLOBAL_CACHE = {
    'TEMP': {},
    'TIDAL': {},
    'TRANSFORM': None,
    'CRS': None
}

# ================= 1. Dynamic Pathing & Helper Functions =================
def get_temp_paths(scenario):
    return {
        2020: os.path.join(CLIMATE_DIR, "wc2.1_30s_tavg_filled_interpolated_proj.tif"),
        2040: os.path.join(CLIMATE_DIR, f"wc2.1_30s_tavg_{scenario}_2021-2040_mean_filled_interpolated_proj_bili.tif"),
        2060: os.path.join(CLIMATE_DIR, f"wc2.1_30s_tavg_{scenario}_2041-2060_mean_filled_interpolated_proj_bili.tif"),
        2080: os.path.join(CLIMATE_DIR, f"wc2.1_30s_tavg_{scenario}_2061-2080_mean_filled_interpolated_proj_bili.tif"),
        2100: os.path.join(CLIMATE_DIR, f"wc2.1_30s_tavg_{scenario}_2081-2100_mean_filled_interpolated_proj_bili.tif")
    }

def get_cropped_array(raster_path, geometry, use_all_touched=False):
    with rasterio.open(raster_path) as src:
        out_image, out_transform = mask(src, [geometry], crop=True, filled=True, all_touched=use_all_touched)
        raw_array = out_image[0]
        float_array = raw_array.astype(np.float32)
        if src.nodata is not None:
            float_array[raw_array == src.nodata] = np.nan
        float_array[float_array < -9999] = np.nan
        return float_array, out_transform, src.crs

def get_dynamic_tidal_array(year, buffer_geom, master_transform, master_shape, master_crs, scenario, mr, conf):
    search_pattern = os.path.join(SLR_RESULTS_DIR, f"Block_{BLOCK_ID}/{scenario}_{mr}_processing_proj/{scenario}_{year}/Prob_Intertidal_*_{scenario}_{year}_{conf}_1km_Binary_proj.tif")
    tiff_list = glob.glob(search_pattern)
    if not tiff_list:
        raise ValueError(f"Tidal surface files not found: {search_pattern}")

    srcs = [rasterio.open(f) for f in tiff_list]
    try:
        source_nodata = srcs[0].nodata if srcs[0].nodata is not None else 255
        minx, miny, maxx, maxy = buffer_geom.bounds
        mosaic_data, mosaic_transform = merge(srcs, bounds=(minx, miny, maxx, maxy), nodata=source_nodata)
        
        aligned_array = np.full(master_shape, np.nan, dtype=np.float32)
        reproject(
            source=mosaic_data, destination=aligned_array,
            src_transform=mosaic_transform, src_crs=srcs[0].crs,
            dst_transform=master_transform, dst_crs=master_crs,
            resampling=Resampling.nearest, src_nodata=source_nodata,
            num_threads=10
        )
        aligned_array[aligned_array == source_nodata] = np.nan
        aligned_array[np.isnan(aligned_array)] = -1
        return aligned_array.astype(np.int8)
    finally:
        for s in srcs: s.close()

def get_cached_slice(global_array, global_transform, geom):
    from rasterio.windows import from_bounds
    window = from_bounds(*geom.bounds, transform=global_transform)
    
    row_off = max(0, math.floor(window.row_off))
    col_off = max(0, math.floor(window.col_off))
    height = math.ceil(window.height)
    width = math.ceil(window.width)

    row_end = min(global_array.shape[0], row_off + height)
    col_end = min(global_array.shape[1], col_off + width)

    sliced = global_array[row_off:row_end, col_off:col_end].copy()
    sliced_transform = rasterio.Affine(
        global_transform.a, global_transform.b, global_transform.c + col_off * global_transform.a,
        global_transform.d, global_transform.e, global_transform.f + row_off * global_transform.e
    )
    return sliced, sliced_transform

def get_polygon_mean_temp_from_cache(geom, global_array, global_transform):
    slice_arr, slice_transform = get_cached_slice(global_array, global_transform, geom)
    if slice_arr.size == 0: return np.nan
    try:
        mask_arr = rasterio.features.geometry_mask(
            [geom], out_shape=slice_arr.shape, transform=slice_transform, invert=True, all_touched=True
        )
        valid_pixels = slice_arr[mask_arr & ~np.isnan(slice_arr)]
        return np.mean(valid_pixels) if len(valid_pixels) > 0 else np.nan
    except Exception:
        return np.nan

def append_to_excel(file_path, df, sheet_name):
    if not os.path.exists(file_path):
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                if sheet_name in writer.book.sheetnames:
                    startrow = writer.book[sheet_name].max_row
                    df.to_excel(writer, sheet_name=sheet_name, startrow=startrow, index=False, header=False)
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=True)
        except PermissionError:
            print(f"\n❌ CRITICAL: Cannot append to Excel. File is currently open/locked: {file_path}")
        except Exception as e:
            print(f"\n❌ Unknown exception during Excel append: {e}\n")
            
# ================= 2. Memory Preloading & Caching Core =================
def preload_temp_data(block_bounds, scenario):
    print(f"🔥 [1/2] Building [Temperature] global cache -> Scenario: {scenario} ...")
    GLOBAL_CACHE['TEMP'].clear()
    gc.collect()
    
    temp_paths = get_temp_paths(scenario)
    expanded_geom = box(block_bounds[0]-500000, block_bounds[1]-500000, block_bounds[2]+500000, block_bounds[3]+500000)
    
    t2020, master_transform, master_crs = get_cropped_array(temp_paths[2020], expanded_geom, use_all_touched=True)
    GLOBAL_CACHE['TRANSFORM'] = master_transform
    GLOBAL_CACHE['CRS'] = master_crs
    GLOBAL_CACHE['TEMP'][2020] = t2020
    
    for year in [2040, 2060, 2080, 2100]:
        arr, _, _ = get_cropped_array(temp_paths[year], expanded_geom, use_all_touched=True)
        GLOBAL_CACHE['TEMP'][year] = arr
    
    GLOBAL_CACHE['TEMP'][2030] = (GLOBAL_CACHE['TEMP'][2020] + GLOBAL_CACHE['TEMP'][2040]) / 2.0
    GLOBAL_CACHE['TEMP'][2050] = (GLOBAL_CACHE['TEMP'][2040] + GLOBAL_CACHE['TEMP'][2060]) / 2.0
    GLOBAL_CACHE['TEMP'][2070] = (GLOBAL_CACHE['TEMP'][2060] + GLOBAL_CACHE['TEMP'][2080]) / 2.0
    GLOBAL_CACHE['TEMP'][2090] = (GLOBAL_CACHE['TEMP'][2080] + GLOBAL_CACHE['TEMP'][2100]) / 2.0
    gc.collect()

def preload_tidal_data(block_bounds, scenario, mr, conf):
    print(f"🌊 [2/2] Building [Tidal] global cache -> Strategy: {mr} | Confidence: {conf}...")
    GLOBAL_CACHE['TIDAL'].clear()
    gc.collect()
    
    expanded_geom = box(block_bounds[0]-500000, block_bounds[1]-500000, block_bounds[2]+500000, block_bounds[3]+500000)
    master_transform = GLOBAL_CACHE['TRANSFORM']
    master_crs = GLOBAL_CACHE['CRS']
    master_shape = GLOBAL_CACHE['TEMP'][2020].shape
    
    for year in range(2020, 2110, 10):
        arr = get_dynamic_tidal_array(year, expanded_geom, master_transform, master_shape, master_crs, scenario, mr, conf)
        GLOBAL_CACHE['TIDAL'][year] = arr
    gc.collect()

# ================= 3. Core Simulation Logic (Breadth-First + Strict Lock) =================
def process_single_pa(pas, final_output_name, scenario, mr, conf, thresh, dirs):
    total_participating_grids = len(pas)
    total_participating_area = float(pas['Inter_Area'].fillna(0).sum()) if 'Inter_Area' in pas.columns else 0.0

    TARGET_YEARS = [2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
    REPORT_YEARS = [2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]

    occupied_by_year = {y: set() for y in TARGET_YEARS}
    grouped_pas = pas.groupby(ID_FIELD)
    
    global_points_data, global_ranges_data = [], []
    global_unsuccessful_points_data = []
    global_paths_by_year = {y: [] for y in REPORT_YEARS}
    
    global_initial_starts = []
    global_successful_starts = []
    global_successful_starts_2040, global_successful_starts_2060, global_successful_starts_2080 = [], [], []
    global_endpoints_2040, global_endpoints_2060, global_endpoints_2080 = [], [], []
    
    grand_counts = {y: {'insitu_count': 0, 'insitu_area': 0.0, 'corridor_count': 0, 'corridor_area': 0.0, 'in_pa_count': 0, 'in_pa_area': 0.0} for y in TARGET_YEARS}
    grand_initial_no_tidal_count, grand_initial_no_tidal_area = 0, 0.0
    grand_path_lengths = []
    
    transformer = Transformer.from_crs(pas.crs, "EPSG:4326", always_xy=True)
    overall_pa_geom = pas.geometry.union_all()
    pa_lon_2020_deg, pa_lat_2020_deg = transformer.transform(overall_pa_geom.centroid.x, overall_pa_geom.centroid.y)
    pa_hemisphere = "Northern" if pa_lat_2020_deg >= 0 else "Southern"
    all_2100_endpoints = []

    print(f"    🚀 [{final_output_name}] Commencing synchronous simulation with strict locks for {total_participating_grids} grids...")
    current_grid_idx = 0 
    
    for pa_id, group in grouped_pas:
        current_grid_idx += 1
        if current_grid_idx % 200 == 0 or current_grid_idx == total_participating_grids:
            print(f"    ⏳ [{final_output_name}] Progress: {current_grid_idx} / {total_participating_grids}")
            
        original_pa_geom = group.geometry.union_all()
        prep_pa_geom = prep(original_pa_geom) 
        established_by_year = {y: [] for y in TARGET_YEARS}
        pa_end_points = []  
        counts = {y: {'corridor_count': 0, 'corridor_area': 0.0, 'in_pa_count': 0, 'in_pa_area': 0.0, 'insitu_count': 0, 'insitu_area': 0.0} for y in TARGET_YEARS}

        pa_buffer_500km = original_pa_geom.buffer(500000)
        temp_list, tidal_list = [], []
        master_transform = None
        master_shape = None
        
        local_temp_dict = {}
        local_tidal_dict = {}
        
        try:
            for y in range(2020, 2110, 10):
                t_slice, t_trans = get_cached_slice(GLOBAL_CACHE['TEMP'][y], GLOBAL_CACHE['TRANSFORM'], pa_buffer_500km)
                local_temp_dict[y] = t_slice
                temp_list.append(t_slice)
                
                tidal_slice_raw, _ = get_cached_slice(GLOBAL_CACHE['TIDAL'][y], GLOBAL_CACHE['TRANSFORM'], pa_buffer_500km)
                tidal_slice = tidal_slice_raw.astype(np.float32)
                tidal_slice[tidal_slice_raw == -1] = np.nan
                local_tidal_dict[y] = tidal_slice
                tidal_list.append(tidal_slice)
                
                if y == 2020:
                    master_transform = t_trans
                    master_shape = t_slice.shape
        except Exception:
            continue

        HIGH_PENALTY = 99999.0 

        # =====================================================================
        # [Phase 1] - Initialize all tidal patches as active Agents
        # =====================================================================
        active_patches = []
        for row in group.itertuples():
            geom = row.geometry
            start_point = geom.centroid 
            inter_area_val = getattr(row, 'Inter_Area', 0.0)
            if pd.isna(inter_area_val): inter_area_val = 0.0

            base_temp = get_polygon_mean_temp_from_cache(geom, temp_list[0], master_transform)
            if np.isnan(base_temp): continue

            start_row, start_col = rowcol(master_transform, start_point.x, start_point.y)            
            
            # Neighborhood capture for robust initialization
            if not (0 <= start_row < master_shape[0] and 0 <= start_col < master_shape[1]) or tidal_list[0][start_row, start_col] != 1:
                y_range = np.arange(max(0, start_row-1), min(master_shape[0], start_row+2))
                x_range = np.arange(max(0, start_col-1), min(master_shape[1], start_col+2))
                found = False
                for r in y_range:
                    for c in x_range:
                        if tidal_list[0][r, c] == 1:
                            start_row, start_col = r, c
                            found = True
                            break
                    if found: break
                if not found:
                    grand_initial_no_tidal_count += 1
                    grand_initial_no_tidal_area += inter_area_val
                    continue
                    
            start_tx, start_ty = xy(master_transform, start_row, start_col)
            actual_start_pt = Point(start_tx, start_ty)
            global_initial_starts.append({ID_FIELD: pa_id, 'geometry': actual_start_pt})
            
            active_patches.append({
                'pa_id': pa_id,
                'inter_area_val': inter_area_val,
                'start_row': start_row,
                'start_col': start_col,
                'current_r': start_row,
                'current_c': start_col,
                'actual_start_pt': actual_start_pt,
                'is_dead': False,
                'death_year': 9999,
                'trajectory': [(start_row, start_col)]
            })

        # =====================================================================
        # [Phase 2] - Breadth-First: Synchronous advancement through time
        # =====================================================================
        for y in TARGET_YEARS:
            y_prev = y - 10
            temp_Y = local_temp_dict[y]
            tidal_Y = local_tidal_dict[y]
            temp_Y_prev = local_temp_dict[y_prev]

            for patch in active_patches:
                if patch['is_dead']: continue
                
                current_r, current_c = patch['current_r'], patch['current_c']
                curr_node_temp = temp_Y[current_r, current_c]
                prev_node_temp = temp_Y_prev[current_r, current_c]
                is_tidal_now = tidal_Y[current_r, current_c] == 1
                
                can_stay = False
                if is_tidal_now and not np.isnan(curr_node_temp) and not np.isnan(prev_node_temp):
                    if abs(curr_node_temp - prev_node_temp) <= thresh: 
                        can_stay = True
                
                stay_successful = False
                if can_stay:
                    tx, ty = xy(master_transform, current_r, current_c)
                    global_cell_id = rowcol(GLOBAL_CACHE['TRANSFORM'], tx, ty)
                    
                    if global_cell_id not in occupied_by_year[y]:
                        occupied_by_year[y].add(global_cell_id) 
                        established_by_year[y].append((current_r, current_c))
                        
                        if current_r == patch['start_row'] and current_c == patch['start_col']:
                            counts[y]['insitu_count'] += 1
                            counts[y]['insitu_area'] += patch['inter_area_val']
                        else:
                            counts[y]['corridor_count'] += 1
                            counts[y]['corridor_area'] += patch['inter_area_val']
                            if prep_pa_geom.intersects(Point(tx, ty)):
                                counts[y]['in_pa_count'] += 1
                                counts[y]['in_pa_area'] += patch['inter_area_val']
                        
                        if y in REPORT_YEARS:
                            path_coords = [xy(master_transform, r, c) for r, c in patch['trajectory']]
                            if len(path_coords) > 1:
                                global_paths_by_year[y].append({ID_FIELD: patch['pa_id'], 'geometry': LineString(path_coords)})

                        if y == 2040: global_endpoints_2040.append({ID_FIELD: patch['pa_id'], 'geometry': Point(tx, ty)})
                        elif y == 2060: global_endpoints_2060.append({ID_FIELD: patch['pa_id'], 'geometry': Point(tx, ty)})
                        elif y == 2080: global_endpoints_2080.append({ID_FIELD: patch['pa_id'], 'geometry': Point(tx, ty)})
                                
                        if y == 2100: 
                            pa_end_points.append(Point(tx, ty))
                            path_coords = [xy(master_transform, r, c) for r, c in patch['trajectory']]
                            grand_path_lengths.append(LineString(path_coords).length / 1000.0 if len(path_coords) > 1 else 0.0)
                        
                        stay_successful = True
                        
                if stay_successful:
                    continue

                # ----------------------- [Search for Refugia] -----------------------
                ref_temp = prev_node_temp  
                target_condition = (np.abs(temp_Y - ref_temp) <= thresh) & (tidal_Y == 1) 
                
                target_rows, target_cols = np.where(target_condition)
                
                target_found = False
                target_rc = None

                if len(target_rows) > 0:
                    dist_to_current = (target_rows - current_r)**2 + (target_cols - current_c)**2

                    est_list = established_by_year[y]
                    if len(est_list) > 0:
                        est_arr = np.array(est_list)
                        dist_to_colony_edge = np.min((target_rows[:, None] - est_arr[:, 0])**2 + (target_cols[:, None] - est_arr[:, 1])**2, axis=1)
                        colony_center_r, colony_center_c = np.mean(est_arr[:, 0]), np.mean(est_arr[:, 1])
                        dist_to_colony_center = (target_rows - colony_center_r)**2 + (target_cols - colony_center_c)**2
                        colony_cohesion_dist = dist_to_colony_edge + dist_to_colony_center
                    else:
                        colony_cohesion_dist = np.zeros_like(dist_to_current)

                    def normalize_array(arr):
                        arr_min, arr_max = np.min(arr), np.max(arr)
                        if arr_max == arr_min: return np.zeros_like(arr, dtype=np.float32)
                        return (arr - arr_min) / (arr_max - arr_min + 1e-6)
                    
                    dist_norm = normalize_array(dist_to_current)
                    cohesion_norm = normalize_array(colony_cohesion_dist)

                    final_scores = (0.1 * dist_norm) + (0.9 * cohesion_norm)
                    sorted_indices = np.argsort(final_scores)
                    sorted_target_rows, sorted_target_cols = target_rows[sorted_indices], target_cols[sorted_indices]
                    
                    for r, c in zip(sorted_target_rows, sorted_target_cols):
                        tx, ty = xy(master_transform, r, c)
                        global_cell_id = rowcol(GLOBAL_CACHE['TRANSFORM'], tx, ty)
                        
                        if global_cell_id not in occupied_by_year[y]:
                            occupied_by_year[y].add(global_cell_id) 
                            target_rc = (r, c)
                            target_found = True
                            break 
                        
                if not target_found: 
                    patch['is_dead'] = True
                    patch['death_year'] = y  
                    continue
                
                try:
                    current_t_idx = int((y - 2020) / 10)
                    PAD = 60 
                    r_start = max(0, min(current_r, target_rc[0]) - PAD)
                    r_end = min(master_shape[0], max(current_r, target_rc[0]) + PAD + 1)
                    c_start = max(0, min(current_c, target_rc[1]) - PAD)
                    c_end = min(master_shape[1], max(current_c, target_rc[1]) + PAD + 1)
                                                                                                                                                
                    multiplier = 1.0 / thresh 
                    
                    local_temp = temp_list[current_t_idx][r_start:r_end, c_start:c_end]
                    local_tidal = tidal_list[current_t_idx][r_start:r_end, c_start:c_end]
                    cost = (np.abs(local_temp - prev_node_temp) * multiplier) + 1.0
                    local_cost_surface = np.where((local_tidal == 1) & (~np.isnan(local_temp)), cost, HIGH_PENALTY)                        
                    
                    local_curr = (current_r - r_start, current_c - c_start)
                    local_target = (target_rc[0] - r_start, target_rc[1] - c_start)
                    
                    local_indices, weight = route_through_array(local_cost_surface, local_curr, local_target, fully_connected=True)
                    
                    if int(weight / HIGH_PENALTY) > 1: 
                        patch['is_dead'] = True
                        patch['death_year'] = y  
                        occupied_by_year[y].remove(global_cell_id) 
                        continue
                    
                    patch['current_r'], patch['current_c'] = target_rc
                    patch['trajectory'].extend([(r + r_start, c + c_start) for r, c in local_indices[1:]])
                    established_by_year[y].append(target_rc)
                    
                    counts[y]['corridor_count'] += 1
                    counts[y]['corridor_area'] += patch['inter_area_val']
                    
                    tx, ty = xy(master_transform, target_rc[0], target_rc[1])
                    if prep_pa_geom.intersects(Point(tx, ty)):
                        counts[y]['in_pa_count'] += 1
                        counts[y]['in_pa_area'] += patch['inter_area_val']
                        
                    if y in REPORT_YEARS:
                        path_coords = [xy(master_transform, r, c) for r, c in patch['trajectory']]
                        if len(path_coords) > 1:
                            global_paths_by_year[y].append({ID_FIELD: patch['pa_id'], 'geometry': LineString(path_coords)})
                            
                    if y == 2040: global_endpoints_2040.append({ID_FIELD: patch['pa_id'], 'geometry': Point(tx, ty)})
                    elif y == 2060: global_endpoints_2060.append({ID_FIELD: patch['pa_id'], 'geometry': Point(tx, ty)})
                    elif y == 2080: global_endpoints_2080.append({ID_FIELD: patch['pa_id'], 'geometry': Point(tx, ty)})
                        
                    if y == 2100: 
                        pa_end_points.append(Point(tx, ty))
                        path_coords = [xy(master_transform, r, c) for r, c in patch['trajectory']]
                        grand_path_lengths.append(LineString(path_coords).length / 1000.0 if len(path_coords) > 1 else 0.0)
                
                except Exception: 
                    patch['is_dead'] = True
                    patch['death_year'] = y  
                    continue                

        # =====================================================================
        # [Phase 3] - Final State Archiving
        # =====================================================================
        for patch in active_patches:
            if patch['is_dead']:
                tx, ty = xy(master_transform, patch['current_r'], patch['current_c'])
                global_unsuccessful_points_data.append({ID_FIELD: patch['pa_id'], 'geometry': Point(tx, ty)})
            else:
                global_successful_starts.append({ID_FIELD: patch['pa_id'], 'geometry': patch['actual_start_pt']})

            if patch['death_year'] > 2040: global_successful_starts_2040.append({ID_FIELD: patch['pa_id'], 'geometry': patch['actual_start_pt']})
            if patch['death_year'] > 2060: global_successful_starts_2060.append({ID_FIELD: patch['pa_id'], 'geometry': patch['actual_start_pt']})
            if patch['death_year'] > 2080: global_successful_starts_2080.append({ID_FIELD: patch['pa_id'], 'geometry': patch['actual_start_pt']})

        all_2100_endpoints.extend(pa_end_points)

        for y in TARGET_YEARS:
            grand_counts[y]['insitu_count'] += counts[y]['insitu_count']
            grand_counts[y]['insitu_area'] += counts[y]['insitu_area']
            grand_counts[y]['corridor_count'] += counts[y]['corridor_count']
            grand_counts[y]['corridor_area'] += counts[y]['corridor_area']
            grand_counts[y]['in_pa_count'] += counts[y]['in_pa_count']
            grand_counts[y]['in_pa_area'] += counts[y]['in_pa_area']

        for pt in pa_end_points:
            global_points_data.append({ID_FIELD: pa_id, 'geometry': pt})
            
        if pa_end_points:
            merged_end_points = unary_union(pa_end_points)
            grid_squares = merged_end_points.buffer(500, cap_style=3)
            tight_envelope = grid_squares.buffer(1200, join_style=1).buffer(-1200, join_style=1)
            final_envelope = tight_envelope.difference(original_pa_geom)
            if not final_envelope.is_empty:
                if final_envelope.geom_type == 'GeometryCollection':
                    polys = [g for g in final_envelope.geoms if g.geom_type in ['Polygon', 'MultiPolygon']]
                    final_envelope = unary_union(polys) if polys else None
                if final_envelope and not final_envelope.is_empty:
                    global_ranges_data.append({ID_FIELD: pa_id, 'geometry': final_envelope})

    pa_lat_2100_deg = np.nan
    migration_angle, migration_distance_km, lat_diff, avg_path_length_km = np.nan, np.nan, np.nan, np.nan

    if all_2100_endpoints:
        merged_all_endpoints = unary_union(all_2100_endpoints)
        end_centroid = merged_all_endpoints.centroid
        pa_lon_2100_proj, pa_lat_2100_proj = end_centroid.x, end_centroid.y
        pa_lon_2100_deg, pa_lat_2100_deg = transformer.transform(pa_lon_2100_proj, pa_lat_2100_proj)
        lat_diff = pa_lat_2100_deg - pa_lat_2020_deg
        dx, dy = pa_lon_2100_proj - overall_pa_geom.centroid.x, pa_lat_2100_proj - overall_pa_geom.centroid.y
        migration_distance_km = math.sqrt(dx**2 + dy**2) / 1000.0
        if dx != 0 or dy != 0:
            angle_deg = math.degrees(math.atan2(dx, dy))
            migration_angle = angle_deg if angle_deg >= 0 else angle_deg + 360.0
            
    if grand_path_lengths:
        avg_path_length_km = np.mean(grand_path_lengths)

    actual_tidal_count = total_participating_grids - grand_initial_no_tidal_count
    actual_tidal_area = total_participating_area - grand_initial_no_tidal_area

    # Apply strictly translated English column names (excluding failure metrics) 
    # but keeping 'NoAction_2100_Temp_Rise_deg'
    summary_dict = {
        'Sce': [scenario], 'MR': [mr], 'Conf': [conf], 'Blk': [BLOCK_ID], 'Thresh': [thresh], 
        'PA_Name': [final_output_name], 
        'Total_Grids': [total_participating_grids], 
        'Total_Area': [total_participating_area],
        'No_Init_Tidal_Grids': [grand_initial_no_tidal_count], 
        'No_Init_Tidal_Area': [grand_initial_no_tidal_area],
        'Actual_Tidal_Grids': [actual_tidal_count], 
        'Actual_Tidal_Area': [actual_tidal_area],
        'Hemisphere': [pa_hemisphere],
        'Center_Lon_2020': [round(pa_lon_2020_deg, 4)], 
        'Center_Lat_2020': [round(pa_lat_2020_deg, 4)],
        'Center_Lat_2100': [round(pa_lat_2100_deg, 4) if not np.isnan(pa_lat_2100_deg) else None],
        'Lat_Difference': [round(lat_diff, 4) if not np.isnan(lat_diff) else None],
        'Migration_Angle_deg': [round(migration_angle, 2) if not np.isnan(migration_angle) else None],
        'Centroid_Move_Dist_km': [round(migration_distance_km, 2) if not np.isnan(migration_distance_km) else None],
        'Avg_Path_Length_km': [round(avg_path_length_km, 2) if not np.isnan(avg_path_length_km) else None]
    }
    
    for y in REPORT_YEARS:
        summary_dict[f'InSitu_Count_{y}'] = [grand_counts[y]['insitu_count']]
        summary_dict[f'InSitu_Area_{y}'] = [grand_counts[y]['insitu_area']]
        summary_dict[f'Corridor_Count_{y}'] = [grand_counts[y]['corridor_count']]
        summary_dict[f'Corridor_Area_{y}'] = [grand_counts[y]['corridor_area']]
        summary_dict[f'InPA_Count_{y}'] = [grand_counts[y]['in_pa_count']]
        summary_dict[f'InPA_Area_{y}'] = [grand_counts[y]['in_pa_area']]
        
    summary_dict['NoAction_2100_Temp_Rise_deg'] = [None]

    col_order = ['Sce', 'MR', 'Conf', 'Blk', 'Thresh', 'PA_Name', 'Total_Grids', 'Total_Area',
                 'No_Init_Tidal_Grids', 'No_Init_Tidal_Area', 'Actual_Tidal_Grids', 'Actual_Tidal_Area',
                 'Hemisphere','Center_Lon_2020', 'Center_Lat_2020', 'Center_Lat_2100', 'Lat_Difference', 
                 'Migration_Angle_deg', 'Centroid_Move_Dist_km', 'Avg_Path_Length_km']
                 
    for y in REPORT_YEARS:
        col_order.extend([f'InSitu_Count_{y}', f'InSitu_Area_{y}', f'Corridor_Count_{y}', 
                          f'Corridor_Area_{y}', f'InPA_Count_{y}', f'InPA_Area_{y}'])
                          
    col_order.append('NoAction_2100_Temp_Rise_deg')
    
    summary_df = pd.DataFrame(summary_dict)[col_order]
    
    base_name = f"{final_output_name}_{scenario}_{mr}_{conf}_T{thresh}"
    if global_points_data:
        gpd.GeoDataFrame(global_points_data, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}.shp"))
    if global_unsuccessful_points_data:
        gpd.GeoDataFrame(global_unsuccessful_points_data, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_unsuccessful.shp"))
    if global_initial_starts:
        gpd.GeoDataFrame(global_initial_starts, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_InitialTidalPts.shp")) 
    if global_successful_starts:
        gpd.GeoDataFrame(global_successful_starts, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_SuccessfulStartPts.shp"))
    if global_ranges_data:
        env_gdf = gpd.GeoDataFrame(global_ranges_data, crs=pas.crs)
        env_gdf['geom_wkt'] = env_gdf.geometry.apply(lambda g: g.wkt)
        env_gdf.drop_duplicates(subset=['geom_wkt']).drop(columns=['geom_wkt']).to_file(os.path.join(dirs['RANGE'], f"{base_name}.shp"))
    
    for y in REPORT_YEARS:
        if global_paths_by_year[y]:
            out_p = dirs['OUTPUT'] if y == 2100 else dirs['INTERMEDIATE']
            gpd.GeoDataFrame(global_paths_by_year[y], crs=pas.crs).to_file(os.path.join(out_p, f"{base_name}_paths_{y}.shp"))

    if global_successful_starts_2040:
        gpd.GeoDataFrame(global_successful_starts_2040, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_SuccessfulStartPts_2040.shp"))
    if global_successful_starts_2060:
        gpd.GeoDataFrame(global_successful_starts_2060, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_SuccessfulStartPts_2060.shp"))
    if global_successful_starts_2080:
        gpd.GeoDataFrame(global_successful_starts_2080, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_SuccessfulStartPts_2080.shp"))        
    if global_endpoints_2040:
        gpd.GeoDataFrame(global_endpoints_2040, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_Endpoints_2040.shp"))
    if global_endpoints_2060:
        gpd.GeoDataFrame(global_endpoints_2060, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_Endpoints_2060.shp"))
    if global_endpoints_2080:
        gpd.GeoDataFrame(global_endpoints_2080, crs=pas.crs).to_file(os.path.join(dirs['PT'], f"{base_name}_Endpoints_2080.shp"))
    
    return summary_df

# ================= 4. Task Dispatcher & Processing Driver =================
def worker_task(shp_path, block_bounds, sce, mr, conf, thresh, dirs):
    final_output_name = os.path.splitext(os.path.basename(shp_path))[0]
    print(f"  -> [Task Dispatch] Processing PA: {final_output_name}")
    try:
        pas = gpd.read_file(shp_path)
        if pas.empty: return None
        minx, miny, maxx, maxy = pas.total_bounds
        if (maxx < block_bounds[0] or minx > block_bounds[2] or maxy < block_bounds[1] or miny > block_bounds[3]):
            return None
        
        result = process_single_pa(pas, final_output_name, sce, mr, conf, thresh, dirs)
        
        print(f"✅✅✅ [{final_output_name}] Successfully completed!")
        return result

    except Exception as e:
        print(f"❌ Computation error for PA {final_output_name}: {e}")
        return None

def main():
    print(f"======== 🚀 Launching High-Performance Batch Engine | Block {BLOCK_ID} ========")
    shp_files = glob.glob(os.path.join(INPUT_DIR, "*.shp"))
    if not shp_files: 
        print(f"No PA shapefiles found in input directory: {INPUT_DIR}")
        return
    
    shp_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    
    MAX_WORKERS = 25 
    print(f"⚙️ Multi-processing enabled. Allocated CPU Cores: {MAX_WORKERS}")
    
    sample_sce = SCENARIO_LIST[0]
    sample_mr = MR_LIST[0]
    sample_conf = CONF_LIST[0]
    
    search_pattern_2020 = os.path.join(SLR_RESULTS_DIR, f"Block_{BLOCK_ID}/{sample_sce}_{sample_mr}_processing_proj/{sample_sce}_2020/Prob_Intertidal_*_{sample_sce}_2020_{sample_conf}_1km_Binary_proj.tif")
    block_tiffs = glob.glob(search_pattern_2020)
    if not block_tiffs: 
        print(f"Reference base tidal rasters not found. Unable to calculate block boundaries.\nCheck path: {search_pattern_2020}")
        return

    block_bounds = None
    for f in block_tiffs:
        with rasterio.open(f) as src:
            if block_bounds is None: block_bounds = list(src.bounds)
            else:
                block_bounds[0] = min(block_bounds[0], src.bounds.left)
                block_bounds[1] = min(block_bounds[1], src.bounds.bottom)
                block_bounds[2] = max(block_bounds[2], src.bounds.right)
                block_bounds[3] = max(block_bounds[3], src.bounds.top)

    for sce in SCENARIO_LIST:
        preload_temp_data(block_bounds, sce)
        
        for mr in MR_LIST:
            for conf in CONF_LIST:
                preload_tidal_data(block_bounds, sce, mr, conf)

                for thresh in THRESH_LIST:
                    
                    base_out = os.path.join(OUTPUT_ROOT, sce, mr, f"{conf}_T{thresh}", f"Block_{BLOCK_ID}")
                    dirs = {
                        'OUTPUT': os.path.join(base_out, "Output_paths"),
                        'PT': os.path.join(base_out, "Output_ranges_pt"),
                        'RANGE': os.path.join(base_out, "Output_ranges"),
                        'INTERMEDIATE': os.path.join(base_out, "Output_paths_Intermediatefile")
                    }
                    for d in dirs.values():
                        os.makedirs(d, exist_ok=True)

                    print(f"\n>>>> Executing | Scenario: {sce} | Strategy: {mr} | Confidence: {conf} | Threshold: {thresh} <<<<")
                    
                    all_summaries = []

                    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        
                        futures = [
                            executor.submit(worker_task, shp, block_bounds, sce, mr, conf, thresh, dirs) 
                            for shp in shp_files
                        ]
                        
                        for future in concurrent.futures.as_completed(futures):
                            result = future.result()
                            if result is not None:
                                all_summaries.append(result)

                    if all_summaries:
                        final_summary_df = pd.concat(all_summaries, ignore_index=True)
                        append_to_excel(EXCEL_PATH, final_summary_df, sheet_name="Sheet1_Summary")
                        print(f"✅ Results for {sce}-{mr}-{conf}-T{thresh} successfully appended to Excel!")

if __name__ == "__main__":
    main()
