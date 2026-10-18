# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import os
import warnings

warnings.filterwarnings("ignore")

# =====================================================================
# 1. 配置文件路径与基础参数
# =====================================================================
INPUT_EXCEL = r"G:\github\GIPA\Data\Master_Baseline_Combined_0923_1013_v2_linkinfo_fixed.xlsx" 
OUTPUT_DIR = r"G:\github\GIPA\Figure"  

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

COLOR_BASELINE = '#C58473'  
COLOR_BA       = '#E09F3E'   
COLOR_BAMR1    =  '#8CA693'

# 横坐标纯数字映射
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
# 2. 数据处理与抗性占比计算
# =====================================================================
print("🚀 开始读取并处理 Panel c 统计数据...")

try:
    df = pd.read_excel(INPUT_EXCEL, sheet_name="Sheet2_Summary")
except ValueError:
    df = pd.read_excel(INPUT_EXCEL)

# 🌟 修正后的容错过滤逻辑（已补上 Thresh 筛选）：
df_ssp245 = df[
    (df['Sce'] == 'ssp245') & 
    (np.isclose(df['Thresh'].astype(float), 0.20, atol=1e-3)) &  # 👈 核心新增：精准锁定 0.2 阈值，防浮点误差
    (df['实际潮滩_面积'] > -1e-4)  
].copy()

# 将这些微小负数或 0 安全截断为极小正数，防止后续求生存率时分母为 0 报错
df_ssp245['实际潮滩_面积'] = df_ssp245['实际潮滩_面积'].clip(lower=1e-6)

# 然后通过 map_strategy 函数提取需要的策略，并剔除不需要的
def map_strategy(mr_val):
    val = str(mr_val).strip().lower()
    if 'baseline' in val or 'noaction' in val: return 'Baseline'
    if 'mr0' in val: return 'BA'
    if 'mr1' in val: return 'BA+MR1'
    return None

df_ssp245['Strategy'] = df_ssp245['MR'].apply(map_strategy)
df_ssp245 = df_ssp245.dropna(subset=['Strategy'])
# 🌟 核心修正：Retained_Area 仅计算 原地面积_2100 + 廊道面积_2100
df_ssp245['Retained_Area'] = df_ssp245['原地面积_2100'].fillna(0) + \
                             df_ssp245['廊道面积_2100'].fillna(0)

df_ssp245['Survival_Rate'] = (df_ssp245['Retained_Area'] / df_ssp245['实际潮滩_面积']) * 100
df_ssp245['Survival_Rate'] = df_ssp245['Survival_Rate'].clip(0, 100) 

def map_strategy(mr_val):
    val = str(mr_val).strip().lower()
    if val == 'baseline': return 'Baseline'
    if val == 'mr0': return 'BA'
    if val == 'mr1': return 'BA+MR1'
    return None

df_ssp245['Strategy'] = df_ssp245['MR'].apply(map_strategy)
df_ssp245 = df_ssp245.dropna(subset=['Strategy']) 

df_pa = df_ssp245.groupby(['REALM', 'PA_Name', 'Strategy'])['Survival_Rate'].mean().reset_index()

# 映射横坐标纯数字编号
df_pa['MEOW_Code'] = df_pa['REALM'].map(MEOW_DICT)
df_pa = df_pa.dropna(subset=['MEOW_Code']) 
df_pa['MEOW_Code'] = df_pa['MEOW_Code'].astype(int)
df_pa = df_pa.sort_values(by=['MEOW_Code'])

# =====================================================================
# 3. 开始绘制顶级期刊级并排柱状图
# =====================================================================
print("🎨 正在生成高对比度可视化版面...")

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



# 🌟 核心修改：高度在原来 2.5 的基础上增加 15% (即 2.875 英寸)

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
# 4. 图表修饰、坐标轴锁定与右侧图例
# =====================================================================
import matplotlib.patches as mpatches

# 🌟 手动构建图例色块，确保和柱状图的颜色、边框完全一致
legend_patches = [
    mpatches.Patch(facecolor=COLOR_BASELINE, edgecolor='#333333', linewidth=1.2, label='Baseline'),
    mpatches.Patch(facecolor=COLOR_BA, edgecolor='#333333', linewidth=1.2, label='BA'),
    mpatches.Patch(facecolor=COLOR_BAMR1, edgecolor='#333333', linewidth=1.2, label='BA+MR')
]

# 🌟 核心修改：将 bbox_to_anchor 的 X 值从 0.5 改为 0.35，使图例整体左移
# 如果觉得还不够左，可以继续减小到 0.3 或 0.25
ax.legend(handles=legend_patches, title='', loc='upper center', bbox_to_anchor=(0.5, 1.18), 
          ncol=3, frameon=False, fontsize=12)

ax.set_ylim(0, 105)
ax.set_yticks([0, 20, 40, 60, 80, 100])

ax.set_ylabel('Climate-resistant area (%)', fontweight='bold', fontsize=12, labelpad=2)

ax.set_xlabel('Ecoregions', fontweight='bold', fontsize=12, labelpad=6)
# 横坐标现在全是单个数字，取消倾斜，居中显示
ax.set_xticklabels(ax.get_xticklabels(), rotation=0, horizontalalignment='center', 
                   fontweight='bold', fontsize=12)

sns.despine(ax=ax)

# =====================================================================
# 🌟 终极解决方案：创建隐形附轴专门挂载长文本
# =====================================================================
# 强制主图占据左侧 75% 的空间
plt.subplots_adjust(left=0.08, right=0.85, top=0.88, bottom=0.15)

# 在右侧单独开辟一个透明的坐标系 (左下角X, 左下角Y, 宽度, 高度)
ax_text = fig.add_axes([0.88, 0.25, 0.25, 0.73])
ax_text.axis('off') # 隐藏所有边框和刻度

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

# 现在文字是挂在这个附轴上的，原点 (0,1) 就是附轴的左上角
ax_text.text(0, 1, region_legend_text, fontsize=12, 
             verticalalignment='top', horizontalalignment='left', linespacing=1.6,
             transform=ax_text.transAxes)

out_file = os.path.join(OUTPUT_DIR, "Figure4c_SSP245_Statistics.png")

# 使用 bbox_inches='tight'，系统会自动包裹住所有 Axes (包括隐形的文字轴)
# 🌟 只保留了带白色背景的保存方式
plt.savefig(out_file, dpi=300, facecolor='white', bbox_inches='tight')

print(f"✅ Panel c 已成功生成: {out_file}")
