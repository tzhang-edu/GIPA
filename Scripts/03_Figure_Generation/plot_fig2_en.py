# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.legend_handler import HandlerBase
from matplotlib.text import Text
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import warnings

warnings.filterwarnings("ignore")

# Custom Composite Legend Renderer
class CustomCIHandler(HandlerBase):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        t1 = Text(x=0, y=height/2, text="66% CI  ", va='center', ha='left', 
                  fontsize=fontsize, color='#333333', transform=trans)
        box_x = fontsize * 4.0  
        box_w = fontsize * 1.8  
        box_h = fontsize * 1.0  
        rect = Rectangle((box_x, height/2 - box_h/2), box_w, box_h, 
                         facecolor='#696969', alpha=0.7, edgecolor='none', transform=trans)
        line = Line2D([box_x, box_x + box_w + fontsize*0.2], [height/2, height/2], 
                      color='#333333', linewidth=2.8, transform=trans)
        t2 = Text(x=box_x + box_w + fontsize*0.35, y=height/2, text="", 
                  va='center', ha='left', fontsize=fontsize, color='#333333', transform=trans)
        return [t1, rect, line, t2]

class DummyCIHandle:
    pass

# =====================================================================
# 1. Configuration Paths and Parameter Settings
# =====================================================================
COMBINED_EXCEL = r"G:\github\GIPA\Data\Overall_Summary_260923.xlsx"
OUTPUT_FIG = r"G:\github\GIPA\Figure\Figure2.png"

TARGET_THRESH = 0.20
TARGET_CONF = 'Mid_Prob'

SSP_COLORS = {
    'ssp126': '#8cb8d7',  
    'ssp245': '#8893a9',  
    'ssp370': '#ebb17d',  
    'ssp585': '#c16d6d'   
}
ssp_order = ['ssp126', 'ssp245', 'ssp370', 'ssp585']

# =====================================================================
# 2. Data Processing A: Temporal Dynamics (Panels a, b, c)
# =====================================================================
def load_temporal_data():
    try:
        df = pd.read_excel(COMBINED_EXCEL, sheet_name="Sheet1_Summary")
    except ValueError:
        df = pd.read_excel(COMBINED_EXCEL)
        
    df = df[np.isclose(df['Thresh'].astype(float), TARGET_THRESH, atol=1e-3)]
    
    def clean_mr_name(mr_str):
        mr_str_lower = str(mr_str).lower()
        if 'baseline' in mr_str_lower: return 'Baseline'
        if 'mr0' in mr_str_lower: return 'MR0'
        if 'mr1' in mr_str_lower: return 'MR1'
        return 'Drop' 
        
    df['MR_Clean'] = df['MR'].apply(clean_mr_name)
    df = df[df['MR_Clean'] != 'Drop']

    pa_mr_counts = df.groupby(['Sce', 'Conf', 'PA_Name'])['MR_Clean'].transform('nunique')
    REQUIRED_MR_COUNT = df['MR_Clean'].nunique() 
    df_aligned = df[pa_mr_counts == REQUIRED_MR_COUNT].copy()
    
    records = []
    years = [2040, 2060, 2080, 2100]
    
    df_agg = df_aligned.groupby(['Sce', 'MR_Clean', 'Conf']).sum(numeric_only=True).reset_index()
    
    for idx, row in df_agg.iterrows():
        sce = row['Sce']
        mr = row['MR_Clean']
        conf = row['Conf']
            
        actual_area = row.get('Actual_Tidal_Area', 0)
        records.append({'Sce': sce, 'Strategy': mr, 'Conf': conf, 'Year': 2020, 'Survival_Ratio': 100.0, 'Survived_Area': actual_area})
        
        for y in years:
            insitu_area = row.get(f'InSitu_Area_{y}', 0)
            corridor_area = row.get(f'Corridor_Area_{y}', 0)
            
            survived_area = insitu_area + corridor_area
            ratio = (survived_area / actual_area) * 100.0 if actual_area > 0 else 0
            records.append({'Sce': sce, 'Strategy': mr, 'Conf': conf, 'Year': y, 'Survival_Ratio': ratio, 'Survived_Area': survived_area})
            
    return pd.DataFrame(records)

# =====================================================================
# 3. Data Processing B: Total Area Post-Intervention (Panel d)
# =====================================================================
def load_net_benefits_data():
    try:
        df = pd.read_excel(COMBINED_EXCEL, sheet_name="Sheet1_Summary")
    except ValueError:
        df = pd.read_excel(COMBINED_EXCEL)
    
    df = df[np.isclose(df['Thresh'].astype(float), TARGET_THRESH, atol=1e-3)]
    
    def clean_mr_name(mr_str):
        mr_str_lower = str(mr_str).lower()
        if 'baseline' in mr_str_lower: return 'Baseline'
        if 'mr0' in mr_str_lower: return 'MR0'
        if 'mr1' in mr_str_lower: return 'MR1'
        return 'Drop' 
        
    df['MR_Clean'] = df['MR'].apply(clean_mr_name)
    df = df[df['MR_Clean'] != 'Drop']

    pa_mr_counts = df.groupby(['Sce', 'Conf', 'PA_Name'])['MR_Clean'].transform('nunique')
    REQUIRED_MR_COUNT = df['MR_Clean'].nunique() 
    df_aligned = df[pa_mr_counts == REQUIRED_MR_COUNT].copy()

    df_aligned['Survival_2100_Abs'] = df_aligned['InSitu_Area_2100'].fillna(0) + df_aligned['Corridor_Area_2100'].fillna(0)
    
    agg_df = df_aligned.groupby(['Sce', 'MR_Clean', 'Conf'])[['Survival_2100_Abs']].sum().reset_index()
    agg_df = agg_df.rename(columns={'MR_Clean': 'Strategy', 'Survival_2100_Abs': 'Final_Total_Area'})
    
    agg_df['Strategy'] = pd.Categorical(agg_df['Strategy'], categories=['Baseline', 'MR0', 'MR1'], ordered=True)
    agg_df = agg_df.sort_values(by=['Strategy', 'Sce', 'Conf'])
    
    return agg_df

# =====================================================================
# 4. Combined Plotting
# =====================================================================
def plot_combined_figure(long_df, net_df):
    
    sns.set_theme(style="ticks", context="paper", font_scale=1.7)
    
    fig = plt.figure(figsize=(13.5, 10)) 
    
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[1, 1.2], hspace=0.35, wspace=0.22)
    
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1], sharey=ax_a)
    ax_c = fig.add_subplot(gs[0, 2], sharey=ax_a)
    ax_d = fig.add_subplot(gs[1, :])
    
    axes_lines = [ax_a, ax_b, ax_c]
    plot_strategies = ['Baseline', 'MR0', 'MR1'] 
    panel_labels = ['a', 'b', 'c']
    
    abc_x_offset = -0.05 
    abc_y_offset = 0.90

    for i, strategy in enumerate(plot_strategies):
        ax = axes_lines[i]
        df_strat = long_df[long_df['Strategy'] == strategy]
        
        for sce in ssp_order:
            df_sce = df_strat[df_strat['Sce'] == sce]
            if df_sce.empty: continue
            
            years = sorted(df_sce['Year'].unique())
            y_mid, y_min, y_max = [], [], []
            
            for y in years:
                df_y = df_sce[df_sce['Year'] == y]
                mid_val = df_y[df_y['Conf'] == 'Mid_Prob']['Survival_Ratio'].values
                mid_val = mid_val[0] if len(mid_val) > 0 else np.nan
                min_val = df_y['Survival_Ratio'].min()
                max_val = df_y['Survival_Ratio'].max()
                
                y_mid.append(mid_val)
                y_min.append(min_val)
                y_max.append(max_val)
                
            color = SSP_COLORS.get(sce, 'black')
            sce_label_map = {'ssp126': 'SSP126', 'ssp245': 'SSP245', 'ssp370': 'SSP370', 'ssp585': 'SSP585'}
            ax.plot(years, y_mid, label=sce_label_map.get(sce, sce.upper()), color=color, linewidth=3.0, marker='o', markersize=8)
            ax.fill_between(years, y_min, y_max, color=color, alpha=0.15, edgecolor='none')
            
        current_x = -0.18 if i == 0 else -0.06
        ax.set_title(panel_labels[i], fontweight='bold', fontsize=25, x=current_x, y=abc_y_offset)
        
        ax.set_xticks([2020, 2040, 2060, 2080, 2100])
        ax.set_xlim(2018, 2102)
        ax.grid(True, linestyle='--', alpha=0.5)
        
        ax.set_xlabel('Year', fontweight='bold', fontsize=18, labelpad=8)
        ax.tick_params(axis='x', labelsize=18)
        
        if i == 0:  
            sns.despine(ax=ax)
            ax.set_ylabel('Resistant area proportion (%)', fontweight='bold', fontsize=18, labelpad=8)
            ax.tick_params(axis='y', labelsize=18)
        else:         
            sns.despine(ax=ax, left=True)
            ax.tick_params(left=False, labelleft=False)
            
    ax_a.set_ylim(-2, 105) 
    
    handles, labels = ax_a.get_legend_handles_labels()
    handles.append(DummyCIHandle())
    labels.append("            Median") 
    
    ax_a.legend(handles, labels, loc='upper right', frameon=True, 
                facecolor='white', edgecolor='none', framealpha=0.9, fontsize=16,
                handler_map={DummyCIHandle: CustomCIHandler()})
                
    df_mid = net_df[net_df['Conf'] == 'Mid_Prob']
    
    sns.barplot(
        data=df_mid, 
        x='Strategy', 
        y='Final_Total_Area',  
        hue='Sce', 
        hue_order=ssp_order,
        palette=SSP_COLORS,
        edgecolor='black',
        linewidth=1.2,
        alpha=0.9,
        width=0.4, 
        ax=ax_d
    )
    
    strategy_map = {'Baseline': 'Baseline', 'MR0': 'BA', 'MR1': 'BA + MR'}
    current_labels = [t.get_text() for t in ax_d.get_xticklabels()]
    new_labels = [strategy_map.get(label, label) for label in current_labels]
    
    ax_d.set_xticklabels(new_labels, fontweight='bold', fontsize=18)
    ax_d.set_title('d', fontweight='bold', fontsize=25, x=-0.05, y=1.02)
    
    ax_d.set_xlabel('Management strategy', fontweight='bold', fontsize=18, labelpad=10)
    ax_d.set_ylabel('Resistant area (km²)', fontweight='bold', fontsize=18, labelpad=10)
    ax_d.tick_params(axis='y', labelsize=18)
    ax_d.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    ax_d.axhline(0, color='black', linewidth=1.2, linestyle='-')
    ax_d.grid(axis='y', linestyle='--', alpha=0.6)
    sns.despine(ax=ax_d)
    
    if ax_d.get_legend() is not None:
        ax_d.get_legend().remove()
    
    bars = [p for p in ax_d.patches if isinstance(p, Rectangle)]
    p_idx = 0
    
    for sce in ssp_order:
        for strategy in ['Baseline', 'MR0', 'MR1']:
            if p_idx >= len(bars): break
            p = bars[p_idx]
            
            sub_df = net_df[(net_df['Sce'] == sce) & (net_df['Strategy'] == strategy)]
            if sub_df.empty:
                p_idx += 1; continue
                
            vals = sub_df['Final_Total_Area'].dropna().values
            if len(vals) == 0:
                p_idx += 1; continue
            
            mid_series = sub_df[sub_df['Conf'] == 'Mid_Prob']['Final_Total_Area']
            mid_val = mid_series.values[0] if not mid_series.empty else np.nan
            
            _max = np.max(vals)
            _min = np.min(vals)
            x_center = p.get_x() + p.get_width() / 2.
            
            if len(vals) > 1 and not np.isnan(_max) and not np.isnan(_min):
                ax_d.plot([x_center, x_center], [_min, _max], color='#333333', lw=1.5, zorder=3)
                cap_w = p.get_width() * 0.25
                ax_d.plot([x_center - cap_w, x_center + cap_w], [_max, _max], color='#333333', lw=1.5, zorder=3)
                ax_d.plot([x_center - cap_w, x_center + cap_w], [_min, _min], color='#333333', lw=1.5, zorder=3)
            
            if not np.isnan(mid_val) and mid_val != 0:
                label_y = _max if not np.isnan(_max) else mid_val 
                ax_d.annotate(f'{mid_val:,.0f}', 
                              (x_center, label_y), 
                              ha='center', va='bottom', 
                              xytext=(0, 4), textcoords='offset points', 
                              fontsize=15, fontweight='bold', color='#333333')
            
            p_idx += 1

    fig.align_ylabels([ax_a, ax_d])
    plt.subplots_adjust(top=0.96, bottom=0.08, left=0.07, right=0.97)
    
    plt.savefig(OUTPUT_FIG, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"[SUCCESS] Figure saved successfully to: {OUTPUT_FIG}")
    plt.close()

if __name__ == "__main__":
    print("[INFO] Initializing data loading and preparation workflow...")
    df_temporal = load_temporal_data()
    df_net = load_net_benefits_data()
    
    if not df_temporal.empty and not df_net.empty:
        print("[INFO] Rendering combined plots...")
        plot_combined_figure(df_temporal, df_net)
        
    if not df_temporal.empty:
        print("\n[INFO] Climate-resistant area and proportion across time points/scenarios:")
        df_print = df_temporal[df_temporal['Conf'] == 'Mid_Prob'].copy()
        
        df_print['Display_Value'] = df_print.apply(
            lambda row: f"{row['Survival_Ratio']:.2f}% ({row['Survived_Area']:,.0f})", 
            axis=1
        )
        
        pivot_df = df_print.pivot_table(
            index=['Strategy', 'Sce'], 
            columns='Year', 
            values='Display_Value',
            aggfunc='first' 
        )
        
        strategy_order = ['Baseline', 'MR0', 'MR1']
        pivot_df = pivot_df.reindex(strategy_order, level=0)
        
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        
        print(pivot_df)
        print("[INFO] End of summary.\n")
