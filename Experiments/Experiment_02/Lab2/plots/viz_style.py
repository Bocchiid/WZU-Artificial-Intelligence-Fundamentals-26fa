# -*- coding: utf-8 -*-
"""实验二插图统一样式：调色板 + 绘图约定。

配色取自 dataviz 参考调色板，已用校验器实测通过，不要凭感觉改：

  4 色组 TOUR4（MTSP 路径图，4 条路径同屏 -> all-pairs 校验）
      #2a78d6, #eb6834, #1baf7a, #4a3aa7   全部 PASS
      备选方案实测失败，勿用：加入黄色(#eda100) 与橙色 ΔE 13.7 < 15；
      加入红色(#e34948) ΔE 7.1；加入品红(#e87ba4) ΔE 12.9。

  5 色组 SERIES[:5]（参数对比曲线，5 条线相邻对校验）全部 PASS。

对比度告警：青(#1baf7a)、黄(#eda100)、品红(#e87ba4) 在浅色底上低于 3:1，
按规则必须配「可见直接标注」（曲线末端直接写字），不能只靠图例。
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

# ---- 图面与墨色 ----
SURFACE = "#fcfcfb"   # 图表底色
INK = "#0b0b0b"       # 主文字
INK_2 = "#52514e"     # 次级文字（直接标注用这个，不用系列色）
MUTED = "#898781"     # 坐标轴刻度标签
GRID = "#e1e0d9"      # 网格线（细）
AXIS = "#c3c2b7"      # 轴线

# ---- 分类色 ----
SERIES = [
    "#2a78d6",  # 1 蓝
    "#eb6834",  # 2 橙
    "#1baf7a",  # 3 青
    "#eda100",  # 4 黄
    "#e87ba4",  # 5 品红
    "#008300",  # 6 绿
    "#4a3aa7",  # 7 紫
    "#e34948",  # 8 红
]
TOUR4 = [SERIES[0], SERIES[1], SERIES[2], SERIES[6]]  # 蓝 橙 青 紫

FONT = "Microsoft YaHei"

DPI = 200


def apply():
    """套用全局 rcParams。每个绘图脚本开头调用一次。"""
    plt.rcParams.update({
        "font.sans-serif": [FONT, "SimHei", "Noto Sans SC", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": MUTED,
        "ytick.labelcolor": MUTED,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 13,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
        "legend.labelcolor": INK_2,
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.18,
    })
    return plt


def despine(ax, keep=("left", "bottom")):
    """去掉多余边框，只留需要的两条轴。"""
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)
