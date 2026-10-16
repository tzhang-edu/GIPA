# -*- coding: utf-8 -*-
# ==============================================================================
# SLRprediction_Baseline_Extraction.py
# 
# Architecture: Linux Server Adapted - Baseline High-Speed Refactored Version 
# Description: 10-year dynamic temperature judgment & SHP full-matrix dynamic distribution
# ==============================================================================
import os

# 💡 CRITICAL: Lock underlying NumPy threads for stable multi-processing
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
from shapely.geometry import Point, box
from pyproj import Transformer
import rasterio
from rasterio.mask import mask
from rasterio.transform import rowcol, xy
from rasterio.warp import reproject, Resampling
from rasterio.merge import merge
import concurrent.futures
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

# =====================================================================
# 0. Ultimate Batch Processing Console
# =====================================================================
# Note: The globe is divided into 18 blocks (120°x120° each).
BLOCK_ID = "02"              

SCENARIO_LIST = ["ssp126", "ssp245", "ssp370", "ssp585"]
CONF_LIST = ["High_Prob", "Mid_Prob", "Low_Prob"]
MR_LIST = ["MR0"]
THRESH_LIST = [0.20, 0.15, 0.25]
REPORT_YEARS = [2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]

# 🌟 Dynamic Path Configurations 🌟
BASE_WORKSPACE = "./"  # Change this to your root working directory (e.g., "/home/zhangting/SLR")
INPUT_DIR = os.path.join(BASE_WORKSPACE, f"WDPA_grid4.1_block/Block_{BLOCK_ID}")
EXCEL_PATH = os.path.join(BASE_WORKSPACE, f"PA_Results/Baseline_Statistics_Block_{BLOCK_ID}.xlsx")
ID_FIELD = "myWDPAID3"
MAX_WORKERS = 20  

# 🌟 NEW: SHP Full Export Settings
EXPORT_SHP_SETTINGS = {
    'ENABLE': True,               # If True, exports all processed SHP matrix combinations unconditionally
    'BASE_OUT_DIR': os.path.join(BASE_WORKSPACE, "PA_Results_Baseline") # Base directory for exports
}

GLOBAL_CACHE = {
    'TEMP': {},
    'TIDAL': {},
    'TRANSFORM': None,
    'CRS': None
}

# ================= 1. Dynamic Paths & Helper Functions =================

def get_temp_paths(scenario):
    return {
        2020: os.path.join(BASE_WORKSPACE, "WorldClim/wc2.1_30s_tavg_filled_interpolated_proj.tif"),
        2040: os.path.join(BASE_WORKSPACE, f"WorldClim/wc2.1_30s_tavg_{scenario}_2021-2040_mean_filled_interpolated_proj_bili.tif"),
        2060: os.path.join(BASE_WORKSPACE, f"WorldClim/wc2.1_30s_tavg_{scenario}_2041-2060_mean_filled_interpolated_proj_bili.tif"),
        2080: os.path.join(BASE_WORKSPACE, f"WorldClim/wc2.1_30s_tavg_{scenario}_2061-2080_mean_filled_interpolated_proj_bili.tif"),
        2100: os.path.join(BASE_WORKSPACE, f"WorldClim/wc2.1_30s_tavg_{scenario}_2081-2100_mean_filled_interpolated_proj_bili.tif")
    }

def get_cropped_array(raster_path, geometry, use_all_touched=False):
    with rasterio.open(raster_path) as src:
        out_image, out_transform = mask(src, [geometry], crop=True, filled=True, all_touched=use_all_touched)
        
        if out_image.shape[0] == 12:
            valid_mask = out_image > -9990
            out_nan = np.where(valid_mask, out_image, np.nan)
            raw_array = np.nanmean(out_nan, axis=0)
        else:
            raw_array = out_image[0]
            
        float_array = raw_array.astype(np.float32)
        if src.nodata is not None:
            float_array[raw_array == src.nodata] = np.nan
        float_array[float_array < -9999] = np.nan
        return float_array, out_transform, src.crs

def get_dynamic_tidal_array(year, buffer_geom, master_transform, master_shape, master_crs, scenario, mr, conf):
    base_dir = os.path.join(BASE_WORKSPACE, f"Upload_Blocks_Result/Block_{BLOCK_ID}")
    pattern_proj = os.path.join(base_dir, f"{scenario}_{mr}_processing_proj/{scenario}_{year}/Prob_Intertidal_*_{scenario}_{year}_{conf}_1km_Binary_proj.tif")
    pattern_noproj = os.path.join(base_dir, f"{scenario}_{mr}/{scenario}_{year}/Prob_Intertidal_*_{scenario}_{year}_{conf}_1km_Binary_proj.tif")
    
    tiff_list = glob.glob(pattern_proj)
    if not tiff_list:
        tiff_list = glob.glob(pattern_noproj)
        
    if not tiff_list:
        raise ValueError(f"Cannot find tidal data. Attempted paths:\n1. {pattern_proj}\n2. {pattern_noproj}")

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

# ================= 2. Global Memory Cache Management =================

def preload_temp_data(block_bounds, scenario):
    print(f"🔥 [1/2] Building [All-Year Temperature] cache -> Climate Scenario: {scenario} ...")
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

def preload_tidal_data(block_bounds, scenario, conf):
    print(f"🌊 [2/2] Building [Tidal] cache (Baseline MR0) -> Confidence: {conf}...")
    GLOBAL_CACHE['TIDAL'].clear()
    gc.collect()
    
    expanded_geom = box(block_bounds[0]-500000, block_bounds[1]-500000, block_bounds[2]+500000, block_bounds[3]+500000)
    master_transform = GLOBAL_CACHE['TRANSFORM']
    master_crs = GLOBAL_CACHE['CRS']
    master_shape = GLOBAL_CACHE['TEMP'][2020].shape
    
    for year in range(2020, 2110, 10):
        arr = get_dynamic_tidal_array(year, expanded_geom, master_transform, master_shape, master_crs, scenario, "MR0", conf)
        GLOBAL_CACHE['TIDAL'][year] = arr
    gc.collect()

# ================= 3. Core Computation Engine =================
def worker_task(shp_path, block_bounds, sce, conf):
    pa_name = os.path.splitext(os.path.basename(shp_path))[0]
    print(f"  -> [Process Allocation] Extracting baseline for: {pa_name}")
    try:
        pas = gpd.read_file(shp_path)
        if pas.empty: return []
        minx, miny, maxx, maxy = pas.total_bounds
        if (maxx < block_bounds[0] or minx > block_bounds[2] or maxy < block_bounds[1] or miny > block_bounds[3]):
            return []

        total_participating_grids = len(pas)
        total_participating_area = float(pas['Inter_Area'].fillna(0).sum()) if 'Inter_Area' in pas.columns else 0.0

        transformer = Transformer.from_crs(pas.crs, "EPSG:4326", always_xy=True)
        overall_pa_geom = pas.geometry.union_all()
        pa_lon_2020_deg, pa_lat_2020_deg = transformer.transform(overall_pa_geom.centroid.x, overall_pa_geom.centroid.y)
        pa_hemisphere = "Northern" if pa_lat_2020_deg >= 0 else "Southern"
        
        pa_buffer = overall_pa_geom.buffer(50000) 
        
        local_temp_dict = {}
        t_trans, master_shape = None, None
        for y in range(2020, 2110, 10):
            t_slice, current_trans = get_cached_slice(GLOBAL_CACHE['TEMP'][y], GLOBAL_CACHE['TRANSFORM'], pa_buffer)
            local_temp_dict[y] = t_slice
            if y == 2020:
                t_trans = current_trans
                master_shape = t_slice.shape
                
        local_tidal_dict = {}
        for y in range(2020, 2110, 10):
            tidal_raw, _ = get_cached_slice(GLOBAL_CACHE['TIDAL'][y], GLOBAL_CACHE['TRANSFORM'], pa_buffer)
            local_tidal_dict[y] = tidal_raw

        grand_initial_no_tidal_count, grand_initial_no_tidal_area = 0, 0.0
        grand_noaction_temp_diff_sum, grand_noaction_temp_diff_count = 0.0, 0
        grand_pure_physical_insitu_2100_count = 0
        grand_pure_physical_insitu_2100_area = 0.0
        grand_counts = {t: {y: {'insitu_count': 0, 'insitu_area': 0.0} for y in REPORT_YEARS} for t in THRESH_LIST}

        # 🌟 MODIFICATION: Unconditional geometry collection if export is enabled
        need_export_shp = EXPORT_SHP_SETTINGS['ENABLE']
        
        if need_export_shp:
            initial_geoms = [] 
            surviving_geoms = {t: {y: [] for y in REPORT_YEARS} for t in THRESH_LIST} 

        for row in pas.itertuples():
            geom = row.geometry
            start_point = geom.centroid
            inter_area_val = getattr(row, 'Inter_Area', 0.0)
            if pd.isna(inter_area_val): inter_area_val = 0.0
            
            start_row, start_col = rowcol(t_trans, start_point.x, start_point.y)
            
            # 3x3 neighborhood capture for leak prevention
            if not (0 <= start_row < master_shape[0] and 0 <= start_col < master_shape[1]) or local_tidal_dict[2020][start_row, start_col] != 1:
                y_range = np.arange(max(0, start_row-1), min(master_shape[0], start_row+2))
                x_range = np.arange(max(0, start_col-1), min(master_shape[1], start_col+2))
                found = False
                for r in y_range:
                    for c in x_range:
                        if local_tidal_dict[2020][r, c] == 1:
                            start_row, start_col = r, c
                            found = True
                            break
                    if found: break
                if not found:
                    grand_initial_no_tidal_count += 1
                    grand_initial_no_tidal_area += inter_area_val
                    continue
            
            # Reaching here means the grid has initial tidal flats
            if need_export_shp:
                initial_geoms.append(geom)
                    
            # Calculate total in-situ temperature difference for the grid
            t20 = local_temp_dict[2020][start_row, start_col]
            t21 = local_temp_dict[2100][start_row, start_col]
            if not np.isnan(t20) and not np.isnan(t21):
                grand_noaction_temp_diff_sum += (t21 - t20)
                grand_noaction_temp_diff_count += 1
                
            # A. Calculate pure physical survival status
            is_physically_dead = False
            for y in REPORT_YEARS:
                if local_tidal_dict[y][start_row, start_col] != 1:
                    is_physically_dead = True
                    break
            if not is_physically_dead:
                grand_pure_physical_insitu_2100_count += 1
                grand_pure_physical_insitu_2100_area += inter_area_val

            # B. Comprehensive (Physical + Temperature Threshold) 10-year dynamic check
            is_dead_dict = {t: False for t in THRESH_LIST}
            for y in REPORT_YEARS:
                y_prev = y - 10
                curr_temp = local_temp_dict[y][start_row, start_col]
                prev_temp = local_temp_dict[y_prev][start_row, start_col]
                is_tidal_now = local_tidal_dict[y][start_row, start_col] == 1
                
                for t in THRESH_LIST:
                    if is_dead_dict[t]: 
                        continue  
                    
                    if not is_tidal_now or np.isnan(curr_temp) or np.isnan(prev_temp):
                        is_dead_dict[t] = True
                    elif abs(curr_temp - prev_temp) > t:
                        is_dead_dict[t] = True
                        
                    if not is_dead_dict[t]:
                        grand_counts[t][y]['insitu_count'] += 1
                        grand_counts[t][y]['insitu_area'] += inter_area_val
                        
                        if need_export_shp:
                            surviving_geoms[t][y].append(geom)

        # =========================================================
        # 🌟 CORE ADDITION: Dynamically generate subfolders and pack SHP files
        # =========================================================
        if need_export_shp:
            base_out = EXPORT_SHP_SETTINGS['BASE_OUT_DIR']
            
            for t in THRESH_LIST:
                t_str = f"T{t}"
                
                # Dynamic path mapping: /Base_Dir/ssp245/Baseline/Mid_Prob_T0.20
                dynamic_out_dir = os.path.join(base_out, sce, "Baseline", f"{conf}_{t_str}")
                os.makedirs(dynamic_out_dir, exist_ok=True)
                
                # 1. Export InitialTidalPts
                if initial_geoms:
                    gdf_init = gpd.GeoDataFrame(geometry=initial_geoms, crs=pas.crs)
                    init_name = f"{pa_name}_{sce}_baseline_{conf}_{t_str}_InitialTidalPts.shp"
                    gdf_init.to_file(os.path.join(dynamic_out_dir, init_name))
                
                # 2. Export Endpoints for each decade
                for y in REPORT_YEARS:
                    pts = surviving_geoms[t][y]
                    if pts:
                        gdf_y = gpd.GeoDataFrame(geometry=pts, crs=pas.crs)
                        y_name = f"{pa_name}_{sce}_baseline_{conf}_{t_str}_Endpoints_{y}.shp"
                        gdf_y.to_file(os.path.join(dynamic_out_dir, y_name))
        
        # ------------------------ Aggregation & Writing ------------------------
        actual_tidal_count = total_participating_grids - grand_initial_no_tidal_count
        actual_tidal_area = total_participating_area - grand_initial_no_tidal_area
        avg_noaction_temp_inc = grand_noaction_temp_diff_sum / grand_noaction_temp_diff_count if grand_noaction_temp_diff_count > 0 else np.nan
        physical_loss_count_2100 = actual_tidal_count - grand_pure_physical_insitu_2100_count
        physical_loss_area_2100 = actual_tidal_area - grand_pure_physical_insitu_2100_area

        results = []
        for mr in MR_LIST:
            for thresh in THRESH_LIST:
                comp_insitu_2100_count = grand_counts[thresh][2100]['insitu_count']
                comp_insitu_2100_area = grand_counts[thresh][2100]['insitu_area']
                comp_loss_count_2100 = actual_tidal_count - comp_insitu_2100_count
                comp_loss_area_2100 = actual_tidal_area - comp_insitu_2100_area

                # Excel Output Standardization (English Columns for Reproducibility)
                row_dict = {
                    'Sce': sce, 'MR': mr, 'Conf': conf, 'Blk': f"Block_{BLOCK_ID}", 'Thresh': thresh, 'PA_Name': pa_name,
                    'Total_Grids': total_participating_grids, 'Total_Area': total_participating_area,
                    'No_Init_Tidal_Grids': grand_initial_no_tidal_count, 'No_Init_Tidal_Area': grand_initial_no_tidal_area,
                    'Actual_Tidal_Grids': actual_tidal_count, 'Actual_Tidal_Area': actual_tidal_area,
                    'Hemisphere': pa_hemisphere,
                    'Center_Lon_2020': round(pa_lon_2020_deg, 4), 'Center_Lat_2020': round(pa_lat_2020_deg, 4),
                    'Center_Lat_2100': None, 'Lat_Difference': None, 'Migration_Angle_deg': None, 'Centroid_Move_Dist_km': None, 'Avg_Path_Length_km': None,
                    'NoAction_2100_Temp_Rise_deg': round(avg_noaction_temp_inc, 4) if not np.isnan(avg_noaction_temp_inc) else None
                }
                
                for y in REPORT_YEARS:
                    row_dict[f'InSitu_Count_{y}'] = grand_counts[thresh][y]['insitu_count']
                    row_dict[f'InSitu_Area_{y}'] = grand_counts[thresh][y]['insitu_area']
                    row_dict[f'Corridor_Count_{y}'] = 0
                    row_dict[f'Corridor_Area_{y}'] = 0.0
                    row_dict[f'InPA_Count_{y}'] = 0
                    row_dict[f'InPA_Area_{y}'] = 0.0

                row_dict['Failed_Count_2100'] = grand_initial_no_tidal_count + comp_loss_count_2100
                row_dict['Failed_Area_2100'] = grand_initial_no_tidal_area + comp_loss_area_2100
                row_dict['Actual_Failed_Count_2100'] = comp_loss_count_2100
                row_dict['Actual_Failed_Area_2100'] = comp_loss_area_2100
                row_dict['Total_Failure'] = "Y" if comp_loss_count_2100 == actual_tidal_count else "N"
                row_dict['NoAction_Physical_Loss_Grids'] = physical_loss_count_2100
                row_dict['NoAction_Physical_Loss_Area'] = physical_loss_area_2100
                row_dict['NoAction_Total_Loss_Grids'] = comp_loss_count_2100
                row_dict['NoAction_Total_Loss_Area'] = comp_loss_area_2100
                row_dict['NoAction_Total_Failure'] = row_dict['Total_Failure']

                results.append(row_dict)
                
        print(f"✅✅✅ [{pa_name}] Baseline extraction completed! (SHP exported)")
        return results
    except Exception as e:
        print(f"❌ Exception in PA {pa_name}: {e}")
        return []

# ================= 4. Main Workflow Dispatcher =================
def main():
    print(f"======== 🚀 Launching Baseline Data High-Speed Extraction Engine (with full-matrix SHP dynamic distribution) | Block {BLOCK_ID} ========")
    shp_files = glob.glob(os.path.join(INPUT_DIR, "*.shp"))
    if not shp_files: 
        print("No PA shapefiles found!")
        return

    shp_files.sort(key=lambda x: os.path.getsize(x), reverse=True)
    print(f"⚙️ Multi-processing enabled. Allocated CPU cores: {MAX_WORKERS}")
    if EXPORT_SHP_SETTINGS['ENABLE']:
        print(f"📁 SHP full-matrix distribution tracking enabled. Base directory: {EXPORT_SHP_SETTINGS['BASE_OUT_DIR']}")

    sample_sce = SCENARIO_LIST[0]
    sample_conf = CONF_LIST[0]
    
    base_dir = os.path.join(BASE_WORKSPACE, f"Upload_Blocks_Result/Block_{BLOCK_ID}")
    pattern_proj = os.path.join(base_dir, f"{sample_sce}_MR0_processing_proj/{sample_sce}_2020/Prob_Intertidal_*_{sample_sce}_2020_{sample_conf}_1km_Binary_proj.tif")
    pattern_noproj = os.path.join(base_dir, f"{sample_sce}_MR0/{sample_sce}_2020/Prob_Intertidal_*_{sample_sce}_2020_{sample_conf}_1km_Binary_proj.tif")
    
    block_tiffs = glob.glob(pattern_proj)
    if not block_tiffs:
        block_tiffs = glob.glob(pattern_noproj)
        
    if not block_tiffs: 
        print(f"Base reference tidal image not found! Attempted paths:\n1. {pattern_proj}\n2. {pattern_noproj}")
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

    all_summaries = []

    for sce in SCENARIO_LIST:
        preload_temp_data(block_bounds, sce)
        for conf in CONF_LIST:
            preload_tidal_data(block_bounds, sce, conf)
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = [executor.submit(worker_task, shp, block_bounds, sce, conf) for shp in shp_files]
                
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        all_summaries.extend(res)

    if all_summaries:
        df_out = pd.DataFrame(all_summaries)
        
        col_order = [
            'Sce', 'MR', 'Conf', 'Blk', 'Thresh', 'PA_Name', 
            'Total_Grids', 'Total_Area', 'No_Init_Tidal_Grids', 'No_Init_Tidal_Area', 
            'Actual_Tidal_Grids', 'Actual_Tidal_Area', 'Hemisphere', 
            'Center_Lon_2020', 'Center_Lat_2020', 'Center_Lat_2100', 'Lat_Difference', 
            'Migration_Angle_deg', 'Centroid_Move_Dist_km', 'Avg_Path_Length_km'
        ]
        
        for y in REPORT_YEARS:
            col_order.extend([
                f'InSitu_Count_{y}', f'InSitu_Area_{y}', 
                f'Corridor_Count_{y}', f'Corridor_Area_{y}', 
                f'InPA_Count_{y}', f'InPA_Area_{y}'
            ])
            
        col_order.extend([
            'Failed_Count_2100', 'Failed_Area_2100', 'Actual_Failed_Count_2100', 'Actual_Failed_Area_2100', 'Total_Failure',
            'NoAction_2100_Temp_Rise_deg',
            'NoAction_Physical_Loss_Grids', 'NoAction_Physical_Loss_Area',
            'NoAction_Total_Loss_Grids', 'NoAction_Total_Loss_Area', 'NoAction_Total_Failure'
        ])
        
        df_out = df_out[col_order]
        os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)
        df_out.to_excel(EXCEL_PATH, index=False, engine='openpyxl')
        print(f"\n🎉 Excellent! Block {BLOCK_ID} baseline extraction perfectly aligned and completed!\nFile saved to: {EXCEL_PATH}")

if __name__ == "__main__":
    main()
