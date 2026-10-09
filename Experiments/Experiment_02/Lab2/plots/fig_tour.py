# -*- coding: utf-8 -*-
"""路径图绘制：把 GA 输出的最优路径画成 TSP / MTSP 路线图。

读取 GA_TSP.exe 产生的 <prefix>_best.txt，格式：
    # m=4 depot=0 total=... maxroute=... spread=...
    # route_id  n_cities  length  city_indices...
    0 59 1776.000 172 70 133 ...
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import viz_style as vs

plt = vs.apply()

import matplotlib.patheffects as pe

# 路径编号常常压在线上，加一圈底色描边保证可读
HALO = [pe.withStroke(linewidth=3.2, foreground=vs.SURFACE)]

HERE = os.path.dirname(os.path.abspath(__file__))
LAB2 = os.path.dirname(HERE)


def load_cities(path):
    pts = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            a = line.split()
            if len(a) >= 2:
                pts.append((float(a[0]), float(a[1])))
    return pts


def load_tour(path):
    """-> (header_dict, [(route_id, n, length, [cities])])"""
    head, routes = {}, []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                for tok in line[1:].split():
                    if "=" in tok:
                        k, v = tok.split("=", 1)
                        head[k] = v
                continue
            a = line.split()
            if len(a) >= 3:
                routes.append((int(a[0]), int(a[1]), float(a[2]),
                               [int(x) for x in a[3:]]))
    return head, routes


def plot(prefix, out_png, title, depot=0):
    pts = load_cities(os.path.join(LAB2, "tsp225.txt"))
    head, routes = load_tour(prefix + "_best.txt")
    m = int(head.get("m", "1"))

    # 单条路线时按顺序取色；m>1 用通过 all-pairs 校验的蓝橙青紫四色组
    colors = vs.TOUR4 if m > 1 else [vs.SERIES[0]]

    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    ax.scatter([p[0] for p in pts], [p[1] for p in pts],
               s=13, c=vs.MUTED, zorder=2, linewidths=0, label="城市")

    for i, (rid, n, L, cities) in enumerate(routes):
        c = colors[i % len(colors)]
        seq = [depot] + cities + [depot]
        # m=1 时只有一条回路，叫"旅行商 1"没有意义
        label = ("最优路径（%d 城，%.0f）" % (n, L)) if m == 1 \
            else ("旅行商 %d（%d 城，%.0f）" % (rid + 1, n, L))
        ax.plot([pts[x][0] for x in seq], [pts[x][1] for x in seq],
                color=c, linewidth=1.8, zorder=3, solid_capstyle="round",
                label=label)
        # 路线编号：多旅行商时用来把颜色对回编号；单条路径不需要
        if m > 1:
            mid = cities[len(cities) // 2]
            ax.annotate(str(rid + 1), xy=pts[mid], xytext=(0, 9),
                        textcoords="offset points", ha="center",
                        color=vs.INK_2, fontsize=10, fontweight="bold",
                        zorder=6, path_effects=HALO)

    dx, dy = pts[depot]
    ax.scatter([dx], [dy], s=190, marker="*", c=vs.INK, zorder=7,
               edgecolors=vs.SURFACE, linewidths=1.2, label="起点（城市 %d）" % depot)

    ax.set_title(title, pad=12, loc="left")
    ax.set_xlabel("x 坐标")
    ax.set_ylabel("y 坐标")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)
    vs.despine(ax, keep=())

    # 图例放到画布下方、坐标轴之外，避免压在线条和 x 轴标签上。
    # 不要用 mode="expand"：条目宽度不一时会被拉伸导致文字互相重叠。
    ncol = 3 if m > 1 else 3
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13),
              ncol=ncol, borderaxespad=0, columnspacing=1.6, handlelength=1.8)

    fig.savefig(out_png)
    plt.close(fig)
    print("saved:", out_png, os.path.getsize(out_png), "bytes")


def main():
    root = os.path.dirname(LAB2)
    fig_root = os.path.join(root, "Pictures")

    plot(os.path.join(LAB2, "results", "tsp_m1"),
         os.path.join(fig_root, "discrete", "02_tsp_tour.png"),
         "任务 2 & 4：m=1 经典 TSP 最优路径（总长 4156，TSPLIB 最优 3916）")

    plot(os.path.join(LAB2, "results", "mtsp_m4"),
         os.path.join(fig_root, "discrete", "04_mtsp_tour_m4.png"),
         "任务 2：m=4 多旅行商最优路径（总路程 8091，最长路径 2065，极差 101）")


if __name__ == "__main__":
    main()
