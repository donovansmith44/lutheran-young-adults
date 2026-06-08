#!/usr/bin/env python3
"""Render bulletin-insert.html -> bulletin-instert.png (482x769).

Supersamples through a PDF (WeasyPrint) and rasterizes with PyMuPDF, then
downscales with Lanczos for crisp text. The output filename keeps the
original (mis)spelling so existing references stay valid.
"""
import pathlib
import fitz  # PyMuPDF
import weasyprint
from PIL import Image

ROOT = pathlib.Path(__file__).parent
HTML = ROOT / "bulletin-insert.html"
OUT = ROOT / "bulletin-instert.png"
W, H = 482, 769
SS = 4  # supersample factor

pdf_bytes = weasyprint.HTML(str(HTML), base_url=str(ROOT)).write_pdf()
doc = fitz.open(stream=pdf_bytes, filetype="pdf")
page = doc[0]
# CSS px are 96dpi; PDF points are 72dpi. zoom = (96/72) * SS gets SS× pixels.
zoom = (96 / 72) * SS
pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
img = img.resize((W, H), Image.LANCZOS)
img.save(OUT)
print(f"wrote {OUT.name} {img.size}")
