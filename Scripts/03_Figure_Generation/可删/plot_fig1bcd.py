# -*- coding: utf-8 -*-
import os
import warnings
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
import libpysal
from spreg import GM_Error
from scipy.stats import spearmanr

# 忽略常规警告
warnings.filterwarnings("ignore")

# =====================================================================
# 1. 配置文件路径与全局参数
# =====================================================================
INPUT_EXCEL_BASELINE = r"G:\github\GIPA\Data\Master_Baseline_Combined_0923_1013_v2_linkinfo_fixed.xlsx" 
# 🌟 修改点 1：更新输出的 Excel 文件名
PROCESSED_EXCEL = r"G:\github\GIPA\Data\Figure1b_Intermediate_data.xlsx"
OUTPUT_DIR = r"G:\github\GIPA\Figure"

# 绘图参数
SCENARIO = 'ssp245'  
TARGET_CONF = 'Mid_Prob' 
TARGET_THRESH = 0.20  
SSP245_COLOR = '#7b86a5' 
LINE_COLOR = '#333333'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# =====================================================================
# 2. 模块 A：数据预处理 
# =====================================================================
def process_data():
    print("开始执行模块 A: 读取 Baseline 并生成网格统计数据...")
    
    print(f"正在加载数据: {INPUT_EXCEL_BASELINE}")
    df = pd.read_excel(INPUT_EXCEL_BASELINE)
    
    df = df[
        (df['MR'] == 'Baseline') & 
        (df['Sce'] == SCENARIO) & 
        (df['Conf'] == TARGET_CONF) &
        (np.isclose(df['Thresh'].astype(float), TARGET_THRESH, atol=1e-3))
    ].copy()
    
    if df.empty:
        print(f"⚠️ 警告：筛选后数据为空，请检查表格中是否包含对应条件的数据。")
        return

    # 提取参与计算的基础列
    cols_needed = [
        'Sce', '2020中心经度', '2020中心纬度', 
        '实际潮滩_面积', '原地面积_2100', '廊道面积_2100', 
        'NoAction_2100原址升温(度)'
    ]
    
    # 检查列是否存在以防报错
    missing_cols = [col for col in cols_needed if col not in df.columns]
    if missing_cols:
        print(f"⚠️ 报错：输入表格中找不到以下列，无法执行计算: {missing_cols}")
        return

    # 去掉缺失坐标的无效行
    df = df[cols_needed].dropna(subset=['2020中心经度', '2020中心纬度'])
    
    # 按照公式计算新的丧失面积列
    df['实际潮滩丧失_面积'] = df['实际潮滩_面积'] - df['原地面积_2100'] - df['廊道面积_2100']
    area_col = '实际潮滩丧失_面积'

    # 网格化处理 (Binning)
    df['Lat_Grid'] = np.floor(df['2020中心纬度']).astype(int)
    df['Lon_Grid'] = np.floor(df['2020中心经度']).astype(int)

    df = df[(df['Lat_Grid'] >= -60) & (df['Lat_Grid'] <= 60)]
    df = df[(df['Lon_Grid'] >= -180) & (df['Lon_Grid'] <= 180)]

    scenarios = ['ssp126', 'ssp245', 'ssp370', 'ssp585']

    def create_pivot(data, index_col, values_col, index_range, index_name, agg_method='mean', fill_val=np.nan):
        pivot = data.pivot_table(
            index=index_col, columns='Sce', values=values_col,
            aggfunc=agg_method, fill_value=fill_val
        )
        for sce in scenarios:
            if sce not in pivot.columns:
                pivot[sce] = fill_val
        pivot = pivot[scenarios] 
        
        full_index = pd.Index(range(index_range[0], index_range[1] + 1), name=index_name)
        pivot = pivot.reindex(full_index, fill_value=fill_val)
        pivot.reset_index(inplace=True)
        return pivot

    print("正在计算网格统计值...")
    # 生成数据表 
    lat_area_df = create_pivot(df, 'Lat_Grid', area_col, (-60, 60), 'Latitude', agg_method='sum', fill_val=np.nan)
    lon_area_df = create_pivot(df, 'Lon_Grid', area_col, (-180, 180), 'Longitude', agg_method='sum', fill_val=np.nan)
    lat_temp_df = create_pivot(df, 'Lat_Grid', 'NoAction_2100原址升温(度)', (-60, 60), 'Latitude', agg_method='mean', fill_val=np.nan)
    lon_temp_df = create_pivot(df, 'Lon_Grid', 'NoAction_2100原址升温(度)', (-180, 180), 'Longitude', agg_method='mean', fill_val=np.nan)

    # 二维网格聚合数据
    jointplot_df = df.groupby(['Sce', 'Lat_Grid', 'Lon_Grid']).agg(
        Grid_AreaLost=(area_col, 'sum'),
        Grid_TempInc=('NoAction_2100原址升温(度)', 'mean')
    ).reset_index()
    
    # 剔除丧失面积为 0 或负数 的无效网格
    jointplot_df = jointplot_df[jointplot_df['Grid_AreaLost'] > 0]

    # 🌟 修改点 2：更新控制台打印信息
    print(f"处理后的中间数据保存至: {PROCESSED_EXCEL}")
    with pd.ExcelWriter(PROCESSED_EXCEL, engine='openpyxl') as writer:
        lat_area_df.to_excel(writer, sheet_name='Sheet1_Lat_AreaLost', index=False)
        lon_area_df.to_excel(writer, sheet_name='Sheet2_Lon_AreaLost', index=False)
        lat_temp_df.to_excel(writer, sheet_name='Sheet3_Lat_TempInc', index=False)
        lon_temp_df.to_excel(writer, sheet_name='Sheet4_Lon_TempInc', index=False)
        jointplot_df.to_excel(writer, sheet_name='Sheet5_Jointplot_Data', index=False)
    print("✅ 模块 A 完成！")

# =====================================================================
# 3. 模块 B：生成图 1b (Regplot)
# =====================================================================
def generate_figure_1b():
    print(f"\n🚀 开始执行模块 B: 生成图 1b (Regplot) | 情景: {SCENARIO}")
    
    df_grid = pd.read_excel(PROCESSED_EXCEL, sheet_name='Sheet5_Jointplot_Data')
    df_sce = df_grid[df_grid['Sce'] == SCENARIO].copy()
    
    df_clean = df_sce[df_sce['Grid_AreaLost'] > 0].copy()
    df_clean['Log_AreaLost'] = np.log10(df_clean['Grid_AreaLost'])
    
    X = df_clean['Grid_TempInc']
    Y = df_clean['Log_AreaLost']

    spearman_corr, p_s = spearmanr(X, Y)

    sns.set_theme(style="ticks", context="paper")
    
    ax_size_mm = 40.0
    ax_size_in = ax_size_mm / 25.4  
    
    left_margin_in = 0.8
    right_margin_in = 0.2
    bottom_margin_in = 0.8
    top_margin_in = 0.2
    
    fig_width_in = ax_size_in + left_margin_in + right_margin_in
    fig_height_in = ax_size_in + bottom_margin_in + top_margin_in
    
    fig, ax = plt.subplots(figsize=(fig_width_in, fig_height_in))
    
    plt.subplots_adjust(
        left = left_margin_in / fig_width_in,
        right = 1.0 - (right_margin_in / fig_width_in),
        bottom = bottom_margin_in / fig_height_in,
        top = 1.0 - (top_margin_in / fig_height_in)
    )
    
    sns.regplot(
        x=X, y=Y, truncate=False, ax=ax,
        scatter_kws={"color": SSP245_COLOR, "s": 30, "alpha": 0.8, "edgecolors": "white", "linewidths": 0.5},
        line_kws={"color": LINE_COLOR, "linewidth": 2}
    )

    ax.set_xlabel(r'Temp.$_{\mathrm{incr.}}$ (°C)', fontsize=12, labelpad=1)
    ax.set_ylabel(r'Log$_{10}$ Area$_{\mathrm{loss}}$ ($km^2$)', fontsize=12, labelpad=1)
    
    ax.locator_params(axis='x', nbins=4)
    ax.locator_params(axis='y', nbins=5)
    ax.tick_params(axis='both', which='major', labelsize=12)
    
    stat_text = f"Spearman's $\\rho$ = {spearman_corr:.2f}\n$p$ = {p_s:.2e}"
    
    bbox_props = dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='square,pad=0.1')
    
    ax.text(
        0.95, 0.95, stat_text, transform=ax.transAxes, 
        fontsize=9, verticalalignment='top', horizontalalignment='right',
        bbox=bbox_props
    )
    
    sns.despine()
    out_fig = os.path.join(OUTPUT_DIR, f"Figure1b_Regplot_{SCENARIO}.png")
    
    plt.savefig(out_fig, dpi=300, transparent=True)
    print(f"✅ 图 1b 已成功保存至: {out_fig}")
    plt.close()

# =====================================================================
# 4. 模块 C：生成图 1c & 1d (纬度剖面) 
# =====================================================================
def generate_figure_1cd():
    print(f"\n🚀 开始执行模块 C: 生成图 1c & 1d (纬度剖面) | 情景: {SCENARIO}")
    
    df_area = pd.read_excel(PROCESSED_EXCEL, sheet_name='Sheet1_Lat_AreaLost')
    df_temp = pd.read_excel(PROCESSED_EXCEL, sheet_name='Sheet3_Lat_TempInc')
    
    lat_profile = pd.DataFrame({
        'Latitude': df_area['Latitude'],
        'Area_Loss': df_area[SCENARIO],
        'Temp_Inc': df_temp[SCENARIO]
    })
    
    lat_profile['Log_Area_Loss'] = np.log10(lat_profile['Area_Loss'].where(lat_profile['Area_Loss'] > 0, np.nan))
    lat_north = lat_profile[lat_profile['Latitude'] > 0]
    lat_south = lat_profile[lat_profile['Latitude'] < 0]
    
    df_grid2d = pd.read_excel(PROCESSED_EXCEL, sheet_name='Sheet5_Jointplot_Data')
    df_sce2d = df_grid2d[df_grid2d['Sce'] == SCENARIO].copy().dropna()
    df_sce2d = df_sce2d[df_sce2d['Grid_AreaLost'] > 0].copy()
    df_sce2d['Log_AreaLost'] = np.log10(df_sce2d['Grid_AreaLost'])
    df_sce2d['Abs_Lat_Grid'] = df_sce2d['Lat_Grid'].abs()
    
    df_north_stat = df_sce2d[df_sce2d['Lat_Grid'] > 0].copy()
    df_south_stat = df_sce2d[df_sce2d['Lat_Grid'] < 0].copy()
    
    def run_local_sem(df_subset, var_name, region_name):
        if len(df_subset) < 5:
            return "N/A", "N/A"
        try:
            geometry = [Point(xy) for xy in zip(df_subset['Lon_Grid'], df_subset['Lat_Grid'])]
            gdf = gpd.GeoDataFrame(df_subset, geometry=geometry, crs="EPSG:4326")
            Y_val = gdf[var_name].values.reshape(-1, 1)
            X_val = gdf['Abs_Lat_Grid'].values.reshape(-1, 1)
            w = libpysal.weights.KNN.from_dataframe(gdf, k=4)
            w.transform = 'r'
            sem_model = GM_Error(Y_val, X_val, w=w, name_y=var_name, name_x=['Abs_Latitude'])
            return sem_model.betas[1][0], sem_model.z_stat[1][1]
        except:
            return None, None

    results_text = {'Log_Area_Loss': {}, 'Temp_Inc': {}}
    var_mapping = {'Log_Area_Loss': 'Log_AreaLost', 'Temp_Inc': 'Grid_TempInc'}
    
    for key, grid_col in var_mapping.items():
        coef_n, pval_n = run_local_sem(df_north_stat, grid_col, "North")
        results_text[key]['North'] = f"SEM Coef={coef_n:.3f}\n$p$={pval_n:.3f}" if coef_n else "SEM Coef: N/A"
            
        coef_s, pval_s = run_local_sem(df_south_stat, grid_col, "South")
        results_text[key]['South'] = f"SEM Coef={coef_s:.3f}\n$p$={pval_s:.3f}" if coef_s else "SEM Coef: N/A"

    sns.set_theme(style="ticks", context="paper")
    
    ax_height_mm = 99.81
    ax_width_mm = 25.0
    
    ax_height_in = ax_height_mm / 25.4  
    ax_width_in = ax_width_mm / 25.4    
    
    bottom_margin_in = 0.9  
    top_margin_in = 0.6     
    left_margin_in = 0.9    
    right_margin_in = 0.2   
    wspace_in = 0.15         
    
    fig_height_in = ax_height_in + bottom_margin_in + top_margin_in
    fig_width_in = (ax_width_in * 2) + wspace_in + left_margin_in + right_margin_in
    
    fig, axes = plt.subplots(1, 2, figsize=(fig_width_in, fig_height_in), sharey=True)
    
    plt.subplots_adjust(
        bottom = bottom_margin_in / fig_height_in,
        top = (bottom_margin_in + ax_height_in) / fig_height_in,
        left = left_margin_in / fig_width_in,
        right = 1.0 - (right_margin_in / fig_width_in),
        wspace = wspace_in / ax_width_in  
    )
    
    # 图 1c
    sns.scatterplot(data=lat_profile, x='Log_Area_Loss', y='Latitude', 
                    ax=axes[0], color=SSP245_COLOR, alpha=0.8, s=40, edgecolor='white', linewidth=0.8)
    sns.regplot(data=lat_north, x='Log_Area_Loss', y='Latitude', 
                ax=axes[0], scatter=False, lowess=False, color=LINE_COLOR, line_kws={'linewidth': 2.5})
    sns.regplot(data=lat_south, x='Log_Area_Loss', y='Latitude', 
                ax=axes[0], scatter=False, lowess=False, color=LINE_COLOR, line_kws={'linewidth': 2.5})
    
    axes[0].set_ylim(-90, 90)
    axes[0].set_yticks([-90, -60, -30, 0, 30, 60, 90])
    axes[0].set_yticklabels(['90°S', '60°S', '30°S', '0°', '30°N', '60°N', '90°N'], rotation=90, ha='right', va='center', fontsize=12)
    
    axes[0].set_xlabel(r'Log$_{10}$ Area$_{\mathrm{loss}}$', fontsize=12, labelpad=1)
    axes[0].axhline(0, color='gray', linestyle='--', linewidth=1.5) 
    
    axes[0].locator_params(axis='x', nbins=4)
    axes[0].tick_params(axis='both', which='major', labelsize=12)
    
    bbox_props = dict(facecolor='none', edgecolor='none', pad=0.1)
    axes[0].text(0.5, 0.95, results_text['Log_Area_Loss']['North'], transform=axes[0].transAxes, 
                 ha='center', va='top', fontsize=9, bbox=bbox_props)
    axes[0].text(0.5, 0.05, results_text['Log_Area_Loss']['South'], transform=axes[0].transAxes, 
                 ha='center', va='bottom', fontsize=9, bbox=bbox_props)

    # 图 1d
    sns.scatterplot(data=lat_profile, x='Temp_Inc', y='Latitude', 
                    ax=axes[1], color=SSP245_COLOR, alpha=0.8, s=40, edgecolor='white', linewidth=0.8)
    sns.regplot(data=lat_north, x='Temp_Inc', y='Latitude', 
                ax=axes[1], scatter=False, lowess=False, color=LINE_COLOR, line_kws={'linewidth': 2.5})
    sns.regplot(data=lat_south, x='Temp_Inc', y='Latitude', 
                ax=axes[1], scatter=False, lowess=False, color=LINE_COLOR, line_kws={'linewidth': 2.5})
    
    axes[1].set_xlabel(r'Temp.$_{\mathrm{incr.}}$', fontsize=12, labelpad=1)
    axes[1].axhline(0, color='gray', linestyle='--', linewidth=1.5) 
    
    axes[1].locator_params(axis='x', nbins=4)
    axes[1].tick_params(axis='both', which='major', labelsize=12)
    
    bbox_props = dict(facecolor='none', edgecolor='none', pad=0.1)
    axes[1].text(0.5, 0.95, results_text['Temp_Inc']['North'], transform=axes[1].transAxes, 
                 ha='center', va='top', fontsize=9, bbox=bbox_props)
    axes[1].text(0.5, 0.05, results_text['Temp_Inc']['South'], transform=axes[1].transAxes, 
                 ha='center', va='bottom', fontsize=9, bbox=bbox_props)

    for ax in axes:
        ax.grid(axis='both', linestyle='--', alpha=0.5)
    sns.despine()

    out_fig_cd = os.path.join(OUTPUT_DIR, f"Figure1cd_LatProfiles_Split_{SCENARIO}.png")
    
    plt.savefig(out_fig_cd, dpi=300, transparent=True)
    print(f"✅ 图 1c & 1d 已成功保存至: {out_fig_cd}")
    plt.close()

# =====================================================================
# 5. 主程序执行顺序
# =====================================================================
if __name__ == "__main__":
    process_data()          
    generate_figure_1b()    
    generate_figure_1cd()   
