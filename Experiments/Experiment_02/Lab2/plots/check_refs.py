# -*- coding: utf-8 -*-
"""检查 docx 里所有 REF 交叉引用域的缓存值。

Word 在不更新域的情况下，显示的就是域里 separate 与 end 之间的那段缓存文本。
这段文本正确，用户打开文档就能看到正确编号。
"""

import re
import sys
import zipfile

INSTR = re.compile(r"REF (_Ref\w+) \\h")
T = re.compile(r"<w:t[^>]*>([^<]*)</w:t>")


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def main(path):
    x = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")

    print("%-12s %-6s %s" % ("书签", "缓存值", "上下文"))
    print("-" * 74)
    n = 0
    bad = 0
    for m in INSTR.finditer(x):
        n += 1
        name = m.group(1)
        seg = x[m.end():m.end() + 800]
        parts = seg.split("separate", 1)
        got = "(无 separate)"
        if len(parts) > 1:
            t = T.search(parts[1])
            if t:
                got = t.group(1)
        if got in ("?", "(无 separate)") or not got.isdigit():
            bad += 1
            flag = "  <-- 有问题"
        else:
            flag = ""
        before = strip_tags(x[max(0, m.start() - 500):m.start()])[-12:]
        after = strip_tags(seg)[:14]
        print("%-12s %-6s ...%s【%s】%s...%s"
              % (name, got, before, got, after, flag))

    print()
    print("REF 域共 %d 处，异常 %d 处" % (n, bad))
    return bad


if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1]) else 0)
