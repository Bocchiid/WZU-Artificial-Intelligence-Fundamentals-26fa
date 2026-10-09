# -*- coding: utf-8 -*-
"""225 城市散点分布图 -> Pictures/discrete/01_cities.png

单系列散点，按规则不配图例（标题即系列名）。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import viz_style as vs

plt = vs.apply()

HERE = os.path.dirname(os.path.abspath(__file__))
LAB2 = os.path.dirname(HERE)
OUT = os.path.join(os.path.dirname(LAB2), "Pictures", "discrete")
os.makedirs(OUT, exist_ok=True)


def load_cities(path):
    xs, ys = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                xs.append(float(parts[0]))
                ys.append(float(parts[1]))
    return xs, ys


def main():
    xs, ys = load_cities(os.path.join(LAB2, "tsp225.txt"))
    n = len(xs)

    # 数据宽高比实测 2.13:1（x 跨 469.5，y 跨 220.5），figsize 按此贴合，
    # 否则 equal aspect 会把坐标框压扁、四周留大块空白。
    fig, ax = plt.subplots(figsize=(9.2, 4.7))
    ax.scatter(xs, ys, s=26, c=vs.SERIES[0], edgecolors=vs.SURFACE,
               linewidths=0.9, zorder=3)

    ax.set_title("TSP225 城市分布（共 %d 个城市）" % n, pad=14)
    ax.set_xlabel("x 坐标")
    ax.set_ylabel("y 坐标")
    ax.set_aspect("equal", adjustable="box")
    # 地图形态：网格没有信息量，去掉
    ax.grid(False)
    vs.despine(ax, keep=())

    out = os.path.join(OUT, "01_cities.png")
    fig.savefig(out)
    plt.close(fig)
    print("saved:", out, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
