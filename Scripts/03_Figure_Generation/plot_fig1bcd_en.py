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

warnings.filterwarnings("ignore")

# =====================================================================
# 1. Configuration and Global Parameters
# =====================================================================
INPUT_EXCEL_BASELINE = r"G:\github\GIPA\Data\Overall_Summary_260923.xlsx"
PROCESSED_EXCEL = r"G:\github\GIPA\Data\Figure1b_Intermediate_data.xlsx"
OUTPUT_DIR = r"G:\github\GIPA\Figure"

SCENARIO = 'ssp245'
TARGET_CONF = 'Mid_Prob'
TARGET_THRESH = 0.20
SSP245_COLOR = '#7b86a5'
LINE_COLOR = '#333333'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# =====================================================================
# 2. Module A: Data Preprocessing
# =====================================================================
def process_data():
    print("[INFO] Executing Module A: Loading data and computing spatial grid statistics...")
    
    df = pd.read_excel(INPUT_EXCEL_BASELINE)
    df['Thresh'] = pd.to_numeric(df['Thresh'], errors='coerce')
    
    df = df[
        (df['MR'] == 'Baseline') & 
        (df['Sce'] == SCENARIO) & 
        (df['Conf'] == TARGET_CONF) &
        (df['Thresh'].notna()) &
        (np.isclose(df['Thresh'], TARGET_THRESH, atol=1e-3))
    ].copy()
    
    if df.empty:
        print("[WARNING] The filtered dataset is empty. Please verify the filtering parameters.")
        return

    # Extract required variables
    cols_needed = [
        'Sce', 'Center_Lon_2020', 'Center_Lat_2020', 
        'Actual_Tidal_Area', 'InSitu_Area_2100', 'Corridor_Area_2100', 
        'NoAction_2100_Temp_Rise_deg'
    ]
    
    missing_cols = [col for col in cols_needed if col not in df.columns]
    if missing_cols:
        print(f"[ERROR] Missing required columns: {missing_cols}")
        return

    df = df[cols_needed].dropna(subset=['Center_Lon_2020', 'Center_Lat_2020'])
    
    df['Actual_Area_Loss'] = df['Actual_Tidal_Area'] - df['InSitu_Area_2100'] - df['Corridor_Area_2100']
    area_col = 'Actual_Area_Loss'

    df['Lat_Grid'] = np.floor(df['Center_Lat_2020']).astype(int)
    df['Lon_Grid'] = np.floor(df['Center_Lon_2020']).astype(int)

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

    lat_area_df = create_pivot(df, 'Lat_Grid', area_col, (-60, 60), 'Latitude', agg_method='sum', fill_val=np.nan)
    lon_area_df = create_pivot(df, 'Lon_Grid', area_col, (-180, 180), 'Longitude', agg_method='sum', fill_val=np.nan)
    lat_temp_df = create_pivot(df, 'Lat_Grid', 'NoAction_2100_Temp_Rise_deg', (-60, 60), 'Latitude', agg_method='mean', fill_val=np.nan)
    lon_temp_df = create_pivot(df, 'Lon_Grid', 'NoAction_2100_Temp_Rise_deg', (-180, 180), 'Longitude', agg_method='mean', fill_val=np.nan)

    jointplot_df = df.groupby(['Sce', 'Lat_Grid', 'Lon_Grid']).agg(
        Grid_AreaLost=(area_col, 'sum'),
        Grid_TempInc=('NoAction_2100_Temp_Rise_deg', 'mean')
    ).reset_index()
    
    jointplot_df = jointplot_df[jointplot_df['Grid_AreaLost'] > 0]

    with pd.ExcelWriter(PROCESSED_EXCEL, engine='openpyxl') as writer:
        lat_area_df.to_excel(writer, sheet_name='Sheet1_Lat_AreaLost', index=False)
        lon_area_df.to_excel(writer, sheet_name='Sheet2_Lon_AreaLost', index=False)
        lat_temp_df.to_excel(writer, sheet_name='Sheet3_Lat_TempInc', index=False)
        lon_temp_df.to_excel(writer, sheet_name='Sheet4_Lon_TempInc', index=False)
        jointplot_df.to_excel(writer, sheet_name='Sheet5_Jointplot_Data', index=False)
    
    print("[SUCCESS] Module A executed successfully.")

# =====================================================================
# 3. Module B: Generate Figure 1b (Regplot)
# =====================================================================
def generate_figure_1b():
    print(f"\n[INFO] Executing Module B: Generating Figure 1b | Scenario: {SCENARIO}")
    
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
    left_margin_in, right_margin_in = 0.8, 0.2
    bottom_margin_in, top_margin_in = 0.8, 0.2
    
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
    print(f"[SUCCESS] Figure 1b saved to: {out_fig}")
    plt.close()

# =====================================================================
# 4. Module C: Generate Figures 1c & 1d (Latitudinal Profiles)
# =====================================================================
def generate_figure_1cd():
    print(f"\n[INFO] Executing Module C: Generating Figures 1c & 1d | Scenario: {SCENARIO}")
    
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
    
    ax_height_mm, ax_width_mm = 99.81, 25.0
    ax_height_in = ax_height_mm / 25.4 
    ax_width_in = ax_width_mm / 25.4   
    
    bottom_margin_in, top_margin_in = 0.9, 0.6 
    left_margin_in, right_margin_in = 0.9, 0.2 
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
    
    # Panel 1c
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

    # Panel 1d
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
    
    axes[1].text(0.5, 0.95, results_text['Temp_Inc']['North'], transform=axes[1].transAxes, 
                 ha='center', va='top', fontsize=9, bbox=bbox_props)
    axes[1].text(0.5, 0.05, results_text['Temp_Inc']['South'], transform=axes[1].transAxes, 
                 ha='center', va='bottom', fontsize=9, bbox=bbox_props)

    for ax in axes:
        ax.grid(axis='both', linestyle='--', alpha=0.5)
    sns.despine()

    out_fig_cd = os.path.join(OUTPUT_DIR, f"Figure1cd_LatProfiles_Split_{SCENARIO}.png")
    plt.savefig(out_fig_cd, dpi=300, transparent=True)
    print(f"[SUCCESS] Figures 1c & 1d saved to: {out_fig_cd}")
    plt.close()

# =====================================================================
# 5. Main Execution Workflow
# =====================================================================
if __name__ == "__main__":
    process_data()        
    generate_figure_1b()    
    generate_figure_1cd()
