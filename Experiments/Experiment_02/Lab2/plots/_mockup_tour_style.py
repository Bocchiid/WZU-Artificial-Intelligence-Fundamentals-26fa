# -*- coding: utf-8 -*-
"""【风格预览 · 非实验结果】

只为让「m=4 多旅行商路径图」的画风先定下来，用贪心最近邻随手切了 4 条路径，
不是离散 GA 跑出来的结果。看图可以，别往报告里贴。

真正的结果图由离散 GA 跑完后用同一套样式出。
"""

import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import viz_style as vs

plt = vs.apply()

HERE = os.path.dirname(os.path.abspath(__file__))
LAB2 = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_mockup")
os.makedirs(OUT, exist_ok=True)

M = 4
DEPOT = 0


def greedy_routes(pts, m, depot):
    """贪心最近邻 + 均分上限，仅用于预览。"""
    n = len(pts)
    unvisited = set(range(n)) - {depot}
    cap = math.ceil((n - 1) / m)
    routes = []
    for _ in range(m):
        route = [depot]
        cur = depot
        while unvisited and len(route) - 1 < cap:
            nxt = min(unvisited, key=lambda c: (pts[c][0] - pts[cur][0]) ** 2
                      + (pts[c][1] - pts[cur][1]) ** 2)
            unvisited.discard(nxt)
            route.append(nxt)
            cur = nxt
        route.append(depot)
        if len(route) > 2:
            routes.append(route)
    return routes


def length(route, pts):
    return sum(math.dist(pts[route[i]], pts[route[i + 1]])
               for i in range(len(route) - 1))


def main():
    pts = []
    with open(os.path.join(LAB2, "tsp225.txt"), encoding="utf-8") as f:
        for line in f:
            a = line.split()
            if len(a) >= 2:
                pts.append((float(a[0]), float(a[1])))

    routes = greedy_routes(pts, M, DEPOT)
    total = sum(length(r, pts) for r in routes)

    fig, ax = plt.subplots(figsize=(9.2, 4.7))
    ax.scatter([p[0] for p in pts], [p[1] for p in pts],
               s=14, c=vs.MUTED, zorder=2, linewidths=0)

    for i, r in enumerate(routes):
        color = vs.TOUR4[i]
        xs = [pts[c][0] for c in r]
        ys = [pts[c][1] for c in r]
        ax.plot(xs, ys, color=color, linewidth=1.8, zorder=3,
                solid_capstyle="round", label="旅行商 %d（%.0f）" % (i + 1, length(r, pts)))
        # 低对比度色靠直接标注兜底：在路径末端标出编号
        mid = r[len(r) // 2]
        ax.annotate(str(i + 1), xy=pts[mid], xytext=(0, 7),
                    textcoords="offset points", ha="center",
                    color=vs.INK_2, fontsize=10, fontweight="bold")

    dx, dy = pts[DEPOT]
    ax.scatter([dx], [dy], s=180, marker="*", c=vs.INK, zorder=5,
               edgecolors=vs.SURFACE, linewidths=1.2, label="起点（城市 %d）" % DEPOT)

    ax.set_title("【风格预览·非结果】m=%d 多旅行商路径  总路程 ≈ %.0f" % (M, total),
                 pad=14, loc="left")
    ax.set_xlabel("x 坐标")
    ax.set_ylabel("y 坐标")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)
    vs.despine(ax, keep=())
    ax.legend(loc="upper right")

    out = os.path.join(OUT, "tour_style.png")
    fig.savefig(out)
    plt.close(fig)
    print("saved:", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
