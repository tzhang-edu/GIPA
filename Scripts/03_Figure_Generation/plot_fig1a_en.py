# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

# =====================================================================
# 1. Configuration
# =====================================================================
FILE_PATH = r"G:\github\GIPA\Data\Overall_Summary_260923.xlsx"
OUTPUT_PATH = r"G:\github\GIPA\Data\Figure1a_Bivariate_Map.csv"

TARGET_SCE = 'ssp245'
TARGET_MR = 'Baseline'
TARGET_CONF = 'Mid_Prob'
TARGET_THRESH = 0.20  

COL_TEMP_RISE = 'NoAction_2100_Temp_Rise_deg' 
COL_ACTUAL_AREA = 'Actual_Tidal_Area'
COL_INSITU_2100 = 'InSitu_Area_2100'
COL_CORRIDOR_2100 = 'Corridor_Area_2100'

# =====================================================================
# 2. Data Processing
# =====================================================================
def process_bivariate_map_data():
    print("Loading data and filtering target scenarios...")
    df = pd.read_excel(FILE_PATH)

    # 安全转换 Thresh 列
    df['Thresh'] = pd.to_numeric(df['Thresh'], errors='coerce')

    # 过滤目标数据
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
    df_map['Area_Loss'] = (
        df_map[COL_ACTUAL_AREA].fillna(0) - 
        df_map[COL_INSITU_2100].fillna(0) - 
        df_map[COL_CORRIDOR_2100].fillna(0)
    )

    # 提取作图数据
    map_columns = ['PA_Name', 'Area_Loss', COL_TEMP_RISE]
    df_map_clean = df_map[map_columns].copy()

    # 填充缺失值
    print("Masking NaN values in area loss with -9999...")
    df_map_clean['Area_Loss'] = df_map_clean['Area_Loss'].fillna(-9999)

    # 重命名并排序
    df_map_clean = df_map_clean.rename(columns={
        'Area_Loss': 'intertidal area loss (km2)',
        COL_TEMP_RISE: 'temperature increase(℃)'
    })
    
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
