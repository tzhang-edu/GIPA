# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# =====================================================================
# 1. Configuration and Global Parameters
# =====================================================================
FILE_PATH = r"G:\github\GIPA\Data\Overall_Summary_260923.xlsx"

TARGET_MR = 'baseline'
TARGET_THRESH = 0.20
EXPECTED_PA_COUNT = 665

# =====================================================================
# 2. Main Processing Function
# =====================================================================
def calculate_combined_stats():
    print(f"[INFO] Initializing statistical analysis...")
    print(f"[INFO] Reading dataset: {FILE_PATH}")
    
    try:
        df = pd.read_excel(FILE_PATH)
        df.columns = df.columns.str.strip()
        
        # Verify required English open-source columns exist
        required_cols = [
            'Sce', 'MR', 'Conf', 'Thresh', 'ISO3', 'PA_Total_Area', 'Actual_Tidal_Area', 
            'Total_Grids', 'Actual_Tidal_Grids', 'InSitu_Area_2100', 
            'Corridor_Area_2100', 'NoAction_2100_Temp_Rise_deg'
        ]
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"[ERROR] Missing required columns: {missing_cols}")
            print(f"[INFO] Available columns: {df.columns.tolist()[:10]}...")
            return

        ssp_scenarios = ['ssp126', 'ssp245', 'ssp370', 'ssp585']
        conf_levels = ['Mid_Prob', 'Low_Prob', 'High_Prob']
        
        print("[INFO] Processing scenarios and computing structural/loss metrics...")
        
        # Outer loop: Climate Scenarios (SSPs)
        for ssp in ssp_scenarios:
            print("\n" + "="*75)
            print(f"[INFO] Summary Statistics | Scenario: {ssp.upper()} | MR: Baseline | Thresh: 0.20")
            print("="*75)
            
            base_mask = (
                (df['MR'].astype(str).str.strip().str.lower() == TARGET_MR) &
                (df['Sce'].astype(str).str.strip().str.lower() == ssp) &
                (np.isclose(df['Thresh'].astype(float), TARGET_THRESH, atol=1e-3))
            )
            
            # Inner loop: Confidence Levels
            for conf in conf_levels:
                final_mask = base_mask & (df['Conf'].astype(str).str.strip() == conf)
                filtered_df = df[final_mask].copy()
                
                row_count = len(filtered_df)
                
                if row_count == 0:
                    print(f"[WARNING] Confidence: {conf} - No data found matching criteria.")
                    continue
                
                # Fill NAs to prevent NaN propagation during mathematical operations
                filtered_df['Actual_Tidal_Area'] = filtered_df['Actual_Tidal_Area'].fillna(0)
                filtered_df['InSitu_Area_2100'] = filtered_df['InSitu_Area_2100'].fillna(0)
                filtered_df['Corridor_Area_2100'] = filtered_df['Corridor_Area_2100'].fillna(0)
                
                # --- Metrics Calculation ---
                sum_area = filtered_df['PA_Total_Area'].sum()
                sum_tide = filtered_df['Actual_Tidal_Area'].sum()
                iso3_count = filtered_df['ISO3'].nunique()
                
                sum_total_grid = filtered_df['Total_Grids'].sum()
                sum_tide_grid = filtered_df['Actual_Tidal_Grids'].sum()
                
                lost_area_series = filtered_df['Actual_Tidal_Area'] - filtered_df['InSitu_Area_2100'] - filtered_df['Corridor_Area_2100']
                total_lost_area = lost_area_series.sum()
                
                temp_mean = filtered_df['NoAction_2100_Temp_Rise_deg'].mean()
                temp_std = filtered_df['NoAction_2100_Temp_Rise_deg'].std()
                
                # --- Output Reporting ---
                status_flag = "[SUCCESS]" if row_count == EXPECTED_PA_COUNT else "[WARNING]"
                
                print(f"▶ Confidence Level: {conf}")
                print(f"    - Protected Areas (N):   {row_count} {status_flag}")
                print(f"    - Unique ISO3 Codes:     {iso3_count}")
                print(f"    - PA Total Area:         {sum_area:,.2f} km²")
                print(f"    - Actual Tidal Area:     {sum_tide:,.2f} km²")
                print(f"    - Initial Grid Cells:    {sum_total_grid:,.0f}")
                print(f"    - Final Tidal Grids:     {sum_tide_grid:,.0f}")
                print(f"    - Total Area Loss:       {total_lost_area:,.2f} km²")
                print(f"    - Local Temp Increase:   {temp_mean:.2f} ± {temp_std:.2f} °C\n")

    except FileNotFoundError:
        print(f"[ERROR] Target file not found. Verify path: {FILE_PATH}")
    except Exception as e:
        print(f"[ERROR] Execution failed with exception: {e}")

if __name__ == "__main__":
    calculate_combined_stats()
