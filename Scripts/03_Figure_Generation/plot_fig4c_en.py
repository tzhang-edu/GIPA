# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import warnings

warnings.filterwarnings("ignore")

# =====================================================================
# 1. Global Configuration and Parameters
# =====================================================================
INPUT_EXCEL = r"G:\github\GIPA\Data\Overall_Summary_260923.xlsx" 
OUTPUT_DIR = r"G:\github\GIPA\Figure"  

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

COLOR_BASELINE = '#C58473'  
COLOR_BA       = '#E09F3E'   
COLOR_BAMR1    = '#8CA693'

# Mapping dictionary for Marine Ecoregions of the World (MEOW)
MEOW_DICT = {
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

# =====================================================================
# 2. Data Processing and Climate-Resistant Ratio Calculation
# =====================================================================
print("[INFO] Reading and processing Panel c statistical data...")

try:
    df = pd.read_excel(INPUT_EXCEL, sheet_name="Sheet2_Summary")
except ValueError:
    df = pd.read_excel(INPUT_EXCEL)

# Filter dataset for target scenario and threshold 
df_ssp245 = df[
    (df['Sce'] == 'ssp245') & 
    (np.isclose(df['Thresh'].astype(float), 0.20, atol=1e-3))
    #&  
    #(df['Actual_Tidal_Area'] > 1.0)
].copy()

# Map intervention strategies
def map_strategy(mr_val):
    val = str(mr_val).strip().lower()
    if 'baseline' in val or 'noaction' in val: return 'Baseline'
    if 'mr0' in val: return 'BA'
    if 'mr1' in val: return 'BA+MR1'
    return None

df_ssp245['Strategy'] = df_ssp245['MR'].apply(map_strategy)
df_ssp245 = df_ssp245.dropna(subset=['Strategy'])

# Calculate retained climate-resistant area (In-situ + Corridor)
df_ssp245['Retained_Area'] = df_ssp245['InSitu_Area_2100'].fillna(0) + \
                             df_ssp245['Corridor_Area_2100'].fillna(0)

df_ssp245['Survival_Rate'] = (df_ssp245['Retained_Area'] / df_ssp245['Actual_Tidal_Area']) * 100
df_ssp245['Survival_Rate'] = df_ssp245['Survival_Rate'].clip(0, 100) 

df_pa = df_ssp245.groupby(['REALM', 'PA_Name', 'Strategy'])['Survival_Rate'].mean().reset_index()

# Map REALM names to numerical MEOW codes
df_pa['MEOW_Code'] = df_pa['REALM'].map(MEOW_DICT)
df_pa = df_pa.dropna(subset=['MEOW_Code']) 
df_pa['MEOW_Code'] = df_pa['MEOW_Code'].astype(int)
df_pa = df_pa.sort_values(by=['MEOW_Code'])

# =====================================================================
# 3. Render High-Tier Journal Bar Plot
# =====================================================================
print("[INFO] Generating high-contrast visualization layout...")

sns.set_theme(
    style="ticks", 
    rc={
        "font.size": 12,
        "axes.titlesize": 12,
        "axes.labelsize": 12,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12
    }
)

fig_width_mm = 260.0
fig_width_in = fig_width_mm / 25.4
fig_height_in = 2.875 

fig, ax = plt.subplots(figsize=(fig_width_in, fig_height_in))

sns.barplot(
    data=df_pa, 
    x='MEOW_Code', 
    y='Survival_Rate', 
    hue='Strategy',
    hue_order=['Baseline', 'BA', 'BA+MR1'],
    palette={'Baseline': COLOR_BASELINE, 'BA': COLOR_BA, 'BA+MR1': COLOR_BAMR1},
    errorbar='sd',       
    capsize=0.1,         
    errwidth=1.5,
    ax=ax,
    edgecolor='#333333', 
    linewidth=1.2,
    alpha=0.85
)

sns.stripplot(
    data=df_pa,
    x='MEOW_Code',
    y='Survival_Rate',
    hue='Strategy',
    hue_order=['Baseline', 'BA', 'BA+MR1'],
    dodge=True,          
    jitter=True,         
    alpha=0.6,           
    size=3.5,
    palette={'Baseline': '#ffffff', 'BA': '#ffffff', 'BA+MR1': '#ffffff'}, 
    linewidth=0.5,
    edgecolor='gray',    
    ax=ax
)

# =====================================================================
# 4. Chart Decoration, Legend, and Text Axis
# =====================================================================
# Custom legend patches 
legend_patches = [
    mpatches.Patch(facecolor=COLOR_BASELINE, edgecolor='#333333', linewidth=1.2, label='Baseline'),
    mpatches.Patch(facecolor=COLOR_BA, edgecolor='#333333', linewidth=1.2, label='BA'),
    mpatches.Patch(facecolor=COLOR_BAMR1, edgecolor='#333333', linewidth=1.2, label='BA+MR')
]

ax.legend(handles=legend_patches, title='', loc='upper center', bbox_to_anchor=(0.35, 1.18), 
          ncol=3, frameon=False, fontsize=12)

ax.set_ylim(0, 105)
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.set_ylabel('Climate-resistant area (%)', fontweight='bold', fontsize=12, labelpad=2)
ax.set_xlabel('Ecoregions', fontweight='bold', fontsize=12, labelpad=6)

ax.set_xticklabels(ax.get_xticklabels(), rotation=0, horizontalalignment='center', 
                   fontweight='bold', fontsize=12)

sns.despine(ax=ax)

# =====================================================================
# 5. Invisible Axes for Region Legend Text
# =====================================================================
plt.subplots_adjust(left=0.08, right=0.85, top=0.88, bottom=0.15)

ax_text = fig.add_axes([0.88, 0.25, 0.25, 0.73])
ax_text.axis('off') 

region_legend_text = (
    "1: Arctic\n"
    "2: Temperate Northern Atlantic\n"
    "3: Temperate Northern Pacific\n"
    "4: Tropical Atlantic\n"
    "5: Western Indo-Pacific\n"
    "6: Central Indo-Pacific\n"
    "7: Eastern Indo-Pacific\n"
    "8: Tropical Eastern Pacific\n"
    "9: Temperate South America\n"
    "10: Temperate Southern Africa\n"
    "11: Temperate Australasia\n"
    "12: Southern Ocean"
)

ax_text.text(0, 1, region_legend_text, fontsize=12, 
             verticalalignment='top', horizontalalignment='left', linespacing=1.6,
             transform=ax_text.transAxes)

out_file = os.path.join(OUTPUT_DIR, "Figure4c_SSP245_Statistics.png")
plt.savefig(out_file, dpi=300, facecolor='white', bbox_inches='tight')

print(f"[SUCCESS] Panel c successfully generated: {out_file}")
