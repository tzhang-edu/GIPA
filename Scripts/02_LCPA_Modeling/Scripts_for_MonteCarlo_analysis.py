# -*- coding: utf-8 -*-
# ==============================================================================
# SLRprediction_MLWS_MHHW_multiyears_MonteCarlo_Parallel.py
# 
# Architecture: Dynamic multi-core concurrency + Process isolation + Tile compatibility
# Core fix: Prevented Float32 NoData multiplication overflow and tile file conflicts
# ==============================================================================
import os

# 💡 CRITICAL: When using outer multi-processing, underlying NumPy threads MUST be locked 
# to 1 to prevent underlying C-library thread contention and system crashes.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import glob
import numpy as np
import rasterio
from rasterio.windows import Window
from scipy.ndimage import gaussian_filter, label
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing
import gc
import time
import shutil

# ================= 1. Parameters, Paths & Concurrency Tuning =================
# 🌟 Global Configuration: Easy to modify for different runs
# Note: The globe is divided into 18 blocks (120°x120° each, e.g., Block_01 to Block_18) to facilitate regional computation.
BLOCK_ID = "Block_01"          # e.g., "Block_01", "Block_02", etc.
SCENARIO_NAME = "ssp585"       # Options: "ssp126", "ssp245", "ssp370", "ssp585"

MC_ITERATIONS = 100    
FILTER_SIGMA = 2       

TIME_SERIES = {0: 0, 2040: 20, 2060: 20, 2080: 20, 2100: 20}

TOTAL_CORES = os.cpu_count()
CPU_LIMIT_RATIO = 0.30  # Strictly limit to 30% of total CPU power to avoid server overload

# Reduce inner threads to minimize Python GIL lock competition; bias computing power to outer processes
INNER_THREADS = 6 
MAX_FILE_CONCURRENCY = max(1, int((TOTAL_CORES * CPU_LIMIT_RATIO) // INNER_THREADS))

# === HDD Input/Output Workspaces (Dynamically generated based on BLOCK_ID and SCENARIO_NAME) ===
BASE_WORKSPACE = f"./Upload_Blocks/{BLOCK_ID}"
hdd_dem_workspace   = os.path.join(BASE_WORKSPACE, "DEM_n1")
hdd_mhhw_workspace  = os.path.join(BASE_WORKSPACE, "MHHW")       
hdd_mlws_workspace  = os.path.join(BASE_WORKSPACE, "MLWS")       
hdd_slr_workspace   = os.path.join(BASE_WORKSPACE, SCENARIO_NAME)    
hdd_rmse_workspace  = os.path.join(BASE_WORKSPACE, "DEM_RMSE")
hdd_rmax_workspace  = os.path.join(BASE_WORKSPACE, "Rmax_Threshold")
hdd_out_workspace   = f"./Upload_Blocks_Result/{BLOCK_ID}/{SCENARIO_NAME}"

# === High-Speed RAM Disk Root ===
# Note for Windows/Mac users: "/dev/shm" is a Linux-specific RAM disk. 
# Change this to a standard temporary directory (e.g., "./temp_ram") if not on Linux.
RAMDISK_ROOT = f"/dev/shm/SLR_HPC_WORKSPACE_{BLOCK_ID}_{SCENARIO_NAME}"

# ================= 2. Core Algorithm Logic =================
def get_coastal_window(dem_path, max_elev=15.0):
    with rasterio.open(dem_path) as src:
        scale = 10
        out_shape = (1, max(1, src.height // scale), max(1, src.width // scale))
        dem_coarse = src.read(1, out_shape=out_shape)
        valid = (dem_coarse > -9990)
        if src.nodata is not None: valid &= (dem_coarse != src.nodata)
        mask = (dem_coarse <= max_elev) & valid
        if not np.any(mask): return None
        rows, cols = np.any(mask, axis=1), np.any(mask, axis=0)
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        buffer = 500 
        return Window.from_slices(
            (max(0, rmin * scale - buffer), min(src.height, (rmax + 1) * scale + buffer)),
            (max(0, cmin * scale - buffer), min(src.width, (cmax + 1) * scale + buffer))
        )

def generate_error_field(shape, rmse_arr, sigma, valid_mask):
    noise = np.random.standard_normal(shape).astype(np.float32)
    smoothed = gaussian_filter(noise, sigma=sigma)
    del noise 
    std_smoothed = np.std(smoothed[valid_mask])
    if std_smoothed > 0: smoothed /= std_smoothed  
    
    smoothed *= rmse_arr 
    smoothed[~valid_mask] = 0
    return smoothed

STRUCTURE_3X3 = np.ones((3, 3), dtype=bool)

def get_largest_connected_component(binary_mask):
    labeled_array, num_features = label(binary_mask, STRUCTURE_3X3)
    if num_features == 0: return np.zeros_like(binary_mask, dtype=bool)
    counts = np.bincount(labeled_array.ravel())
    counts[0] = 0  
    if len(counts) <= 1: return np.zeros_like(binary_mask, dtype=bool)
    largest_label = np.argmax(counts)
    ocean_mask = (labeled_array == largest_label)
    del labeled_array 
    return ocean_mask

# ================= 3. Single DEM Processing Workflow =================
def process_single_dem_parallel(dem_filename):
    start_time = time.time()
    
    # Smart parsing of filenames to support both "tiled" and "untiled" DEMs
    base_name = os.path.splitext(dem_filename)[0]
    name_parts = base_name.split('_')
    
    if name_parts[-1].isdigit():  # If ends with a digit (e.g., _0, _1)
        geo_id = name_parts[-2]
        tile_suffix = f"_{name_parts[-1]}"
    else:  # Standard untiled DEM
        geo_id = name_parts[-1]
        tile_suffix = ""
    
    # Add tile_suffix to RAM folder to prevent multi-process overwriting
    local_ram_base = os.path.join(RAMDISK_ROOT, f"{geo_id}{tile_suffix}")
    ram_dem_path = os.path.join(local_ram_base, "DEM", dem_filename)
    ram_out_base = os.path.join(local_ram_base, "OUT")
    
    try:
        for sub in ["DEM", "MHHW", "MLWS", "SLR", "RMAX", "OUT"]:
            os.makedirs(os.path.join(local_ram_base, sub), exist_ok=True)
            
        shutil.copy2(os.path.join(hdd_dem_workspace, dem_filename), ram_dem_path)
        
        mhhw_src_files = glob.glob(os.path.join(hdd_mhhw_workspace, f"*{geo_id}*.tif"))
        mlws_src_files = glob.glob(os.path.join(hdd_mlws_workspace, f"*{geo_id}*.tif"))
        if not mhhw_src_files or not mlws_src_files:
            shutil.rmtree(local_ram_base)
            return f"❌ [{geo_id}{tile_suffix}] Skipped: Missing tidal surface files."
            
        for f in mhhw_src_files: shutil.copy2(f, os.path.join(local_ram_base, "MHHW"))
        for f in mlws_src_files: shutil.copy2(f, os.path.join(local_ram_base, "MLWS"))
        for f in glob.glob(os.path.join(hdd_slr_workspace, f"*{SCENARIO_NAME}*{geo_id}*.tif")):
            shutil.copy2(f, os.path.join(local_ram_base, "SLR"))
            
        rmse_src_files = glob.glob(os.path.join(hdd_rmse_workspace, f"*DEM_RMSE_{geo_id}*.tif"))
        if not rmse_src_files:
            shutil.rmtree(local_ram_base)
            return f"❌ [{geo_id}{tile_suffix}] Skipped: Missing corresponding DEM_RMSE file."

        rmax_src_files = glob.glob(os.path.join(hdd_rmax_workspace, f"*{geo_id}*.tif"))
        if rmax_src_files:
            shutil.copy2(rmax_src_files[0], os.path.join(local_ram_base, "RMAX"))

        window = get_coastal_window(ram_dem_path, max_elev=15.0)
        if window is None:
            shutil.rmtree(local_ram_base)
            return f"⏭️ [{geo_id}{tile_suffix}] Scanned: No coastline or elevation too high locally. Skipping."
        
        with rasterio.open(ram_dem_path) as src:
            dem_arr = src.read(1, window=window).astype(np.float32)
            profile = src.profile
            dem_nodata = src.nodata
            chunk_bounds = rasterio.windows.bounds(window, src.transform)
            profile.update({'height': window.height, 'width': window.width, 'transform': rasterio.windows.transform(window, src.transform)})
            
        valid_mask = (dem_arr != dem_nodata) if dem_nodata is not None else (dem_arr > -9990)
        
        mhhw_ram_files = glob.glob(os.path.join(local_ram_base, "MHHW", f"*{geo_id}*.tif"))
        ml_ram_files = glob.glob(os.path.join(local_ram_base, "MLWS", f"*{geo_id}*.tif"))
        
        with rasterio.open(mhhw_ram_files[0]) as src:            
            mhhw_window = rasterio.windows.from_bounds(*chunk_bounds, transform=src.transform)
            mhhw_arr = src.read(1, window=mhhw_window, out_shape=dem_arr.shape).astype(np.float32)
            
        with rasterio.open(ml_ram_files[0]) as src: 
            mlws_window = rasterio.windows.from_bounds(*chunk_bounds, transform=src.transform)
            mlws_arr = src.read(1, window=mlws_window, out_shape=dem_arr.shape).astype(np.float32)        

        rmax_ram_files = glob.glob(os.path.join(local_ram_base, "RMAX", f"*{geo_id}*.tif"))      
        if rmax_ram_files:
            with rasterio.open(rmax_ram_files[0]) as src:
                rmax_window = rasterio.windows.from_bounds(*chunk_bounds, transform=src.transform)
                r_max_arr = src.read(1, window=rmax_window, out_shape=dem_arr.shape, boundless=True, fill_value=-9999.0).astype(np.float32)
        else:
            r_max_arr = np.zeros(dem_arr.shape, dtype=np.float32)

        with rasterio.open(rmse_src_files[0]) as src_rmse:
            rmse_window = rasterio.windows.from_bounds(*chunk_bounds, transform=src_rmse.transform)
            rmse_arr = src_rmse.read(1, window=rmse_window, out_shape=dem_arr.shape).astype(np.float32)
            
            if src_rmse.nodata is not None:
                rmse_arr[rmse_arr == src_rmse.nodata] = 0.0
            rmse_arr[(rmse_arr < 0) | (rmse_arr > 10000)] = 0.0 
            rmse_arr[~valid_mask] = 0.0
            
        cumulative_slr_meters = 0.0
        cumulative_accretion_meters = 0.0  
        
        for target_year, duration in TIME_SERIES.items():
            year_folder = f"{SCENARIO_NAME}_2020" if target_year == 0 else f"{SCENARIO_NAME}_{target_year}"            
            
            # Apply tile_suffix to output file to prevent overwriting among tiles
            out_final_tif = os.path.join(ram_out_base, year_folder, f"Prob_Intertidal_{geo_id}{tile_suffix}_{year_folder}.tif")
            
            if target_year != 0:
                search_path = os.path.join(hdd_slr_workspace, f"*{SCENARIO_NAME}*{target_year}*{geo_id}*.tif")
                
                slr_ram_files = glob.glob(os.path.join(local_ram_base, "SLR", f"*{SCENARIO_NAME}*{target_year}*{geo_id}*.tif"))
                if not slr_ram_files:
                    print(f"  ⚠️ Warning [{geo_id}{tile_suffix}]: SLR data not found, skipping year {target_year}.")
                    continue
                    
                with rasterio.open(slr_ram_files[0]) as src:
                    slr_window = rasterio.windows.from_bounds(*chunk_bounds, transform=src.transform)
                    slr_arr = src.read(1, window=slr_window, out_shape=dem_arr.shape, boundless=True, fill_value=-9999.0).astype(np.float32)
                    slr_arr[~valid_mask] = 0.0  
              
                survive_mask = (slr_arr <= r_max_arr) & valid_mask
                accretion_rate = np.zeros_like(slr_arr, dtype=np.float32)
                accretion_rate[survive_mask] = slr_arr[survive_mask]
                
                cumulative_accretion_meters += (accretion_rate * duration) / 1000.0
                del survive_mask, accretion_rate
                
                cumulative_slr_meters += (slr_arr * duration) / 1000.0
                del slr_arr 
                
            effective_slr = cumulative_slr_meters - cumulative_accretion_meters
            target_high = mhhw_arr + effective_slr
            target_low = mlws_arr + effective_slr
            prob_sum_arr = np.zeros_like(dem_arr, dtype=np.float32)
            
            def run_single_mc():
                error_field = generate_error_field(dem_arr.shape, rmse_arr, FILTER_SIGMA, valid_mask)
                perturbed_dem = dem_arr + error_field
                del error_field
                inundated = (perturbed_dem <= target_high) & valid_mask
                ocean_mask = get_largest_connected_component(inundated)
                del inundated
                intertidal_mask = ocean_mask & (perturbed_dem >= target_low)
                del perturbed_dem, ocean_mask
                return intertidal_mask

            # 💡 Core Concurrency: Apply uniform global settings to inner ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=INNER_THREADS) as thread_pool:
                futures = [thread_pool.submit(run_single_mc) for _ in range(MC_ITERATIONS)]
                for future in as_completed(futures):
                    prob_sum_arr[future.result()] += 1.0 
                    
            final_prob = prob_sum_arr / MC_ITERATIONS
            final_prob[~valid_mask] = -9999.0
            final_prob[final_prob == 0] = -9999.0
            
            profile.update(dtype=rasterio.float32, count=1, compress='zstd', zstd_level=1, predictor=3, nodata=-9999.0)

            os.makedirs(os.path.dirname(out_final_tif), exist_ok=True)
            with rasterio.open(out_final_tif, 'w', **profile) as dst:
                dst.write(final_prob.astype(rasterio.float32), 1)
                
            del prob_sum_arr, final_prob
            
        del dem_arr, mhhw_arr, mlws_arr, valid_mask, rmse_arr, r_max_arr
        
        # 5. Write results back to HDD
        for root, dirs, files in os.walk(ram_out_base):
            for file in files:
                if file.endswith(".tif"):
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(root, ram_out_base) 
                    dest_dir = os.path.join(hdd_out_workspace, rel_path)
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(src_file, os.path.join(dest_dir, file))
                    
        shutil.rmtree(local_ram_base)
        elapsed = time.time() - start_time
        return f"⚡ [{geo_id}{tile_suffix}] Processing completed successfully! Time elapsed: {elapsed:.2f} s"
        
    except Exception as e:
        if os.path.exists(local_ram_base): shutil.rmtree(local_ram_base)
        return f"❌ [{geo_id}{tile_suffix}] Runtime Exception: {str(e)}"

# ================= 4. Main Concurrency Engine =================
if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    
    dem_filepaths = glob.glob(os.path.join(hdd_dem_workspace, "*.tif"))
    dem_filenames = [os.path.basename(p) for p in dem_filepaths]
    total_files = len(dem_filenames)
    
    if total_files == 0:
        print(f"❌ Error: No DEM files found in {hdd_dem_workspace}. Please check the workspace path.")
        exit()
        
    print(f"✅ Locked target: {total_files} DEM tile tasks found for {BLOCK_ID} under {SCENARIO_NAME}.")
    print(f"🖥️ Detected physical CPU cores: {TOTAL_CORES}")
    print(f"🤝 [Shared Server Friendly Mode] Activated. Maximum CPU utilization capped at: {int(CPU_LIMIT_RATIO * 100)}%.")
    
    ACTUAL_CONCURRENCY = min(MAX_FILE_CONCURRENCY, total_files)
    
    print(f"🚀 Initializing parallel engine! Outer processes: {ACTUAL_CONCURRENCY} | Inner threads per file: {INNER_THREADS}...")
    print(f"=======================================================================\n")
    
    if os.path.exists(RAMDISK_ROOT): shutil.rmtree(RAMDISK_ROOT)
    os.makedirs(RAMDISK_ROOT, exist_ok=True)
    
    start_block_time = time.time()
    
    with ProcessPoolExecutor(max_workers=ACTUAL_CONCURRENCY) as executor:
        futures = {executor.submit(process_single_dem_parallel, name): name for name in dem_filenames}
        for future in as_completed(futures):
            print(future.result())
            gc.collect()
            
    if os.path.exists(RAMDISK_ROOT): shutil.rmtree(RAMDISK_ROOT)
    
    total_elapsed = time.time() - start_block_time
    print(f"\n🎉 Excellent! High-concurrency processing for {BLOCK_ID} is complete. Total time: {total_elapsed:.2f} s.")
