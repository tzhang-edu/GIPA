# -*- coding: utf-8 -*-
import os
import glob
import pandas as pd
import numpy as np
import geopandas as gpd
import concurrent.futures
import plotly.graph_objects as go
import matplotlib.colors as mcolors
import warnings


# =====================================================================
# 1. 全局配置与文件路径 (统一管理)
# =====================================================================
# ---- 输入数据路径 ----
INPUT_DIR = r"G:\PA_Analysis\PA_Results_26\Results across SSPs" 
EEZ_SHP_PATH = r"G:\Bird_SLR\EEZ_land_union_v4_202410\EEZ_land_union_v4_202410.shp"
MASTER_EXCEL = r"G:\github\GIPA\Data\Master_Baseline_Combined_0923_1013_v2_linkinfo_fixed.xlsx"

# ---- 中间生成文件与最终出图路径 ----
EEZ_SUMMARY_EXCEL = r"G:\PA_Analysis\PA_Results_26\Figure4b_Endpoints_EEZ_Summary_v3.xlsx"
OD_CSV_PATH = r"G:\github\GIPA\Data\Figure4b_Transboundary_OD_Matrix_Optimized.csv"
OUTPUT_PNG_PATH = r"G:\github\GIPA\Figure\Figure4b_Network_Optimized.png"

# ---- 业务参数配置 ----
EXCLUDE_KEYWORDS = [
    '_unsuccessful', '_InitialTidalPts', '_SuccessfulStartPts', 
    '_Endpoints_20', '_paths_'
]

# OD矩阵与出图筛选条件
TARGET_SCE = 'ssp245'  
TARGET_MR = 'MR1'
TARGET_CONF = 'Mid_Prob'
TARGET_THRESH = 0.20

# 声明全局变量，解决多进程传参内存溢出问题
global_eez_gdf = None


# =====================================================================
# 模块 A 工具函数: 文件名解析与多进程初始化
# =====================================================================
def parse_filename(filename):
    base = os.path.splitext(filename)[0]
    parts = base.split('_')
    try:
        thresh_str = parts[-1]
        thresh = float(thresh_str.replace('T', '')) if 'T' in thresh_str else thresh_str
        conf = f"{parts[-3]}_{parts[-2]}" 
        mr = parts[-4]                    
        sce = parts[-5]                   
        pa_name = "_".join(parts[:-5])    
        return pa_name, sce, mr, conf, thresh
    except Exception:
        return None, None, None, None, None

def init_worker(eez_path):
    """多进程初始化：每个核心自己加载一次 EEZ，提取 ISO_TER1"""
    global global_eez_gdf
    global_eez_gdf = gpd.read_file(eez_path)[['ISO_TER1', 'geometry']]

def process_single_shp(shp_path):
    """核心空间匹配工作函数 (单文件处理)"""
    global global_eez_gdf
    filename = os.path.basename(shp_path)
    
    pa_name, sce, mr, conf, thresh = parse_filename(filename)
    if not pa_name:
        return None
        
    try:
        # 拦截 0 字节损坏文件，防止 GDAL 报错崩溃
        if os.path.getsize(shp_path) < 100:
            return None
            
        base_path = os.path.splitext(shp_path)[0]
        if not (os.path.exists(base_path + '.shx') and os.path.exists(base_path + '.dbf')):
            return None

        # 正常读取
        pts_gdf = gpd.read_file(shp_path)
        if pts_gdf.empty:
            return None
            
        if pts_gdf.crs != global_eez_gdf.crs:
            pts_gdf = pts_gdf.to_crs(global_eez_gdf.crs)
            
        joined = gpd.sjoin(pts_gdf, global_eez_gdf, how="left", predicate="intersects")
        
        counts = joined['ISO_TER1'].value_counts(dropna=False).reset_index()
        counts.columns = ['ISO_TER1', 'Point_Count']
        counts['ISO_TER1'] = counts['ISO_TER1'].fillna("High_Seas_or_Unknown")
        
        results = []
        for _, row in counts.iterrows():
            results.append({
                'PA_Name': pa_name,
                'Scenario': sce,
                'MR': mr,
                'Confidence': conf,
                'Threshold': thresh,
                'ISO_TER1': row['ISO_TER1'],
                'Point_Count': int(row['Point_Count'])
            })
        return results
        
    except Exception:
        return None


# =====================================================================
# 步骤 1：空间匹配与生成汇总表 
# =====================================================================
def step1_spatial_matching():
    print("第一步：执行空间匹配与端点提取，汇总EEZ信息...")
    search_pattern = os.path.join(INPUT_DIR, "**", "Output_ranges_pt", "*.shp")
    all_shps = glob.glob(search_pattern, recursive=True)
    
    target_shps = []
    folder_total_counts = {}     
    folder_completed_counts = {} 
    
    for shp in all_shps:
        basename = os.path.basename(shp)
        if not any(k in basename for k in EXCLUDE_KEYWORDS):
            target_shps.append(shp)
            
            parent_dir = os.path.dirname(shp)
            folder_total_counts[parent_dir] = folder_total_counts.get(parent_dir, 0) + 1
            folder_completed_counts[parent_dir] = 0
            
    if not target_shps:
        return

    all_summaries = []
    MAX_WORKERS = min(16, os.cpu_count() or 4) 
    
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=MAX_WORKERS, 
        initializer=init_worker, 
        initargs=(EEZ_SHP_PATH,)
    ) as executor:
        
        futures = {executor.submit(process_single_shp, shp): shp for shp in target_shps}
        
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            shp_path = futures[future]  
            parent_dir = os.path.dirname(shp_path) 
            
            res = future.result()
            if res:
                all_summaries.extend(res)
            
            folder_completed_counts[parent_dir] += 1

    if all_summaries:
        df_summary = pd.DataFrame(all_summaries)
        df_summary.sort_values(by=['PA_Name', 'Scenario', 'MR', 'Point_Count'], 
                               ascending=[True, True, True, False], inplace=True)
        df_summary.to_excel(EEZ_SUMMARY_EXCEL, index=False)
        print(f"输出Excel: {EEZ_SUMMARY_EXCEL}\n")


# =====================================================================
# 步骤 2：生成 OD 矩阵 
# =====================================================================
def step2_generate_od_matrix():
    print("第二步：整合OD矩阵数据，计算比例分配面积...")
    
    try:
        df_master = pd.read_excel(MASTER_EXCEL, sheet_name="Sheet2_Summary")
    except ValueError:
        df_master = pd.read_excel(MASTER_EXCEL)
        
    try:
        df_eez = pd.read_excel(EEZ_SUMMARY_EXCEL)
    except FileNotFoundError:
        return
    
    # 过滤与整理主表数据
    df_m = df_master[(df_master['Sce'] == TARGET_SCE) & 
                     (df_master['MR'].str.contains(TARGET_MR, case=False, na=False)) &
                     (df_master['Conf'] == TARGET_CONF) & 
                     (np.isclose(df_master['Thresh'].astype(float), TARGET_THRESH, atol=1e-3))].copy()
                     
    df_m['廊道面积_2100'] = df_m['廊道面积_2100'].fillna(0)
    master_subset = df_m[['PA_Name', 'ISO3', '廊道面积_2100']]
    
    # 过滤 EEZ 汇总表数据
    df_e = df_eez[(df_eez['Scenario'] == TARGET_SCE) & 
                  (df_eez['MR'] == TARGET_MR) & 
                  (df_eez['Confidence'] == TARGET_CONF) &
                  (np.isclose(df_eez['Threshold'].astype(float), TARGET_THRESH, atol=1e-3))].copy()
                  
    if df_e.empty:
         return
         
    # 计算比例分配面积
    pa_point_totals = df_e.groupby('PA_Name')['Point_Count'].sum().reset_index(name='Total_Points')
    df_e = df_e.merge(pa_point_totals, on='PA_Name', how='left')
    df_e = df_e.merge(master_subset, on='PA_Name', how='inner')
    df_e['Flow_Area'] = df_e['廊道面积_2100'] * (df_e['Point_Count'] / df_e['Total_Points'])
    
    # 构建 OD 矩阵
    od_matrix = df_e.groupby(['ISO3', 'ISO_TER1'])['Flow_Area'].sum().reset_index()
    od_matrix.rename(columns={'ISO3': 'Origin_Country', 'ISO_TER1': 'Destination_Country'}, inplace=True)
    
    od_matrix['Migration_Type'] = np.where(od_matrix['Origin_Country'] == od_matrix['Destination_Country'], 
                                           'Domestic', 'Transboundary')
    od_matrix = od_matrix[od_matrix['Flow_Area'] > 0]
    od_matrix = od_matrix.sort_values(by='Flow_Area', ascending=False)
    
    od_matrix.to_csv(OD_CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"输出CSV: {OD_CSV_PATH}\n")


# =====================================================================
# 步骤 3：绘制 Sankey 图 
# =====================================================================
def step3_draw_sankey():
    print("第三步：数据清洗并绘制跨界流动网络图(Sankey)...")

    try:
        df = pd.read_csv(OD_CSV_PATH)
    except FileNotFoundError:
        return
        
    df_trans = df[df['Migration_Type'] == 'Transboundary'].copy()
    if df_trans.empty:
        return
        
    # =====================================================================
    # 🌟 核心修正：剔除目的地或出发地为公海/未知区域 (High_Seas_or_Unknown)
    # =====================================================================
    df_trans = df_trans[(df_trans['Origin_Country'] != 'High_Seas_or_Unknown') & 
                        (df_trans['Destination_Country'] != 'High_Seas_or_Unknown')].copy()

    # =====================================================================
    # 🌟 核心修正：剔除复合保护地伪跨界
    # =====================================================================
    def is_pseudo_transboundary(row):
        origin = str(row['Origin_Country'])
        dest = str(row['Destination_Country'])
        if dest in origin.split(';'):
            return True
        if origin in dest.split(';'):
            return True
        return False

    df_trans['Is_Pseudo'] = df_trans.apply(is_pseudo_transboundary, axis=1)
    df_trans = df_trans[~df_trans['Is_Pseudo']].copy()

    # 筛选 Top 10
    top_origins = df_trans.groupby('Origin_Country')['Flow_Area'].sum().nlargest(10).index.tolist()
    top_dests = df_trans.groupby('Destination_Country')['Flow_Area'].sum().nlargest(10).index.tolist()
    
    df_top = df_trans[(df_trans['Origin_Country'].isin(top_origins)) & 
                      (df_trans['Destination_Country'].isin(top_dests))].copy()
                      
    if df_top.empty:
        return

    # 灰阶映射
    country_outflow = df_top.groupby('Origin_Country')['Flow_Area'].sum().sort_values(ascending=False)
    gray_scales = [
        '#101010', '#1F1F1F', '#2E2E2E', '#3D3D3D', '#4C4C4C', 
        '#5C5C5C', '#6B6B6B', '#7A7A7A', '#8A8A8A', '#999999', 
        '#A8A8A8', '#B8B8B8', '#C7C7C7', '#D6D6D6', '#E6E6E6'
    ]
    dynamic_palette = {country: gray_scales[i] if i < len(gray_scales) else '#EAEAEA' 
                       for i, country in enumerate(country_outflow.index)}
            
    # 构建节点与连线
    nodes_src = list(df_top['Origin_Country'].unique())
    nodes_tgt = list(df_top['Destination_Country'].unique())
    node_labels = nodes_src + nodes_tgt
    node_colors = [dynamic_palette.get(node, '#E0E0E0') for node in node_labels]

    source_indices, target_indices, values, link_colors = [], [], [], []
    for _, row in df_top.iterrows():
        src_idx = nodes_src.index(row['Origin_Country'])
        tgt_idx = len(nodes_src) + nodes_tgt.index(row['Destination_Country'])
        
        source_indices.append(src_idx)
        target_indices.append(tgt_idx)
        values.append(row['Flow_Area'])
        
        base_color = node_colors[src_idx]
        rgba = mcolors.to_rgba(base_color, alpha=0.45)
        link_colors.append(f"rgba({int(rgba[0]*255)}, {int(rgba[1]*255)}, {int(rgba[2]*255)}, {rgba[3]})")

    # 物理尺寸渲染
    target_height_mm = 100
    target_width_mm = 50 
    base_dpi, target_dpi = 96, 300
    scale_factor = target_dpi / base_dpi 
    base_height_px = int((target_height_mm / 25.4) * base_dpi)
    base_width_px = int((target_width_mm / 25.4) * base_dpi)

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=25, thickness=12, 
            line=dict(color="rgba(0,0,0,0)", width=0), 
            label=node_labels, color=node_colors
        ),
        link=dict(
            source=source_indices, target=target_indices,
            value=values, color=link_colors
        )
    )])

    fig.update_layout(
        font=dict(size=12, color="#333333"), 
        plot_bgcolor='white', paper_bgcolor='white',
        width=base_width_px, height=base_height_px,
        margin=dict(l=35, r=35, t=20, b=20) 
    )

    try:
        fig.write_image(OUTPUT_PNG_PATH, scale=scale_factor) 
        print(f"输出图片: {OUTPUT_PNG_PATH}\n")
    except ValueError:
        pass


# =====================================================================
# 主函数 (自动化流水线控制)
# =====================================================================
def main():
    # 根据需要可以注释掉无需重复执行的步骤
    # step1_spatial_matching() 
    step2_generate_od_matrix()
    step3_draw_sankey()

if __name__ == "__main__":
    main()
