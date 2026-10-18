# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

# =====================================================================
# 1. 配置文件路径与参数设置
# =====================================================================
COMBINED_EXCEL = r"G:\github\GIPA\Data\Master_Baseline_Combined_0923_1013_v2_linkinfo_fixed.xlsx"
OUTPUT_CSV = r"G:\github\GIPA\Data\Figure4_Realm_Data.csv" 
SHEET_NAME = "Sheet1"

# 设定提取条件
TARGET_SCE = 'ssp245'  
TARGET_THRESH = 0.20
TARGET_CONF = 'Mid_Prob'

# 大洲名称到数字代码的映射字典
REALM_CODE_DICT = {
    'Arctic': 1,
    'Temperate Northern Atlantic': 2,
    'Temperate Northern Pacific': 3,
    'Tropical Atlantic': 4,
    'Western Indo-Pacific': 5,
    'Central Indo-Pacific': 6,
    'Eastern Indo-Pacific': 7,
    'Tropical Eastern Pacific': 8,
    'Temperate South America': 9,
    'Temperate Southern Africa': 10,
    'Temperate Australasia': 11,
    'Southern Ocean': 12
}

def generate_arcgis_realm_data():
    print(f"正在读取文件: {COMBINED_EXCEL}...")
    
    try:
        df_all = pd.read_excel(COMBINED_EXCEL, sheet_name=SHEET_NAME)
    except Exception as e:
        print(f"读取 Excel 文件失败: {e}")
        return
    
    # 筛选指定情景与参数的数据
    df_filtered = df_all[(df_all['Sce'] == TARGET_SCE) & 
                         (df_all['Conf'] == TARGET_CONF) & 
                         (np.isclose(df_all['Thresh'].astype(float), TARGET_THRESH, atol=1e-3))].copy()
                
    if df_filtered.empty:
        print("警告：未找到匹配的基准数据，请检查 Sce/Conf/Thresh 设置。")
        return

    # ==================== A路线：处理干预策略 (MR0/MR1) ====================
    print("正在处理干预策略数据...")
    def clean_mr_name(mr_str):
        mr_str_lower = str(mr_str).lower()
        if 'mr0' in mr_str_lower: return 'MR0'
        if 'mr1' in mr_str_lower: return 'MR1'
        return 'Drop'
        
    df_filtered['MR_Clean'] = df_filtered['MR'].apply(clean_mr_name)
    df_mr = df_filtered[df_filtered['MR_Clean'] != 'Drop'].copy()
    
    # 计算干预下的气候抗性面积
    df_mr['Survival_2100'] = df_mr['原地面积_2100'].fillna(0) + df_mr['廊道面积_2100'].fillna(0)
    
    for col in ['PA_Name', 'REALM']:
        if col in df_mr.columns:
            df_mr[col] = df_mr[col].fillna('Unknown')

    # 数据透视，将同一保护地的不同策略横向展开
    pivot_patch = pd.pivot_table(
        df_mr, 
        index=['PA_Name', 'REALM'],
        columns='MR_Clean',
        values='Survival_2100',
        aggfunc='sum'
    ).reset_index()
    
    # 确保 MR0, MR1 列存在
    for mr in ['MR0', 'MR1']:
        if mr not in pivot_patch.columns:
            pivot_patch[mr] = 0
        pivot_patch[mr] = pivot_patch[mr].fillna(0)

    # ==================== B路线：处理无干预 (Baseline/NoAction) ====================
    print("正在处理无干预数据...")
    
    baseline_mask = df_filtered['MR'].astype(str).str.lower().str.contains('baseline|noaction')
    if baseline_mask.any():
        df_baseline = df_filtered[baseline_mask].drop_duplicates(subset=['PA_Name']).copy()
    else:
        # 容错机制：如果没有明确标示 baseline，直接返回空，避免报错
        df_baseline = pd.DataFrame(columns=['PA_Name', '初始潮滩_面积', 'NoAction_2100'])
    
    if not df_baseline.empty:
        # 直接提取 Baseline 状态下的 2100 年气候抗性面积
        df_baseline['NoAction_2100'] = df_baseline['原地面积_2100'].fillna(0) + df_baseline['廊道面积_2100'].fillna(0)
        
        # 提取初始面积列名
        init_col = '初始潮滩_面积' if '初始潮滩_面积' in df_baseline.columns else '实际潮滩_面积'
        baseline_subset = df_baseline[['PA_Name', init_col, 'NoAction_2100']].rename(columns={init_col: '实际潮滩_面积'})
    else:
        baseline_subset = pd.DataFrame(columns=['PA_Name', '实际潮滩_面积', 'NoAction_2100'])

    # ==================== 终极合并与聚合 ====================
    # 合并 A路线与 B路线
    pivot_merged = pd.merge(pivot_patch, baseline_subset, on='PA_Name', how='left')
    pivot_merged['实际潮滩_面积'] = pivot_merged['实际潮滩_面积'].fillna(0)
    pivot_merged['NoAction_2100'] = pivot_merged['NoAction_2100'].fillna(0)

    print("正在按 REALM 进行地理上卷聚合...")
    
    # 按 REALM 聚合数据
    realm_agg = pivot_merged.groupby(['REALM']).agg({
        '实际潮滩_面积': 'sum',
        'NoAction_2100': 'sum',
        'MR0': 'sum',
        'MR1': 'sum'
    }).reset_index()
    
    # 插入 RLM_CODE 编码列
    realm_agg.insert(0, 'RLM_CODE', realm_agg['REALM'].map(REALM_CODE_DICT))
    realm_agg['RLM_CODE'] = realm_agg['RLM_CODE'].fillna(99).astype(int)
    realm_agg = realm_agg.sort_values(by='RLM_CODE')
    
    # ==================== 结果输出 ====================
    realm_agg.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"\n数据已成功保存至: {OUTPUT_CSV}")
    print(f"汇总了 {len(realm_agg)} 个 REALM 大区的数据。")

if __name__ == "__main__":
    generate_arcgis_realm_data()
