# -*- coding: utf-8 -*-
"""参数实验批量运行器（对应实验要求第 3 条）。

实验 1：固定 PMUT，扫 PCROSS
实验 2：固定 PCROSS，扫 PMUT
每个配置跑 NSEED 次（不同随机种子），记录每条收敛曲线与最终结果。

输出 JSON 到 Lab2/sweep/ 供绘图脚本读取。
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAB2 = os.path.dirname(HERE)
SWEEP = os.path.join(LAB2, "sweep")
EXE = os.path.join(LAB2, "GA_TSP.exe")

# 每条日志行：代数 | 最优代价 | 平均代价 | 标准差 | 总路程 | 最长路径 | 极差
ROW = re.compile(
    r"^\s*(\d+),\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*(-?[\d.]+)"
    r"\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)")

NSEED = 10
GENS = 5000
POP = 100

PC_VALUES = [0.1, 0.3, 0.5, 0.7, 0.9]        # 实验 1：扫交叉概率
PM_VALUES = [0.05, 0.1, 0.2, 0.4, 0.7, 1.0]  # 实验 2：扫变异概率
FIX_PM = 0.4                                  # 实验 1 固定的变异概率
FIX_PC = 0.7                                  # 实验 2 固定的交叉概率


def run_one(m, pc, pm, seed, tag):
    """跑一次，返回逐代的 (gen, best_total, best_cost) 列表。"""
    out = os.path.join(SWEEP, "_tmp_" + tag)
    cmd = [EXE, "-m", str(m), "-pc", str(pc), "-pm", str(pm),
           "-seed", str(seed), "-gens", str(GENS), "-pop", str(POP),
           "-out", out]
    r = subprocess.run(cmd, cwd=LAB2, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("run failed: %s\n%s" % (cmd, r.stderr.decode()))

    curve = []
    with open(out + "_log.txt", "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            mm = ROW.match(line)
            if mm:
                curve.append((int(mm.group(1)), float(mm.group(5))))
    os.remove(out + "_log.txt")
    if os.path.exists(out + "_best.txt"):
        os.remove(out + "_best.txt")
    return curve


def sweep(name, m, values, fixed_pc, fixed_pm, is_pc_sweep):
    result = {"m": m, "gens": GENS, "pop": POP, "nseed": NSEED,
              "fixed_pc": fixed_pc, "fixed_pm": fixed_pm, "runs": {}}

    for v in values:
        pc = v if is_pc_sweep else fixed_pc
        pm = fixed_pm if is_pc_sweep else v
        curves, finals = [], []
        for s in range(1, NSEED + 1):
            tag = "%s_%s_s%d" % (name, v, s)
            curve = run_one(m, pc, pm, 1000 + s, tag)
            final = curve[-1][1]
            # 统一成「截至第 g 代的历史最优」，不同种子的曲线才能平均
            best_so_far, norm = 1e18, []
            for g, bt in curve:
                if bt < best_so_far:
                    best_so_far = bt
                norm.append(best_so_far)
            curves.append(norm)
            finals.append(final)
            print("  %s=%s seed=%d  最终最优=%.0f" % (name, v, s, final))

        L = min(len(c) for c in curves)
        avg_curve = [sum(c[i] for c in curves) / len(curves) for i in range(L)]
        result["runs"][str(v)] = {
            "final_best": finals,
            "final_mean": sum(finals) / len(finals),
            "final_min": min(finals),
            "final_max": max(finals),
            "avg_curve": avg_curve,
        }
    return result


def main():
    os.makedirs(SWEEP, exist_ok=True)
    m = 1   # 参数实验在经典 TSP（m=1）上做，收敛信号最干净

    print("=== 实验 1：固定 pm=%.2f，扫交叉概率 ===" % FIX_PM)
    r1 = sweep("pc", m, PC_VALUES, None, FIX_PM, True)
    with open(os.path.join(SWEEP, "exp1_pcrossover.json"), "w",
              encoding="utf-8") as f:
        json.dump(r1, f)

    print("=== 实验 2：固定 pc=%.2f，扫变异概率 ===" % FIX_PC)
    r2 = sweep("pm", m, PM_VALUES, FIX_PC, None, False)
    with open(os.path.join(SWEEP, "exp2_pmutation.json"), "w",
              encoding="utf-8") as f:
        json.dump(r2, f)

    print("\n汇总（10 次种子平均）")
    for label, r in (("交叉概率", r1), ("变异概率", r2)):
        print("\n%s：" % label)
        for k in r["runs"]:
            d = r["runs"][k]
            print("  %-5s  平均最优 %8.1f   最好 %7.0f   最差 %7.0f"
                  % (k, d["final_mean"], d["final_min"], d["final_max"]))


if __name__ == "__main__":
    sys.exit(main())
