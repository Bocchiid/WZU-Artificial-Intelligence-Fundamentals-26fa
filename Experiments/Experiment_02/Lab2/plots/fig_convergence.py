# -*- coding: utf-8 -*-
"""收敛曲线绘图。

支持两种日志格式：
  连续 GA (galog.txt)：     代数, | 最优值 | 平均值 | 标准差
  离散 GA (GA_TSP 输出)：   代数, | 最优代价 | 平均代价 | 标准差 | 总路程 | 最长路径 | 极差
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import viz_style as vs

plt = vs.apply()

HERE = os.path.dirname(os.path.abspath(__file__))
LAB2 = os.path.dirname(HERE)
ROOT = os.path.dirname(LAB2)

RE_CONT = re.compile(r"^\s*(\d+),\s*\|\s*(-?[\d.]+)\s*\|\s*(-?[\d.]+)\s*\|\s*(-?[\d.]+)")
RE_DISC = re.compile(
    r"^\s*(\d+),\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(-?[\d.]+)"
    r"\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)")


def parse_continuous(path):
    """-> [(gen, best, avg, std)]"""
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = RE_CONT.match(line)
            if m:
                rows.append((int(m.group(1)), float(m.group(2)),
                             float(m.group(3)), float(m.group(4))))
    return rows


def parse_discrete(path):
    """-> [(gen, best_cost, avg_cost, std, total, maxroute, spread)]"""
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = RE_DISC.match(line)
            if m:
                rows.append(tuple(float(m.group(i)) for i in range(1, 8)))
    return [(int(r[0]),) + r[1:] for r in rows]


def plot_series(gens, series, out, title, ylabel, xlabel="迭代代数"):
    """series: [(值列表, 名称), ...]；末位直接标注。

    收敛曲线在末端往往彼此靠拢，直接标注会互相压叠成乱码。这里先算出各系列
    的末端值，按 y 轴高度强制拉开最小间距，再画一段短竖线把标签牵回真实端点。
    """
    fig, ax = plt.subplots(figsize=(9, 5.0))
    last_x = gens[-1]

    for i, (vals, name) in enumerate(series):
        ax.plot(gens, vals, linewidth=2, color=vs.SERIES[i], label=name,
                solid_capstyle="round", zorder=3)

    # 先定 y 轴范围，才知道"最小间距"折合多少数据单位
    lo = min(min(v) for v, _ in series)
    hi = max(max(v) for v, _ in series)
    pad = (hi - lo) * 0.06
    ax.set_ylim(lo - pad, hi + pad)
    ymin, ymax = ax.get_ylim()
    min_gap = (ymax - ymin) * 0.055

    ends = sorted(((vals[-1], i) for i, (vals, _) in enumerate(series)),
                  key=lambda t: t[0])
    placed = []
    for y_true, i in ends:
        y_lab = y_true if not placed else max(y_true, placed[-1] + min_gap)
        placed.append(y_lab)
        ax.annotate(series[i][1], xy=(last_x, y_lab), xytext=(7, 0),
                    textcoords="offset points", color=vs.INK_2,
                    fontsize=9.5, va="center", ha="left", zorder=4)
        if abs(y_lab - y_true) > min_gap * 0.25:      # 被推开了就牵线指回
            ax.plot([last_x, last_x], [y_true, y_lab], color=vs.SERIES[i],
                    linewidth=0.9, zorder=2)

    ax.set_title(title, pad=12, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(gens[0], last_x * 1.16)      # 给右侧直接标注让位
    ax.legend(loc="center right")
    vs.despine(ax)

    fig.savefig(out)
    plt.close(fig)
    print("saved:", out, os.path.getsize(out), "bytes")


def fig_continuous():
    out = os.path.join(ROOT, "Pictures", "continuous")
    os.makedirs(out, exist_ok=True)
    rows = parse_continuous(os.path.join(LAB2, "galog.txt"))
    gens = [r[0] for r in rows]
    plot_series(gens,
                [([r[1] for r in rows], "最优适应度"),
                 ([r[2] for r in rows], "平均适应度")],
                os.path.join(out, "01_convergence.png"),
                "任务 1：连续 GA 收敛曲线  f = x1² + x2²", "适应度")


def fig_discrete():
    out = os.path.join(ROOT, "Pictures", "discrete")
    os.makedirs(out, exist_ok=True)

    rows = parse_discrete(os.path.join(LAB2, "results", "tsp_m1_log.txt"))
    gens = [r[0] for r in rows]
    plot_series(gens,
                [([r[1] for r in rows], "最优路径长度"),
                 ([r[2] for r in rows], "平均路径长度")],
                os.path.join(out, "03_tsp_convergence.png"),
                "任务 2：m=1 离散 GA 收敛曲线（225 城市）", "路径长度")

    rows = parse_discrete(os.path.join(LAB2, "results", "mtsp_m4_log.txt"))
    gens = [r[0] for r in rows]
    plot_series(gens,
                [([r[4] for r in rows], "最优总路程"),
                 ([r[5] for r in rows], "最长单条路线")],
                os.path.join(out, "05_mtsp_convergence.png"),
                "任务 2：m=4 多旅行商收敛曲线（均衡惩罚 0.3）", "路程")


if __name__ == "__main__":
    fig_continuous()
    fig_discrete()
