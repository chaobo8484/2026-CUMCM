# -*- coding: utf-8 -*-
"""把 03_预算_点击贡献匹配 与 04_预算Pareto累计占比 横向拼成一张合图。
不重采样、不放大，两图按公共高度居中贴到白底上，中间留白。"""
import os
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # E题/q1
SRC = os.path.join(BASE, "charts_Q1")
F1 = os.path.join(SRC, "03_预算_点击贡献匹配.png")
F2 = os.path.join(SRC, "04_预算Pareto累计占比.png")
OUT = os.path.join(SRC, "03+04_预算匹配与Pareto_合并.png")

GAP = 56        # 两图间距(px)
PAD = 36        # 四周留白(px)


def load_white(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, im).convert("RGB")


a, b = load_white(F1), load_white(F2)
H = max(a.height, b.height)
W = a.width + GAP + b.width
canvas = Image.new("RGB", (W + 2 * PAD, H + 2 * PAD), "white")
canvas.paste(a, (PAD, PAD + (H - a.height) // 2))
canvas.paste(b, (PAD + a.width + GAP, PAD + (H - b.height) // 2))
canvas.save(OUT, dpi=(300, 300))
print("已保存(横排):", OUT, canvas.size)
