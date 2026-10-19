#!/usr/bin/env python3
"""Render an 8x8 STREAM Triad NUMA matrix (CSV) as a colour-coded SVG heatmap.

Rows = NUMA node the memory lives on (numactl --membind, outer loop), columns =
NUMA domain the threads run on (likwid-pin -c M<n>, inner loop). Cells are
coloured by locality tier, not value.

Usage: plot_heatmap.py data/aocc.csv images/aocc.svg "AOCC 3.2.0"
Stdlib only, so it runs anywhere python3 exists.
"""
import csv
import sys

NODES_PER_SOCKET = 4  # EPYC 7702 in NPS4 mode: 4 NUMA nodes per socket, 2 sockets

# Lightness steps differ (dark / pale / mid) so tiers stay apart without colour vision.
TIERS = {
    "local":  ("#2e7d32", "#ffffff", "Local node (CPU node = memory node)"),
    "socket": ("#e3efd6", "#1a1a1a", "Remote node, same socket"),
    "remote": ("#f4a3a3", "#1a1a1a", "Remote node, other socket"),
}

CELL, PAD_L, PAD_T = 64, 110, 96


def tier(mem, cpu):
    if mem == cpu:
        return "local"
    if mem // NODES_PER_SOCKET == cpu // NODES_PER_SOCKET:
        return "socket"
    return "remote"


def render(matrix, title):
    n = len(matrix)
    w = PAD_L + n * CELL + 24
    h = PAD_T + n * CELL + 100
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="Helvetica, Arial, sans-serif">',
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
        f'<text x="{PAD_L}" y="30" font-size="18" font-weight="bold" fill="#1a1a1a">'
        f'STREAM Triad bandwidth [GB/s] - {title}</text>',
        f'<text x="{PAD_L + n * CELL / 2}" y="{PAD_T - 34}" font-size="13" '
        f'text-anchor="middle" fill="#555555">CPU NUMA domain (likwid-pin -c M&lt;n&gt;)</text>',
        f'<text x="24" y="{PAD_T + n * CELL / 2}" font-size="13" text-anchor="middle" '
        f'fill="#555555" transform="rotate(-90 24 {PAD_T + n * CELL / 2})">'
        f'Memory NUMA node (numactl --membind)</text>',
    ]
    for i in range(n):
        out.append(f'<text x="{PAD_L + i * CELL + CELL / 2}" y="{PAD_T - 10}" font-size="14" '
                   f'text-anchor="middle" fill="#1a1a1a">{i}</text>')
        out.append(f'<text x="{PAD_L - 12}" y="{PAD_T + i * CELL + CELL / 2 + 5}" font-size="14" '
                   f'text-anchor="end" fill="#1a1a1a">{i}</text>')
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            fill, ink, _ = TIERS[tier(r, c)]
            x, y = PAD_L + c * CELL, PAD_T + r * CELL
            # 2px white gap between cells
            out.append(f'<rect x="{x + 1}" y="{y + 1}" width="{CELL - 2}" height="{CELL - 2}" '
                       f'rx="3" fill="{fill}"/>')
            out.append(f'<text x="{x + CELL / 2}" y="{y + CELL / 2 + 5}" font-size="14" '
                       f'text-anchor="middle" fill="{ink}">{v:.2f}</text>')
    # Socket boundary
    mid = PAD_L + NODES_PER_SOCKET * CELL
    out.append(f'<line x1="{mid}" y1="{PAD_T}" x2="{mid}" y2="{PAD_T + n * CELL}" '
               f'stroke="#1a1a1a" stroke-width="2" stroke-dasharray="4 3"/>')
    out.append(f'<line x1="{PAD_L}" y1="{PAD_T + NODES_PER_SOCKET * CELL}" x2="{PAD_L + n * CELL}" '
               f'y2="{PAD_T + NODES_PER_SOCKET * CELL}" stroke="#1a1a1a" stroke-width="2" '
               f'stroke-dasharray="4 3"/>')
    ly = PAD_T + n * CELL + 26
    for k, (fill, _, label) in enumerate(TIERS.values()):
        y = ly + k * 22
        out.append(f'<rect x="{PAD_L}" y="{y}" width="16" height="16" rx="3" fill="{fill}" '
                   f'stroke="#999999"/>')
        out.append(f'<text x="{PAD_L + 24}" y="{y + 13}" font-size="13" fill="#1a1a1a">{label}</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    assert (tier(0, 0), tier(0, 3), tier(0, 4), tier(7, 4), tier(3, 4)) == \
        ("local", "socket", "remote", "socket", "remote")
    src, dst, title = sys.argv[1:4]
    with open(src) as f:
        matrix = [[float(v) for v in row] for row in csv.reader(f) if row]
    assert len(matrix) == 8 and all(len(r) == 8 for r in matrix), "expected 8x8 matrix"
    with open(dst, "w") as f:
        f.write(render(matrix, title))
