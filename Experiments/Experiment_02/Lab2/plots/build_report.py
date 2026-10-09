# -*- coding: utf-8 -*-
"""把实验内容写入 24 报告模板的表格里。

要点：
  - 模板整体是一个带边框的大表格，内容按栏目填进各行的第 2 个格子
  - 正文沿用模板默认字体：中文宋体 / 西文 Times New Roman / 五号(10.5pt)
  - 图题在图下方、表题在表上方（学院报告规范）
  - 图题编号用 SEQ 域、正文引用用 REF 域（真·Word 交叉引用），
    并写入正确的缓存结果，这样不更新域也能正常显示
"""

import json
import os
import sys

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
LAB2 = os.path.dirname(HERE)
ROOT = os.path.dirname(LAB2)
PIC = os.path.join(ROOT, "Pictures")

CN = "宋体"
EN = "Times New Roman"
FS = "仿宋_GB2312"      # 模板里「报告名称 / 姓名 / 学号」这些格用的字体
BODY_PT = 10.5          # 五号
HEAD_PT = 12.0          # 报告名称、姓名、学号
CAP_PT = 9.0            # 小五

_bid = [1000]
_fig_no = [0]
_tbl_no = [0]
_bookmarks = {}          # 名字 -> 缓存的编号


# ---------------------------------------------------------------- 基础排版
def style_run(r, size=BODY_PT, bold=False, cn=CN, en=EN):
    r.font.name = en
    r.font.size = Pt(size)
    r.bold = bold
    rpr = r._element.get_or_add_rPr()
    rf = rpr.get_or_add_rFonts()
    rf.set(qn('w:ascii'), en)
    rf.set(qn('w:hAnsi'), en)
    rf.set(qn('w:eastAsia'), cn)
    return r


def clear_cell(cell):
    """清空单元格，只留下一个空段落，并把这个段落返回给调用方。

    注意：这里必须连表格一起删。旧版本往格子里插过表格，重建时只删段落的话，
    这些表格会原地留下——渲染出来就是一张没有题注、位置也不对的表。
    """
    tc = cell._tc
    for child in list(tc):
        if child.tag in (qn('w:p'), qn('w:tbl')):
            tc.remove(child)
    return cell.add_paragraph()


def para_into(p, text="", size=BODY_PT, bold=False, align=None,
              first_indent=True, space_after=4, cn=CN):
    """把一段文字写进一个已经存在的空段落（clear_cell 返回的那个）。"""
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.25
    if align is not None:
        p.alignment = align
    if text:
        r = p.add_run(text)
        style_run(r, size=size, bold=bold, cn=cn)
        if first_indent:
            # 中文正文首行缩进 2 字符
            pf.first_line_indent = Pt(size * 2)
    return p


def para(cell, text="", size=BODY_PT, bold=False, align=None,
         first_indent=True, space_after=4, cn=CN):
    return para_into(cell.add_paragraph(), text, size=size, bold=bold,
                     align=align, first_indent=first_indent,
                     space_after=space_after, cn=cn)


# ---------------------------------------------------------------- 域代码
def _field_run(instr, cached, size=CAP_PT):
    """返回构成一个域的 5 个 <w:r> 元素。"""
    rs = []
    for kind in ('begin', None, 'separate'):
        r = OxmlElement('w:r')
        if kind is None:
            it = OxmlElement('w:instrText')
            it.set(qn('xml:space'), 'preserve')
            it.text = instr
            r.append(it)
        else:
            fc = OxmlElement('w:fldChar')
            fc.set(qn('w:fldCharType'), kind)
            r.append(fc)
        rs.append(r)
    # 缓存结果
    r = OxmlElement('w:r')
    rpr = OxmlElement('w:rPr')
    rf = OxmlElement('w:rFonts')
    rf.set(qn('w:ascii'), EN)
    rf.set(qn('w:hAnsi'), EN)
    rf.set(qn('w:eastAsia'), CN)
    rpr.append(rf)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(int(size * 2)))
    rpr.append(sz)
    r.append(rpr)
    t = OxmlElement('w:t')
    t.text = cached
    r.append(t)
    rs.append(r)
    # end
    r = OxmlElement('w:r')
    fc = OxmlElement('w:fldChar')
    fc.set(qn('w:fldCharType'), 'end')
    r.append(fc)
    rs.append(r)
    return rs


def add_caption(p, prefix, bookmark, text, size=CAP_PT):
    """图题/表题：前缀 + SEQ 域（带书签）+ 名称。"""
    r = p.add_run(prefix)
    style_run(r, size=size)
    if bookmark in _bookmarks:          # 已由 precompute_numbers() 预排
        cached = _bookmarks[bookmark]
    else:
        cached = str(_fig_no[0] if prefix.startswith("图") else _tbl_no[0])
        _bookmarks[bookmark] = cached

    bid = str(_bid[0]); _bid[0] += 1
    bs = OxmlElement('w:bookmarkStart')
    bs.set(qn('w:id'), bid)
    bs.set(qn('w:name'), bookmark)
    p._p.append(bs)
    for el in _field_run(" SEQ %s \\* ARABIC " % prefix.strip(), cached, size):
        p._p.append(el)
    be = OxmlElement('w:bookmarkEnd')
    be.set(qn('w:id'), bid)
    p._p.append(be)

    if text:
        r = p.add_run(" " + text)
        style_run(r, size=size)
    return p


def xref(p, bookmark, size=BODY_PT):
    """正文里的交叉引用：REF 域，指向题注书签。"""
    cached = _bookmarks.get(bookmark, "?")
    for el in _field_run(" REF %s \\h " % bookmark, cached, size):
        # 正文里的域用正文字号
        p._p.append(el)
    return p


# ---------------------------------------------------------------- 插图
def add_figure(cell, img, caption, width_cm=12.0, bookmark=None):
    _fig_no[0] += 1
    p = cell.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(img, width=Cm(width_cm))

    cp = cell.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.space_after = Pt(10)
    cp.paragraph_format.line_spacing = 1.0
    add_caption(cp, "图", bookmark, caption)
    return cp


def add_table_caption(cell, caption, bookmark):
    _tbl_no[0] += 1
    cp = cell.add_paragraph()
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cp.paragraph_format.space_before = Pt(8)
    cp.paragraph_format.space_after = Pt(2)
    cp.paragraph_format.line_spacing = 1.0
    add_caption(cp, "表", bookmark, caption)
    return cp


def set_borders(t):
    """模板里没有 Table Grid 样式，直接写边框 XML。"""
    tblPr = t._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        el = OxmlElement('w:' + edge)
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), '4')
        el.set(qn('w:space'), '0')
        el.set(qn('w:color'), '000000')
        borders.append(el)
    tblPr.append(borders)


def add_data_table(cell, header, rows, widths_cm=None):
    t = cell.add_table(rows=len(rows) + 1, cols=len(header))
    set_borders(t)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for j, h in enumerate(header):
        c = t.cell(0, j)
        c.text = ""
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        style_run(p.add_run(h), size=CAP_PT, bold=True)
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            style_run(p.add_run(str(v)), size=CAP_PT)
    if widths_cm:
        for j, w in enumerate(widths_cm):
            for r_ in t.rows:
                r_.cells[j].width = Cm(w)
    cell.add_paragraph()
    return t


# ---------------------------------------------------------------- 读实验数据
def load_sweep(name):
    with open(os.path.join(LAB2, "sweep", name), "r", encoding="utf-8") as f:
        return json.load(f)


def conv_gen(curve, frac=1.02):
    """首次进入最终值 frac 倍以内的代数。"""
    fin = curve[-1]
    for i, v in enumerate(curve):
        if v <= fin * frac:
            return i + 1
    return len(curve)


def table_rows(d):
    rows = []
    for k in sorted(d["runs"].keys(), key=float):
        r = d["runs"][k]
        rows.append([k,
                     "%.0f" % r["final_mean"],
                     "%.0f" % r["final_min"],
                     "%.0f" % r["final_max"],
                     "%.0f" % (r["final_max"] - r["final_min"]),
                     str(conv_gen(r["avg_curve"]))])
    return rows


def rich_into(p, segments, size=BODY_PT, first_indent=True, space_after=4):
    """把一段混排内容写进已存在的空段落。segments 元素为 str 或 ('xref', 书签名)。"""
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(space_after)
    pf.line_spacing = 1.25
    if first_indent:
        pf.first_line_indent = Pt(size * 2)
    for seg in segments:
        if isinstance(seg, tuple) and seg[0] == "xref":
            xref(p, seg[1], size=size)
        else:
            style_run(p.add_run(seg), size=size)
    return p


def rich(cell, segments, size=BODY_PT, first_indent=True, space_after=4):
    return rich_into(cell.add_paragraph(), segments, size=size,
                     first_indent=first_indent, space_after=space_after)


# ================================================================ 正文
# 图表在文档中出现的先后顺序。必须在写正文之前就登记好编号：
# 正文里的 REF 域要写入「缓存结果」，而插入图片是后发生的，
# 如果边写正文边登记，引用处的缓存值只能填成问号。
FIG_ORDER = ["_Ref_city", "_Ref_ox", "_Ref_run", "_Ref_pc",
             "_Ref_pm", "_Ref_sum", "_Ref_conv1", "_Ref_tour1",
             "_Ref_conv4", "_Ref_tour4"]
TBL_ORDER = ["_Ref_tbpc", "_Ref_tbpm"]


def precompute_numbers():
    for i, name in enumerate(FIG_ORDER, start=1):
        _bookmarks[name] = str(i)
    for i, name in enumerate(TBL_ORDER, start=1):
        _bookmarks[name] = str(i)


def audit_refs(dst):
    """复核：每个 REF 域的缓存结果都必须等于目标书签的编号。"""
    import re as _re
    import zipfile
    z = zipfile.ZipFile(dst)
    xml = z.read("word/document.xml").decode("utf-8")
    bad = []
    for m in _re.finditer(r'REF (_Ref\w+) \\h', xml):
        name = m.group(1)
        tail = xml[m.end():m.end() + 400]
        cm = _re.search(r'<w:t[^>]*>([^<]*)</w:t>', tail)
        got = cm.group(1) if cm else "(无)"
        want = _bookmarks.get(name, "?")
        if got != want:
            bad.append((name, got, want))
    print("REF 域复核: %d 处，%s"
          % (len(_re.findall(r"REF _Ref\w+", xml)),
             "全部正确" if not bad else "有误 -> %s" % bad))
    return not bad


def build(src, dst):
    precompute_numbers()
    doc = Document(src)
    tb = doc.tables[0]

    def cell(r, c=1):
        return tb.cell(r, c)

    # ---- 报告名称 / 学生信息 ----
    # 这三格沿用模板自带标签的字体（仿宋_GB2312 12pt）并居中对齐，
    # 与实验一报告保持一致；用正文字体（宋体 10.5pt）会明显比标签小一号。
    def head_cell(cell, text, bold=False):
        p = clear_cell(cell)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_run(p.add_run(text), size=HEAD_PT, bold=bold, cn=FS, en=FS)
        return p

    head_cell(tb.cell(0, 1), "遗传算法求解多旅行商问题（MTSP）")

    # 「学生」行的网格是 9 列：0=学生(行标签) 1=姓名(列标签) 2~4=合并的姓名值格
    #                        5=学号(列标签) 6~8=合并的学号值格
    # 注意 2、3、4 是同一个合并单元格，写两次会互相覆盖
    head_cell(tb.cell(1, 2), "韩贤煜", bold=True)
    head_cell(tb.cell(1, 6), "24211835201")

    # ================= 问题介绍 =================
    c = cell(2)
    para_into(clear_cell(c),
              "遗传算法是一类模拟自然选择和遗传机制的随机搜索算法。本实验原有的遗传算法代码求解的是连续"
            "变量的函数优化问题，个体用实数向量表示。但现实中很多问题是组合优化问题，解无法表示成一组连续实数，"
            "例如经典的旅行商问题（TSP）：要求确定一条访问所有城市、每个城市只访问一次、最后回到起点的"
            "最短回路。")
    para(c, "本实验处理的是旅行商问题的推广形式——多旅行商问题（MTSP）。给定 n 个城市和 m 个旅行商，"
            "要求每个城市恰好由一个旅行商访问一次，全部旅行商从同一座仓库城市出发、访问完各自负责的城市"
            "后返回仓库，并使总路程尽量短。本实验取 m=4。")
    para(c, "与经典 TSP 相比，MTSP 多了一层“任务划分”的含义：不仅要决定访问顺序，还要决定哪些城市归"
            "哪个旅行商。因此评价一个解不能只看总路程——如果四个旅行商中一个跑了两百个城市、另外三个几乎"
            "空跑，总路程可能很短但并不合理。所以本实验同时记录三个指标：总路程、最长单条路线，以及最长"
            "与最短之差（下称极差），并要求极差尽量小，即各旅行商的工作量尽量均衡。")
    rich(c, ["实验数据采用 TSPLIB 标准算例 tsp225，共 225 个城市，其分布如",
             "图", ("xref", "_Ref_city"), "所示。当 m=1 时该问题退化为经典 TSP，其已知最优解为 3916，"
             "可以作为检验算法改造是否正确的参照。"])
    add_figure(c, os.path.join(PIC, "discrete", "01_cities.png"),
               "TSP225 城市分布", width_cm=11.5, bookmark="_Ref_city")

    # ================= 算法实现 =================
    c = cell(3)
    para_into(clear_cell(c),
              "要在遗传算法里表示一条访问顺序，不能用实数编码，本实验采用排列编码。染色体是一个长度为 225 "
            "的整数数组 perm，其中 perm[0] 固定存放仓库城市，perm[1] 至 perm[224] 是其余 224 个城市的一个"
            "排列，表示访问的先后次序。当 m>1 时，另外用 m−1 个递增的切点把这 224 个城市切成 m 段，第 k 段"
            "交给第 k 个旅行商，其路线为“仓库 → 该段城市依次访问 → 仓库”。这样当 m=1 时没有切点，整条排列"
            "就是一条完整回路，两种情形共用同一套代码。")
    para(c, "适应度采用线性标定：以当前种群的最大代价 cmax 和代价极差 range 为基准，取 "
            "fitness = (cmax − cost) + range / (POPSIZE − 1)，使最好个体与最差个体的适应度之比拉开到 "
            "POPSIZE 附近，最差个体也保留一点非零概率，不至于被彻底饿死。代价按下式计算："
            "cost = 总路程 + 0.3 × 极差。当 m=1 时只有一条路线，极差恒为 0，代价就退化为总路程。")
    para(c, "遗传操作方面：选择采用锦标赛方式，每次随机抽取 8 个个体，留下其中代价最小者复制进入下一代；"
            "交叉采用 OX 顺序交叉，它在第一个父代中取一段连续区间原样保留给子代，其余位置按第二个父代的"
            "相对次序依次填充，能较好地保持城市之间的相邻关系；变异采用逆序变异，即随机选取一段城市序列"
            "整段反转；精英保留策略保证历代出现的最优个体不会丢失。")
    rich(c, ["程序运行参数为：种群规模 100，迭代 5000 代，交叉概率 0.7，变异概率 0.7。OX 顺序交叉的核心"
             "代码如", "图", ("xref", "_Ref_ox"), "所示，程序一次完整运行的输出如",
             "图", ("xref", "_Ref_run"), "所示。"])
    # 12.png 是手工裁过的截图（去掉了 VS Code 的标题栏、侧边栏和状态栏），
    # 比原来的整屏窗口截图 06_ox_crossover.png 干净，两者代码范围相同。
    add_figure(c, os.path.join(PIC, "discrete", "12.png"),
               "OX 顺序交叉的核心代码", width_cm=12.5, bookmark="_Ref_ox")
    add_figure(c, os.path.join(PIC, "discrete", "09_run_tsp_m1.png"),
               "离散遗传算法的运行输出", width_cm=11.0, bookmark="_Ref_run")
    rich(c, ["图", ("xref", "_Ref_run"), "是一次完整运行的结果：参数为 225 个城市、m=1、种群 100、"
             "迭代 5000 代、交叉与变异概率均为 0.7、随机种子 1001，最优回路总长 4156。m=1 时只有一条路线、"
             "极差恒为 0，所以代价与总路程相等，都是 4156，这与前面给出的代价公式一致。"])

    # ================= 实验对比 =================
    c = cell(4)
    para_into(clear_cell(c),
              "为考察交叉概率与变异概率的影响，设计了两组对照实验。每组固定其中一个概率、只改另一个，"
              "每个取值用 10 个不同的随机种子各跑一次，统计 10 次结果的平均值与波动范围。"
              "两组实验都在 m=1（经典 TSP）上做，因为此时评价指标只有总路程，收敛信号最干净。")

    # ---- 交叉概率组：固定变异概率，扫交叉概率 ----
    rich(c, ["交叉概率组：固定变异概率为 0.4，交叉概率分别取 0.1、0.3、0.5、0.7、0.9。五个取值的收敛曲线如",
             "图", ("xref", "_Ref_pc"), "所示，汇总数据见", "表", ("xref", "_Ref_tbpc"), "。"])
    add_figure(c, os.path.join(PIC, "param", "01_pcrossover.png"),
               "不同交叉概率下的收敛曲线（10 个种子平均）", width_cm=12.5, bookmark="_Ref_pc")
    add_table_caption(c, "不同交叉概率的实验结果（10 次运行）", "_Ref_tbpc")
    d1 = load_sweep("exp1_pcrossover.json")
    add_data_table(c, ["交叉概率", "平均最优", "最好", "最差", "极差", "接近最终值代数"],
                   table_rows(d1), widths_cm=[1.9, 1.9, 1.7, 1.7, 1.6, 2.8])
    rich(c, ["图", ("xref", "_Ref_pc"), "的五条曲线在 1000 代以前几乎重合，最后都收敛到 4400 附近；",
             "表", ("xref", "_Ref_tbpc"), "中交叉概率从 0.1 变到 "
             "0.9，10 次运行的平均最优路径长度只在 4344 到 4434 之间变动，相对波动约 2%，比同组内 10 个"
             "种子之间的极差（211 到 305）还小，说明交叉概率对最终解质量几乎没有影响。"
             "差别主要落在收敛速度上：交叉概率越大，第 200 代时的平均路径长度越低，从 17112 降到 15271，"
             "可见交叉的作用是尽快把优良片段拼到一起。另做一组完全不交叉的对照，最终平均最优路径长度为 "
             "4332，与有交叉时基本相当，说明最终解质量主要由变异和选择决定。"])

    # ---- 变异概率组：固定交叉概率，扫变异概率 ----
    rich(c, ["变异概率组：固定交叉概率为 0.7，变异概率分别取 0.05、0.1、0.2、0.4、0.7、1.0。六个取值的"
             "收敛曲线如", "图", ("xref", "_Ref_pm"), "所示，汇总数据见",
             "表", ("xref", "_Ref_tbpm"), "。"])
    add_figure(c, os.path.join(PIC, "param", "02_pmutation.png"),
               "不同变异概率下的收敛曲线（10 个种子平均）", width_cm=12.5, bookmark="_Ref_pm")
    add_table_caption(c, "不同变异概率的实验结果（10 次运行）", "_Ref_tbpm")
    d2 = load_sweep("exp2_pmutation.json")
    add_data_table(c, ["变异概率", "平均最优", "最好", "最差", "极差", "接近最终值代数"],
                   table_rows(d2), widths_cm=[1.9, 1.9, 1.7, 1.7, 1.6, 2.8])
    rich(c, ["图", ("xref", "_Ref_pm"), "的六条曲线明显分成三层：变异概率 0.05 和 1.0 两条到 5000 代仍"
             "停在 5500 以上且还在下降，0.1 居中，0.2、0.4、0.7 三条则迅速降到 4400 附近并稳定下来。",
             "表", ("xref", "_Ref_tbpm"), "中 0.05 时平均最优 5530、"
             "要到第 4721 代才接近最终值，变异太少使种群很快失去多样性，陷入局部最优出不来；升高到 0.7 时"
             "平均值最好（4338）且收敛最快（第 2412 代），但继续升到 1.0 又变差到 5603，因为每一代所有"
             "个体都被强制变异，好结构被反复破坏。另外 0.7 虽然平均值最好，10 次运行之间的极差却有 379，"
             "比 0.4 时的 305 更大，说明它上限更高、但也更看运气。"])

    # ---- 两组实验的对比 ----
    rich(c, ["把两组实验放在一起对比（", "图", ("xref", "_Ref_sum"), "）：左图是变异概率与最终解质量的"
             "关系，呈清晰的 U 形，两端相差超过 1200；右图把交叉概率与第 200 代进度、最终解质量画在一起，"
             "代表最终解的绿线几乎水平，代表早期进度的橙线则明显下降。据此可以把两个参数的作用概括为：",
             "交叉概率决定「多快找到好解」，变异概率决定「能不能找到好解」。"])
    add_figure(c, os.path.join(PIC, "param", "03_summary.png"),
               "参数敏感性总结", width_cm=13.5, bookmark="_Ref_sum")
    rich(c, ["两组在参数上还有一个交点：交叉概率组固定的是变异概率 0.4，变异概率组固定的是交叉概率 0.7，"
             "两者其实是同一组参数。对照表", ("xref", "_Ref_tbpc"), "第四行与表",
             ("xref", "_Ref_tbpm"), "第四行，六项数据完全相同（平均最优 4374、最好 4251、"
             "最差 4556、极差 305、接近最终值代数 2741），说明扫参数的程序没有把两个概率的作用搞混，"
             "数据本身也是可复现的。"])

    # ---- m=1 求解结果 ----
    rich(c, ["下面看最终求解出来的路线。", "图", ("xref", "_Ref_conv1"),
             "是 m=1（经典 TSP）的收敛曲线，", "图", ("xref", "_Ref_tour1"),
             "是对应的最优回路。"])
    add_figure(c, os.path.join(PIC, "discrete", "03_tsp_convergence.png"),
               "m=1 离散遗传算法的收敛曲线", width_cm=11.0, bookmark="_Ref_conv1")
    rich(c, ["图", ("xref", "_Ref_conv1"), "的曲线在最初 500 代从接近 40000 迅速降到 6000 以下，"
             "2000 代以后基本走平，末端最优"
             "路径长度为 4156；平均路径长度曲线始终紧贴最优曲线上方一点，说明种群整体收敛到了相近的水平。"
             "与 TSPLIB 公布的已知最优解 3916 相比，本次结果高 240，相对差距约 6.1%，说明从连续优化"
             "到离散（排列编码）的改造是正确的。"])
    add_figure(c, os.path.join(PIC, "discrete", "02_tsp_tour.png"),
               "m=1 经典 TSP 的最优路径", width_cm=11.5, bookmark="_Ref_tour1")
    rich(c, ["图", ("xref", "_Ref_tour1"), "中绝大多数相邻城市之间都是短连线，只有少数几段较长的"
             "对角线把左右两侧的城市簇"
             "串起来，没有大范围的交叉跨越——否则交换两条相交的边就能缩短总长，它也就不可能只比已知"
             "最优差 6% 了。"])

    # ---- m=4 求解结果 ----
    rich(c, ["把旅行商人数改成 m=4，其他参数保持不变，得到的收敛曲线如",
             "图", ("xref", "_Ref_conv4"), "所示。"])
    add_figure(c, os.path.join(PIC, "discrete", "05_mtsp_convergence.png"),
               "m=4 多旅行商的收敛曲线", width_cm=11.0, bookmark="_Ref_conv4")
    rich(c, ["与图", ("xref", "_Ref_conv1"), "相比，图", ("xref", "_Ref_conv4"),
             "的曲线下降更不平滑，到 5000 代时仍在缓慢改善（约 8090），没有像 m=1 那样"
             "在 2000 代前后走平。原因是 m=4 除了要决定 224 个城市的访问次序，还要额外决定 3 个切点把"
             "序列切成四段，搜索空间大得多；同时代价里多了一项均衡惩罚 0.3×极差，两个目标一起优化本身"
             "就更难。"])
    add_figure(c, os.path.join(PIC, "discrete", "04_mtsp_tour_m4.png"),
               "m=4 多旅行商的最优路径", width_cm=11.5, bookmark="_Ref_tour4")
    rich(c, ["这次求解的总路程为 8091，四条路线分别访问 59、58、58、49 个城市，长度依次为 2016、2065、"
             "2046、1964，长度合计正好 8091，城市数合计 224（加上作为起点的仓库城市共 225 个），"
             "没有重复访问也没有遗漏。最长与最短只差 101，相对于平均单条路线长度约 2023 只有 5%，"
             "图", ("xref", "_Ref_tour4"), "中四条路线各自覆盖的区块大小也大致相当，"
             "没有出现某一条把整个城市群包下来、其余几条"
             "空跑的情况，代价函数里的均衡惩罚项确实起了作用。另外按公式验算，总路程 8091 与极差 101 "
             "对应的代价为 8091 + 0.3 × 101 = 8121.3，与程序输出一致，说明惩罚项的实现没有问题。"])

    # ---- m=1 与 m=4 的整体对比 ----
    rich(c, ["m=1 与 m=4 的总路程不能直接相比：m=4 的四条路线都要往返仓库，比单条回路多出 8 段往返"
             "路程，总路程必然随旅行商人数增加而增大。衡量 m=4 应看单条路线——平均 8091 / 4 ≈ 2023，"
             "不到 m=1 时 4156 的一半，最长的一条也只有 2065。总路程增加近一倍，但每个旅行商的负担"
             "减少了一半以上，这才是引入多个旅行商的意义。"])

    # ================= 所遇到的问题总结 =================
    c = cell(5)
    para_into(clear_cell(c),
              "（1）程序第一次跑出来的结果基本等于随机回路，5000 代之后平均路径长度仍停在 40000 左右。"
            "检查后发现是适应度函数写成了代价的倒数，而种群中各个体的代价相差不大，取倒数"
            "以后适应度几乎相等，轮盘赌选择退化成了均匀随机抽样，好个体得不到复制。改成线性标定、"
            "并把选择算子换成锦标赛以后才正常收敛——锦标赛只看代价的相对大小，压力由参赛规模决定，"
            "与代价的绝对尺度无关。")
    para(c, "（2）适应度改好以后，发现交叉概率越大结果反而越差，这与课本上“交叉概率高一些更好”的说法相反。"
            "后来才明白：选择压力变大以后，种群很快就充满了最优个体的副本，两个几乎一样的父代做交叉不会产生"
            "新个体，反而不如让变异慢慢搜索。")
    para(c, "（3）变异概率一开始是按“每一位以多大比例变异”来理解的，取 0.005 看起来很小，但乘以 224 个"
            "城市之后，每个个体每一代平均要挨一次以上的逆序操作，等于每一代都把个体打散重来。改成“每个个体"
            "以多大比例被变异”之后，这个参数才有了正常的含义。")
    para(c, "心得体会：这次实验让我体会到，遗传算法的效果很大程度上取决于参数和算子的细节，并不是把模板"
            "代码抄下来就能跑好。同一个算法框架，仅仅因为适应度函数换了一种写法，结果就能差好几倍。很多时候"
            "程序能跑出结果，但结果并不对，需要自己找一个能判断对错的参照——这次是靠 TSPLIB 公布的已知最优解，"
            "才确认了离散化改造是否成功。另外也体会到记录的重要性：把每次运行的参数、随机"
            "种子和结果都存成日志以后，回头做对比分析才做得起来。")

    doc.save(dst)
    print("saved:", dst)
    print("图 %d 张，表 %d 个" % (_fig_no[0], _tbl_no[0]))
    audit_refs(dst)


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
