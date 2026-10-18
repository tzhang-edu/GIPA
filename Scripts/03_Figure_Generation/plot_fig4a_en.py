# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np

# =====================================================================
# 1. Configuration and Parameters
# =====================================================================
COMBINED_EXCEL = r"G:\github\GIPA\Data\Overall_Summary_260923.xlsx"
OUTPUT_CSV = r"G:\github\GIPA\Data\Figure4_Realm_Data.csv" 
SHEET_NAME = "Sheet1"

TARGET_SCE = 'ssp245'  
TARGET_THRESH = 0.20
TARGET_CONF = 'Mid_Prob'

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
    print(f"[INFO] Reading file: {COMBINED_EXCEL}...")
    
    try:
        df_all = pd.read_excel(COMBINED_EXCEL, sheet_name=SHEET_NAME)
    except Exception as e:
        print(f"[ERROR] Failed to read Excel file: {e}")
        return
    
    # Filter dataset based on target scenario, confidence, and threshold
    df_filtered = df_all[(df_all['Sce'] == TARGET_SCE) & 
                         (df_all['Conf'] == TARGET_CONF) & 
                         (np.isclose(df_all['Thresh'].astype(float), TARGET_THRESH, atol=1e-3))].copy()
                
    if df_filtered.empty:
        print("[WARNING] No matching baseline data found. Please check Sce/Conf/Thresh parameters.")
        return

    # =================================================================
    # Route A: Process Intervention Strategies (MR0 / MR1)
    # =================================================================
    print("[INFO] Processing intervention strategy data...")
    
    def clean_mr_name(mr_str):
        mr_str_lower = str(mr_str).lower()
        if 'mr0' in mr_str_lower: return 'MR0'
        if 'mr1' in mr_str_lower: return 'MR1'
        return 'Drop'
        
    df_filtered['MR_Clean'] = df_filtered['MR'].apply(clean_mr_name)
    df_mr = df_filtered[df_filtered['MR_Clean'] != 'Drop'].copy()
    
    # Calculate climate-resistant area under intervention
    df_mr['Survival_2100'] = df_mr['InSitu_Area_2100'].fillna(0) + df_mr['Corridor_Area_2100'].fillna(0)
    
    for col in ['PA_Name', 'REALM']:
        if col in df_mr.columns:
            df_mr[col] = df_mr[col].fillna('Unknown')

    # Pivot table to reshape strategy data horizontally
    pivot_patch = pd.pivot_table(
        df_mr, 
        index=['PA_Name', 'REALM'],
        columns='MR_Clean',
        values='Survival_2100',
        aggfunc='sum'
    ).reset_index()
    
    # Ensure all required MR columns exist
    for mr in ['MR0', 'MR1']:
        if mr not in pivot_patch.columns:
            pivot_patch[mr] = 0
        pivot_patch[mr] = pivot_patch[mr].fillna(0)

    # =================================================================
    # Route B: Process Baseline (NoAction) Data
    # =================================================================
    print("[INFO] Processing baseline (NoAction) climate-resistant data...")
    
    baseline_mask = df_filtered['MR'].astype(str).str.lower().str.contains('baseline|noaction')
    if baseline_mask.any():
        df_baseline = df_filtered[baseline_mask].drop_duplicates(subset=['PA_Name']).copy()
    else:
        df_baseline = pd.DataFrame(columns=['PA_Name', 'Actual_Tidal_Area', 'NoAction_2100'])
    
    if not df_baseline.empty:
        df_baseline['NoAction_2100'] = df_baseline['InSitu_Area_2100'].fillna(0) + df_baseline['Corridor_Area_2100'].fillna(0)
        baseline_subset = df_baseline[['PA_Name', 'Actual_Tidal_Area', 'NoAction_2100']]
    else:
        baseline_subset = pd.DataFrame(columns=['PA_Name', 'Actual_Tidal_Area', 'NoAction_2100'])

    # =================================================================
    # Merge and Geographical Aggregation
    # =================================================================
    pivot_merged = pd.merge(pivot_patch, baseline_subset, on='PA_Name', how='left')
    pivot_merged['Actual_Tidal_Area'] = pivot_merged['Actual_Tidal_Area'].fillna(0)
    pivot_merged['NoAction_2100'] = pivot_merged['NoAction_2100'].fillna(0)

    print("[INFO] Aggregating data geographically by REALM...")
    
    realm_agg = pivot_merged.groupby(['REALM']).agg({
        'Actual_Tidal_Area': 'sum',
        'NoAction_2100': 'sum',
        'MR0': 'sum',
        'MR1': 'sum'
    }).reset_index()
    
    # Insert RLM_CODE for GIS mapping
    realm_agg.insert(0, 'RLM_CODE', realm_agg['REALM'].map(REALM_CODE_DICT))
    realm_agg['RLM_CODE'] = realm_agg['RLM_CODE'].fillna(99).astype(int)
    realm_agg = realm_agg.sort_values(by='RLM_CODE')
    
    # =================================================================
    # Export Results
    # =================================================================
    realm_agg.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
    print(f"[SUCCESS] Data successfully saved to: {OUTPUT_CSV}")
    print(f"[INFO] Aggregated data for {len(realm_agg)} REALM regions.")

if __name__ == "__main__":
    generate_arcgis_realm_data()
