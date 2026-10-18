# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

# =====================================================================
# 1. Configuration (仅保留需从 Excel 读取的原始字段)
# =====================================================================
FILE_PATH = r"G:\github\GIPA\Data\Master_Baseline_Combined_0923_1013_v2_linkinfo_fixed.xlsx"
OUTPUT_PATH = r"G:\github\GIPA\Data\Figure1a_Bivariate_Map.csv"

TARGET_SCE = 'ssp245'
TARGET_MR = 'Baseline'
TARGET_CONF = 'Mid_Prob'
TARGET_THRESH = 0.20  

# 从 Excel 读取的基础列
COL_TEMP_RISE = 'NoAction_2100原址升温(度)' 
COL_ACTUAL_AREA = '实际潮滩_面积'
COL_INSITU_2100 = '原地面积_2100'
COL_CORRIDOR_2100 = '廊道面积_2100'

# =====================================================================
# 2. Data Processing
# =====================================================================
def process_bivariate_map_data():
    print("Loading data and filtering target scenarios...")
    df = pd.read_excel(FILE_PATH)

    # 🌟 核心修复：安全转换 Thresh 列
    # 遇到类似 'MR1' 的错位字符串会强制转为 NaN，避免 astype(float) 崩溃
    df['Thresh'] = pd.to_numeric(df['Thresh'], errors='coerce')

    # 过滤目标数据 (加入 Thresh == 0.2，并确保剔除 NaN)
    df_map = df[
        (df['MR'] == TARGET_MR) & 
        (df['Sce'] == TARGET_SCE) & 
        (df['Conf'] == TARGET_CONF) &
        (df['Thresh'].notna()) & 
        (np.isclose(df['Thresh'], TARGET_THRESH, atol=1e-3))
    ].copy()
    
    if df_map.empty:
        print(f"⚠️ 警告：筛选后数据为空，请检查筛选条件或原始 Excel 数据。")
        return
        
    df_map = df_map.drop_duplicates(subset=['PA_Name'])

    # 计算丧失面积
    print("Calculating actual area loss...")
    df_map['实际潮滩丧失_面积'] = (
        df_map[COL_ACTUAL_AREA].fillna(0) - 
        df_map[COL_INSITU_2100].fillna(0) - 
        df_map[COL_CORRIDOR_2100].fillna(0)
    )

    # 提取做图所需的数据
    map_columns = ['PA_Name', '实际潮滩丧失_面积', COL_TEMP_RISE]
    df_map_clean = df_map[map_columns].copy()

    # 填充缺失值
    print("Masking NaN values in area loss with -9999...")
    df_map_clean['实际潮滩丧失_面积'] = df_map_clean['实际潮滩丧失_面积'].fillna(-9999)

    # =================================================================
    # 重命名并强制排序 (A列为PA_Name，B/C列为目标英文)
    # =================================================================
    df_map_clean = df_map_clean.rename(columns={
        '实际潮滩丧失_面积': 'intertidal area loss (km2)',
        COL_TEMP_RISE: 'temperature increase(℃)'
    })
    
    # 强制固定列顺序
    final_columns = [
        'PA_Name', 
        'intertidal area loss (km2)', 
        'temperature increase(℃)'
    ]
    df_map_clean = df_map_clean[final_columns]

    # 导出文件
    df_map_clean.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
    print(f"✅ Success! Extracted and masked data for {len(df_map_clean)} PAs.")
    print(f"File saved to: {OUTPUT_PATH}")

if __name__ == "__main__":
    process_bivariate_map_data()
