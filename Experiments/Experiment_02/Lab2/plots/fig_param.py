# -*- coding: utf-8 -*-
"""任务 3 参数实验插图。

01_pcrossover.png  不同交叉概率下的收敛曲线（10 个种子平均）
02_pmutation.png   不同变异概率下的收敛曲线（10 个种子平均）
03_summary.png     敏感性总结：变异概率的 U 型 + 交叉概率的加速效应
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import viz_style as vs

plt = vs.apply()

HERE = os.path.dirname(os.path.abspath(__file__))
LAB2 = os.path.dirname(HERE)
ROOT = os.path.dirname(LAB2)
SWEEP = os.path.join(LAB2, "sweep")
OUT = os.path.join(ROOT, "Pictures", "param")


def load(name):
    with open(os.path.join(SWEEP, name), "r", encoding="utf-8") as f:
        return json.load(f)


def curves_fig(d, out_png, title, sweep_label):
    runs = d["runs"]
    keys = sorted(runs.keys(), key=float)
    n = len(keys)

    fig, ax = plt.subplots(figsize=(9, 5.0))
    for i, k in enumerate(keys):
        c = runs[k]["avg_curve"]
        ax.plot(range(1, len(c) + 1), c, linewidth=2, color=vs.SERIES[i],
                label="%s = %s" % (sweep_label, k),
                solid_capstyle="round", zorder=3)

    # 收敛曲线在末端彼此靠拢，直接标注会互相压叠，这里用图例承载身份；
    # 低对比度色所需的「可见数值」由 03_summary.png 的表格视图补齐。
    ax.set_yscale("log")
    ax.set_yticks([4000, 5000, 6000, 8000, 10000, 15000, 20000, 30000, 40000])
    ax.set_yticklabels(["4k", "5k", "6k", "8k", "10k", "15k", "20k", "30k", "40k"])
    ax.minorticks_off()

    ax.set_title(title, pad=12, loc="left")
    ax.set_xlabel("迭代代数")
    ax.set_ylabel("平均最优路径长度（对数刻度）")
    ax.margins(x=0.02)
    ax.legend(loc="upper right", ncol=2)
    vs.despine(ax)

    fig.savefig(out_png)
    plt.close(fig)
    print("saved:", out_png, os.path.getsize(out_png), "bytes")


def summary_fig(pc_d, pm_d, out_png):
    """两个面板：左=变异概率的 U 型；右=交叉概率的加速效应。"""
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6))

    # ---- 左：变异概率 vs 最终平均最优 ----
    ax = axes[0]
    keys = sorted(pm_d["runs"].keys(), key=float)
    xs = [float(k) for k in keys]
    ys = [pm_d["runs"][k]["final_mean"] for k in keys]
    err = [[pm_d["runs"][k]["final_mean"] - pm_d["runs"][k]["final_min"] for k in keys],
           [pm_d["runs"][k]["final_max"] - pm_d["runs"][k]["final_mean"] for k in keys]]
    ax.errorbar(xs, ys, yerr=err, color=vs.SERIES[0], linewidth=2,
                marker="o", markersize=8, capsize=4, zorder=3,
                markerfacecolor=vs.SERIES[0], markeredgecolor=vs.SURFACE,
                markeredgewidth=1.5)
    best = min(range(len(ys)), key=lambda i: ys[i])
    # 数值标在误差棒的**顶端之上**，否则会和误差棒竖线压在一起
    for i, (x, y) in enumerate(zip(xs, ys)):
        if i == best:
            anchor, dy = y - err[0][i], -7
        else:
            anchor, dy = y + err[1][i], 7
        ax.annotate("%.0f" % y, xy=(x, anchor), xytext=(0, dy),
                    textcoords="offset points", ha="center",
                    color=vs.INK_2, fontsize=9)
    ax.annotate("最优", xy=(xs[best], ys[best]), xytext=(0, -34),
                textcoords="offset points", ha="center",
                color=vs.INK, fontsize=9.5, fontweight="bold")
    ax.set_title("变异概率：明显的 U 型", pad=10, loc="left")
    ax.set_xlabel("变异概率 PMUT")
    ax.set_ylabel("最终最优路径长度（10 次均值±极差）")
    vs.despine(ax)

    # ---- 右：交叉概率 vs 早期进度 ----
    ax = axes[1]
    keys = sorted(pc_d["runs"].keys(), key=float)
    xs = [float(k) for k in keys]
    g200 = [pc_d["runs"][k]["avg_curve"][199] for k in keys]
    gfin = [pc_d["runs"][k]["final_mean"] for k in keys]
    ax.plot(xs, g200, color=vs.SERIES[1], linewidth=2, marker="s",
            markersize=8, markerfacecolor=vs.SERIES[1],
            markeredgecolor=vs.SURFACE, markeredgewidth=1.5,
            label="第 200 代时", zorder=3)
    ax.plot(xs, gfin, color=vs.SERIES[2], linewidth=2, marker="^",
            markersize=9, markerfacecolor=vs.SERIES[2],
            markeredgecolor=vs.SURFACE, markeredgewidth=1.5,
            label="最终（第 5000 代）", zorder=3)
    for x, y in zip(xs, g200):
        ax.annotate("%.0f" % y, xy=(x, y), xytext=(0, 11),
                    textcoords="offset points", ha="center",
                    color=vs.INK_2, fontsize=9)
    ax.annotate("最终解几乎不受交叉概率影响", xy=(xs[len(xs) // 2], gfin[len(xs) // 2]),
                xytext=(0, 26), textcoords="offset points", ha="center",
                color=vs.INK, fontsize=9.5)
    ax.set_ylim(3800, 19000)
    ax.set_title("交叉概率：只加快早期收敛", pad=10, loc="left")
    ax.set_xlabel("交叉概率 PCROSS")
    ax.set_ylabel("平均最优路径长度")
    ax.legend(loc="center right")
    vs.despine(ax)

    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    print("saved:", out_png, os.path.getsize(out_png), "bytes")


def main():
    os.makedirs(OUT, exist_ok=True)
    pc_d = load("exp1_pcrossover.json")
    pm_d = load("exp2_pmutation.json")

    curves_fig(pc_d, os.path.join(OUT, "01_pcrossover.png"),
               "任务 3：不同交叉概率的收敛曲线（固定 PMUT=0.4，10 种子平均）",
               "PCROSS")
    curves_fig(pm_d, os.path.join(OUT, "02_pmutation.png"),
               "任务 3：不同变异概率的收敛曲线（固定 PCROSS=0.7，10 种子平均）",
               "PMUT")
    summary_fig(pc_d, pm_d, os.path.join(OUT, "03_summary.png"))


if __name__ == "__main__":
    main()
