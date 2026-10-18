# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr, mannwhitneyu
import warnings
import matplotlib.patches as mpatches

# =====================================================================
# 1. 配置文件路径与参数设置
# =====================================================================
# 屏蔽 Seaborn 和 Pandas 版本冲突产生的 FutureWarning，保持控制台整洁
warnings.filterwarnings('ignore')

INPUT_EXCEL = r"G:\github\GIPA\Data\Master_Baseline_Combined_0923_1013_v2_linkinfo_fixed.xlsx"
OUTPUT_FIG = r"G:\github\GIPA\Figure\Figure3.png"

TARGET_SCE = 'ssp245'
TARGET_MR = 'MR1'
TARGET_THRESH = 0.20
TARGET_CONF = 'Mid_Prob'

# =====================================================================
# 2. 数据读取与深度清洗
# =====================================================================
def load_and_prepare_driver_data():
    print("正在读取数据并进行清洗...")
    try:
        df = pd.read_excel(INPUT_EXCEL, sheet_name="Sheet2_Summary")
    except ValueError:
        df = pd.read_excel(INPUT_EXCEL)
    
    # 1. 基础过滤：锁定特定情景和概率
    df = df[(df['Sce'] == TARGET_SCE) & 
            (df['MR'].str.contains(TARGET_MR, case=False, na=False)) &
            (df['Conf'] == TARGET_CONF) & 
            (np.isclose(df['Thresh'].astype(float), TARGET_THRESH, atol=1e-3))]
            
    # 2. 终极修复：剔除因 GIS 浮点误差导致的微小负数，以及本来就没有潮滩的保护地
    df = df[df['实际潮滩_面积'] > 1e-4].copy()
    
    # 3. 计算存活面积与比率
    df['Survival_Area_2100'] = df['原地面积_2100'].fillna(0) + df['廊道面积_2100'].fillna(0)
    df['Survival_Ratio'] = (df['Survival_Area_2100'] / df['实际潮滩_面积']) * 100.0
    
    # 此时分母完全干净，存活率保证在客观真实的 [0, 100] 区间
    df['Survival_Ratio'] = df['Survival_Ratio'].fillna(0)
    
    # 4. 获取半球与纬度偏移量信息
    if '2020中心纬度' in df.columns:
        df['Hemisphere'] = np.where(df['2020中心纬度'] > 0, 'Northern', 'Southern')
    else:
        df['Hemisphere'] = 'Unknown'
        
    shift_col = '纬度差' if '纬度差' in df.columns else '平均轨迹长度(km)'
    if shift_col in df.columns:
        df['Shift_Magnitude'] = df[shift_col]
    else:
        df['Shift_Magnitude'] = np.nan
        
    # 5. 剔除缺失自变量（面积、岸线、走向）的行
    df_clean = df.dropna(subset=['PA_Total_Area', 'Shoreline_Length', 'Orientation_Class'])
    return df_clean

# =====================================================================
# 3. 绘制顶级期刊 2x2 面板图
# =====================================================================
def plot_drivers(df):
    
    df = df[df['Survival_Area_2100'] > 0].copy()
    
    sns.set_theme(style="ticks", context="paper", font_scale=2.2)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 14)) 
    
    # -----------------------------------------------------------------
    # Panel a: 保护地总面积 vs 抗性面积
    # -----------------------------------------------------------------
    ax_a = axes[0, 0]
    x_a = np.log10(df['PA_Total_Area'] + 1)
    y_a = np.log10(df['Survival_Area_2100'] + 1)
    
    sns.regplot(x=x_a, y=y_a, ax=ax_a, 
                scatter_kws={'alpha':0.8, 's':100, 'color':'#7b86a5', 'edgecolors':'white', 'linewidths':1.5}, 
                line_kws={'color':'#333333', 'linewidth':4})
    
    corr_a, p_a = spearmanr(df['PA_Total_Area'], df['Survival_Area_2100'])
    sig_a = "***" if p_a < 0.001 else "**" if p_a < 0.01 else "*" if p_a < 0.05 else "ns"
    
    ax_a.text(0.05, 0.95, f"Spearman's $\\rho$ = {corr_a:.2f}\n$p$ = {p_a:.2e}{sig_a}", 
              transform=ax_a.transAxes, fontsize=20, verticalalignment='top',
              bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', boxstyle='round,pad=0.4'))
    
    ax_a.set_title('a', fontweight='bold', loc='left', fontsize=28, pad=15)
    ax_a.set_xlabel('Log$_{10}$ (Total area of PA, $km^2$)', fontweight='bold')
    ax_a.set_ylabel('Log$_{10}$ (Climate-resistant area, $km^2$)', fontweight='bold')
    
    # -----------------------------------------------------------------
    # Panel b: 岸线总长度 vs 抗性面积
    # -----------------------------------------------------------------
    ax_b = axes[0, 1]
    x_b = np.log10(df['Shoreline_Length'] + 1)
    y_b = np.log10(df['Survival_Area_2100'] + 1)
    
    sns.regplot(x=x_b, y=y_b, ax=ax_b, 
                scatter_kws={'alpha':0.8, 's':100, 'color':'#7b86a5', 'edgecolors':'white', 'linewidths':1.5}, 
                line_kws={'color':'#333333', 'linewidth':4})
    
    corr_b, p_b = spearmanr(df['Shoreline_Length'], df['Survival_Area_2100'])
    sig_b = "***" if p_b < 0.001 else "**" if p_b < 0.01 else "*" if p_b < 0.05 else "ns"
    
    ax_b.text(0.05, 0.95, f"Spearman's $\\rho$ = {corr_b:.2f}\n$p$ = {p_b:.2e}{sig_b}", 
              transform=ax_b.transAxes, fontsize=20, verticalalignment='top',
              bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', boxstyle='round,pad=0.4'))
    
    ax_b.set_title('b', fontweight='bold', loc='left', fontsize=28, pad=15)
    ax_b.set_xlabel('Log$_{10}$ (Shoreline length, km)', fontweight='bold')
    ax_b.set_ylabel('Log$_{10}$ (Climate-resistant area, $km^2$)', fontweight='bold')
    
    # -----------------------------------------------------------------
    # Panel c: 岸线走向 (N-S vs E-W)
    # -----------------------------------------------------------------
    ax_c = axes[1, 0]
    df_orient = df[df['Orientation_Class'].isin(['N-S', 'E-W'])]
    
    orient_palette = {'E-W': '#7f8b9f', 'N-S': '#9cbba5'}
    
    sns.boxplot(x='Orientation_Class', y='Survival_Ratio', data=df_orient, ax=ax_c,
                palette=orient_palette, width=0.5, linewidth=2.5, showfliers=False, 
                boxprops=dict(edgecolor='#333333', alpha=0.8),
                medianprops=dict(color='#333333', linewidth=3),
                whiskerprops=dict(color='#333333', linewidth=2.5),
                capprops=dict(color='#333333', linewidth=2.5))
                
    sns.stripplot(x='Orientation_Class', y='Survival_Ratio', data=df_orient, ax=ax_c,
                  color='#7b86a5', alpha=0.8, size=10, jitter=True, edgecolor='white', linewidth=1)
    
    ns_vals = df_orient[df_orient['Orientation_Class'] == 'N-S']['Survival_Ratio']
    ew_vals = df_orient[df_orient['Orientation_Class'] == 'E-W']['Survival_Ratio']
    
    if len(ns_vals) > 0 and len(ew_vals) > 0:
        stat, p_c = mannwhitneyu(ns_vals, ew_vals)
        sig_marker = "***" if p_c < 0.001 else "**" if p_c < 0.01 else "*" if p_c < 0.05 else "ns"
        
        y_max = df_orient['Survival_Ratio'].max()
        ax_c.plot([0, 0, 1, 1], [y_max+5, y_max+8, y_max+8, y_max+5], lw=2.5, color='black')
        
        ax_c.text(0.5, y_max+9, f"$p$ = {p_c:.2f}{sig_marker}", ha='center', va='bottom', color='black', fontsize=20)
        
        # 打印 图c (走向) 的均值和偏差 (标准差) 
        print("\n" + "="*40)
        print("📊 图3c (Orientation_Class) 统计信息输出：")
        print(f"  ▶ E-W 走向: 均值(Mean) = {ew_vals.mean():.2f}%, 偏差(Std) = {ew_vals.std():.2f}%")
        print(f"  ▶ N-S 走向: 均值(Mean) = {ns_vals.mean():.2f}%, 偏差(Std) = {ns_vals.std():.2f}%")
        print("="*40)
        
    ax_c.set_ylim(-5, 120) 
    ax_c.set_title('c', fontweight='bold', loc='left', fontsize=28, pad=15)
    ax_c.set_xlabel('Orientation of PA', fontweight='bold')
    ax_c.set_ylabel('Climate-resistant area ratios (%)', fontweight='bold')
    
    # -----------------------------------------------------------------
    # Panel d: 南北半球偏移距离分布对比
    # -----------------------------------------------------------------
    ax_d = axes[1, 1]
    df_hemi = df[df['Hemisphere'].isin(['Northern', 'Southern'])].dropna(subset=['Shift_Magnitude'])
    
    hemi_palette = {'Northern':'#6b8a9e', 'Southern':'#d4a373'}
    
    if not df_hemi.empty and len(df_hemi) > 2:
        unique_hemis = df_hemi['Hemisphere'].unique()
        
        if len(unique_hemis) == 1:
            hemi_name = unique_hemis[0]
            sns.kdeplot(data=df_hemi, x='Shift_Magnitude', fill=True, ax=ax_d, 
                        color=hemi_palette[hemi_name], 
                        alpha=0.6, linewidth=3, label=hemi_name)
        else:
            sns.kdeplot(data=df_hemi, x='Shift_Magnitude', hue='Hemisphere', fill=True, 
                        ax=ax_d, palette=hemi_palette, 
                        alpha=0.6, linewidth=3, common_norm=False)
        
        if 'Northern' in unique_hemis and 'Southern' in unique_hemis:
            mean_N = df_hemi[df_hemi['Hemisphere'] == 'Northern']['Shift_Magnitude'].mean()
            std_N = df_hemi[df_hemi['Hemisphere'] == 'Northern']['Shift_Magnitude'].std()
            ax_d.axvline(mean_N, color='#455e6e', linestyle='--', linewidth=2.5)
            
            mean_S = df_hemi[df_hemi['Hemisphere'] == 'Southern']['Shift_Magnitude'].mean()
            std_S = df_hemi[df_hemi['Hemisphere'] == 'Southern']['Shift_Magnitude'].std()
            ax_d.axvline(mean_S, color='#b07d4b', linestyle='--', linewidth=2.5)
            
            shift_N = df_hemi[df_hemi['Hemisphere'] == 'Northern']['Shift_Magnitude']
            shift_S = df_hemi[df_hemi['Hemisphere'] == 'Southern']['Shift_Magnitude']
            
            stat_d, p_d = mannwhitneyu(shift_N, shift_S)
            sig_marker_d = "***" if p_d < 0.001 else "**" if p_d < 0.01 else "*" if p_d < 0.05 else "ns"
            
            ax_d.text(0.05, 0.95, f"Mann-Whitney U\n$p$ = {p_d:.2e} {sig_marker_d}", 
                      transform=ax_d.transAxes, fontsize=20, verticalalignment='top',
                      bbox=dict(facecolor='white', alpha=0.9, edgecolor='gray', boxstyle='round,pad=0.4'))
                      
            # 打印 图d (南北半球) 的均值和偏差 (标准差)
            print("\n" + "="*40)
            print("🌍 图3d (Hemisphere Shift) 统计信息输出：")
            print(f"  ▶ 北半球 (Northern): 均值(Mean) = {mean_N:.2f}°, 偏差(Std) = {std_N:.2f}°")
            print(f"  ▶ 南半球 (Southern): 均值(Mean) = {mean_S:.2f}°, 偏差(Std) = {std_S:.2f}°")
            print("="*40 + "\n")
        
        legend_patches = [mpatches.Patch(color=hemi_palette[h], label=h, alpha=0.6) for h in sorted(unique_hemis)]
        ax_d.legend(handles=legend_patches, title='Hemisphere', loc='upper right', title_fontsize=20, fontsize=18)
        
    ax_d.set_title('d', fontweight='bold', loc='left', fontsize=28, pad=15)
    ax_d.set_xlabel('Latitudinal shift (°)', fontweight='bold')
    ax_d.set_ylabel('Density', fontweight='bold')
    
    sns.despine()
    plt.tight_layout()
    
    plt.savefig(OUTPUT_FIG, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"✅ 图表已保存至: {OUTPUT_FIG}")
    plt.show()

if __name__ == "__main__":
    df = load_and_prepare_driver_data()
    if not df.empty:
        plot_drivers(df)
    else:
        print("❌ 数据为空或缺少必要的补充字段，请检查 Excel 文件！")
