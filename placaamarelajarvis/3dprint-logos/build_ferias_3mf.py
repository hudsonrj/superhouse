#!/usr/bin/env python3
"""Casa de férias 3MF for Anycubic Kobra X — furniture-rich, no cars/trees.

Source: ferias.png (Planner-style holiday house + garden + pool).
Scale ~1:150. ACE 4-color PLA: grass, floors+furniture, walls, pool.
"""

from __future__ import annotations

import io
import json
import math
import os
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from PIL import Image, ImageDraw
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "ferias.png"
OUT_3MF = ROOT / "Casa_Ferias_KobraX.3mf"
OUT_OVERLAY = ROOT / "ferias_overlay.png"
OUT_PREVIEW = ROOT / "ferias_preview.png"

# Original image is 400×400. 10 px ≈ 1 m. Print ~1:150.
OX, OY_SOUTH = 6.0, 308.0
PX_TO_MM = 0.66  # 312 px → 206 mm
BED = 260.0

GRASS_H = 1.40
FLOOR_H = 2.00
DECK_H = 1.80
WATER_H = 0.90
WALL_T = 1.60  # ≥ 4 linhas de 0,4 mm em PLA
WALL_H = 13.0
OVERLAP = 0.18
DOOR = 3.2  # cut thickness; opening LENGTH comes from the gap in the wall

# Furniture heights (mm) — chunky enough for 0.4 mm nozzle
Z_F = FLOOR_H - 0.08
H_SEAT = 2.6
H_BACK = 5.4
H_TABLE = 4.4
H_TOP = 0.9
H_BED = 2.8
H_PILLOW = 3.6
H_HEAD = 6.2
H_COUNTER = 5.6
H_FRIDGE = 10.5
H_TOILET = 2.8
H_TANK = 4.2
H_SINK = 5.2
H_TRAY = 1.2
H_TV = 4.8
H_LOUNGE = 2.2
H_NET = 5.0

C_GRASS = (0x4A, 0x7A, 0x3C, 255)
C_FLOOR = (0xE8, 0xD6, 0xB5, 255)
C_WALL = (0x2A, 0x2A, 0x2A, 255)
C_FURN = (0x8B, 0x4E, 0x2A, 255)
C_POOL = (0x2E, 0x9A, 0xD6, 255)

# Layer buckets: (z0, height) -> polygons
LAYERS: dict[tuple[float, float], list] = defaultdict(list)


def P(x: float, y: float) -> tuple[float, float]:
    return ((x - OX) * PX_TO_MM, (OY_SOUTH - y) * PX_TO_MM)


def mm(px: float) -> float:
    return px * PX_TO_MM


def add(poly, z0: float, h: float) -> None:
    if poly is None or poly.is_empty:
        return
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return
    LAYERS[(round(z0, 3), round(h, 3))].append(poly)


def R(cx, cy, w, d, rot=0.0):
    """Center in pixels, size in pixels, rot degrees CCW in model space."""
    x, y = P(cx, cy)
    poly = box(x - mm(w) / 2, y - mm(d) / 2, x + mm(w) / 2, y + mm(d) / 2)
    if rot:
        poly = rotate(poly, rot, origin=(x, y))
    return poly


def RR(cx, cy, w, d, rot=0.0, corner=0.9):
    """Rounded rectangle (corner in mm)."""
    x, y = P(cx, cy)
    hw, hd = mm(w) / 2, mm(d) / 2
    c = min(corner, hw - 0.15, hd - 0.15)
    poly = box(x - hw + c, y - hd + c, x + hw - c, y + hd - c).buffer(c, resolution=8)
    if rot:
        poly = rotate(poly, rot, origin=(x, y))
    return poly


def C(cx, cy, r):
    x, y = P(cx, cy)
    return Point(x, y).buffer(mm(r), resolution=14)


def wall_seg(a, b, t=WALL_T):
    return LineString([P(*a), P(*b)]).buffer(t / 2, cap_style=2, join_style=2)


def door_cut(a, b):
    return LineString([P(*a), P(*b)]).buffer(DOOR / 2, cap_style=2, join_style=2)


def iter_polygons(shape):
    if shape is None or shape.is_empty:
        return
    if shape.geom_type == "Polygon":
        yield shape
    elif shape.geom_type == "MultiPolygon":
        for g in shape.geoms:
            yield g
    else:
        for g in getattr(shape, "geoms", []):
            yield from iter_polygons(g)


def clean(poly, min_area=0.12):
    if poly is None or poly.is_empty:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        parts = [clean(g, min_area) for g in poly.geoms]
        parts = [p for p in parts if p is not None]
        return unary_union(parts) if parts else None
    if poly.area < min_area:
        return None
    holes = [h for h in poly.interiors if Polygon(h).area >= min_area]
    poly = Polygon(poly.exterior, holes).simplify(0.06, preserve_topology=True)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if poly and not poly.is_empty and poly.area >= min_area else None


def extrude(shape, height, z0=0.0):
    meshes = []
    for poly in iter_polygons(shape):
        poly = clean(poly)
        if poly is None:
            continue
        if poly.geom_type == "MultiPolygon":
            meshes.append(extrude(poly, height, z0))
            continue
        try:
            m = trimesh.creation.extrude_polygon(poly, height)
        except Exception:
            simple = Polygon(poly.exterior).buffer(0)
            if simple.is_empty or simple.geom_type != "Polygon":
                continue
            m = trimesh.creation.extrude_polygon(simple, height)
        if z0:
            m.apply_translation([0, 0, z0])
        meshes.append(m)
    if not meshes:
        return None
    out = trimesh.util.concatenate(meshes)
    out.merge_vertices()
    out.update_faces(out.nondegenerate_faces())
    out.remove_unreferenced_vertices()
    out.fix_normals()
    return out


# ---------------------------------------------------------------------------
# Furniture
# ---------------------------------------------------------------------------

def bed(cx, cy, w=22, d=16, rot=0):
    """Frame + rounded mattress + headboard + two oval pillows + foot blanket."""
    add(R(cx, cy, w + 1.2, d + 0.8, rot), Z_F, 1.6)  # frame
    add(RR(cx, cy, w, d - 1.0, rot, corner=1.1), Z_F + 1.4, H_BED - 1.0)
    hx, hy = _offset(cx, cy, 0, -(d / 2 - 1.1), rot)
    add(R(hx, hy, w + 1.6, 2.6, rot), Z_F, H_HEAD)
    # posts
    for s in (-1, 1):
        px, py = _offset(cx, cy, s * (w / 2 - 0.4), -(d / 2 - 1.1), rot)
        add(C(px, py, 1.1), Z_F, H_HEAD + 0.8)
    px1, py1 = _offset(cx, cy, -w * 0.22, -(d / 2 - 4.0), rot)
    px2, py2 = _offset(cx, cy, w * 0.22, -(d / 2 - 4.0), rot)
    add(RR(px1, py1, 7.0, 4.2, rot, 1.3), Z_F, H_PILLOW)
    add(RR(px2, py2, 7.0, 4.2, rot, 1.3), Z_F, H_PILLOW)
    fx, fy = _offset(cx, cy, 0, d / 2 - 2.2, rot)
    add(RR(fx, fy, w - 2, 3.2, rot, 0.8), Z_F + H_BED - 0.4, 0.9)  # folded blanket


def _offset(cx, cy, dx, dy, rot):
    a = math.radians(rot)
    # rot is model CCW; image x right, model x right; image y down, model y up
    # local dx along width, dy along depth in pixel space before P()
    return cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)


def nightstand(cx, cy, rot=0):
    add(R(cx, cy, 5.6, 5.6, rot), Z_F, 2.4)
    add(RR(cx, cy, 5.8, 5.8, rot, 0.5), Z_F + 2.4, 1.1)  # top
    lx, ly = _offset(cx, cy, 0, 0, rot)
    add(C(lx, ly, 1.0), Z_F + 3.5, 1.4)  # lamp base
    add(C(lx, ly, 1.6), Z_F + 4.6, 1.1)  # shade


def sofa(cx, cy, w=28, d=12, rot=0):
    add(RR(cx, cy, w, d, rot, 1.0), Z_F, H_SEAT - 0.4)
    # 3 seat cushions
    n = 3 if w >= 18 else 2
    for i in range(n):
        t = (i + 0.5) / n - 0.5
        sx, sy = _offset(cx, cy, t * (w - 6), 1.0, rot)
        add(RR(sx, sy, w / n - 1.4, d - 5.0, rot, 0.8), Z_F + H_SEAT - 0.5, 1.1)
    bx, by = _offset(cx, cy, 0, -(d / 2 - 2.1), rot)
    add(RR(bx, by, w - 1.0, 4.2, rot, 0.9), Z_F, H_BACK)
    for s in (-1, 1):
        ax, ay = _offset(cx, cy, s * (w / 2 - 1.7), 0.3, rot)
        add(RR(ax, ay, 3.4, d - 2.0, rot, 1.0), Z_F, H_BACK - 0.4)


def sofa_l(cx, cy, w=26, d=11, wing=14, rot=0):
    sofa(cx, cy, w, d, rot)
    wx, wy = _offset(cx, cy, w / 2 - d / 2 + 0.5, d / 2 + wing / 2 - 2.2, rot)
    sofa(wx, wy, wing, d, rot + 90)


def armchair(cx, cy, rot=0):
    add(RR(cx, cy, 9.5, 9.5, rot, 1.1), Z_F, H_SEAT)
    bx, by = _offset(cx, cy, 0, -3.2, rot)
    add(RR(bx, by, 9.5, 3.6, rot, 1.0), Z_F, H_BACK)
    for s in (-1, 1):
        ax, ay = _offset(cx, cy, s * 3.4, 0.4, rot)
        add(RR(ax, ay, 2.8, 8.0, rot, 0.8), Z_F, H_BACK - 0.8)


def table_rect(cx, cy, w=16, d=10, rot=0, h=H_TABLE):
    """Solid two-tier block — prints in PLA with no supports or skinny legs."""
    add(RR(cx, cy, w - 2.2, d - 2.2, rot, 0.5), Z_F, h - 0.85)
    add(RR(cx, cy, w, d, rot, 0.7), Z_F + h - 1.05, 1.05)


def table_round(cx, cy, r=8, h=H_TABLE):
    add(C(cx, cy, max(r * 0.45, 2.6)), Z_F, h - 0.85)
    add(C(cx, cy, r), Z_F + h - 1.05, 1.05)


def chair(cx, cy, rot=0):
    add(RR(cx, cy, 5.0, 5.0, rot, 0.7), Z_F, H_SEAT)
    bx, by = _offset(cx, cy, 0, -2.15, rot)
    add(RR(bx, by, 4.2, 1.6, rot, 0.5), Z_F, H_BACK)


def chairs_rect(cx, cy, tw, td, n_long=2, n_short=1, rot=0):
    # chairs along long sides
    for i in range(n_long):
        t = (i + 0.5) / n_long - 0.5
        x1, y1 = _offset(cx, cy, t * tw, -(td / 2 + 4.2), rot)
        x2, y2 = _offset(cx, cy, t * tw, (td / 2 + 4.2), rot)
        chair(x1, y1, rot)
        chair(x2, y2, rot + 180)
    for i in range(n_short):
        t = (i + 0.5) / max(n_short, 1) - 0.5
        x1, y1 = _offset(cx, cy, -(tw / 2 + 4.2), t * td, rot)
        x2, y2 = _offset(cx, cy, (tw / 2 + 4.2), t * td, rot)
        chair(x1, y1, rot + 90)
        chair(x2, y2, rot - 90)


def chairs_round(cx, cy, radius, n=4):
    for i in range(n):
        a = 2 * math.pi * i / n
        chair(cx + radius * math.cos(a), cy + radius * math.sin(a), rot=math.degrees(a) + 90)


def dining_rect(cx, cy, w=18, d=11, rot=0, n_long=2, n_short=1):
    table_rect(cx, cy, w, d, rot)
    chairs_rect(cx, cy, w, d, n_long, n_short, rot)


def dining_round(cx, cy, r=7.5, n=4):
    table_round(cx, cy, r)
    chairs_round(cx, cy, r + 5.5, n)


def coffee(cx, cy, w=12, d=7, rot=0):
    table_rect(cx, cy, w, d, rot, h=2.4)


def tv(cx, cy, w=14, rot=0):
    add(R(cx, cy, w, 5.2, rot), Z_F, 2.4)
    tx, ty = _offset(cx, cy, 0, 0.3, rot)
    add(R(tx, ty, w - 1.6, 2.6, rot), Z_F + 2.2, H_TV)  # tela ≥ 1,7 mm
    for s in (-1, 1):
        sx, sy = _offset(cx, cy, s * (w / 2 - 1.5), 0, rot)
        add(R(sx, sy, 2.6, 4.0, rot), Z_F, 3.6)


def pingpong(cx, cy, rot=0):
    w, d = 22, 12
    table_rect(cx, cy, w, d, rot, h=3.6)
    nx, ny = _offset(cx, cy, 0, 0, rot)
    add(R(nx, ny, 2.5, d - 0.4, rot), Z_F + 3.4, H_NET - 3.4)


def foosball(cx, cy, rot=0):
    add(R(cx, cy, 20, 11, rot), Z_F, 3.8)
    # center stripe
    sx, sy = _offset(cx, cy, 0, 0, rot)
    add(R(sx, sy, 4.0, 11, rot), Z_F + 3.8, 0.5)


def counter(x1, y1, x2, y2, h=H_COUNTER):
    ax, ay = P(x1, y1)
    bx, by = P(x2, y2)
    poly = box(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))
    add(poly, Z_F, h)
    # backsplash along the longer side
    add(poly.buffer(-0.35), Z_F + h, 2.4)


def sink_bowl(cx, cy, w=7, d=5, rot=0):
    add(RR(cx, cy, w, d, rot, 0.8), Z_F + H_COUNTER, 0.7)
    add(C(cx, cy, 1.5), Z_F + H_COUNTER + 0.7, 1.6)  # faucet


def stove(cx, cy, rot=0):
    add(R(cx, cy, 10, 7.5, rot), Z_F, H_COUNTER + 0.3)
    for dx in (-2.4, 2.4):
        for dy in (-1.7, 1.7):
            x, y = _offset(cx, cy, dx, dy, rot)
            add(C(x, y, 1.35), Z_F + H_COUNTER + 0.3, 0.5)
            add(C(x, y, 0.7), Z_F + H_COUNTER + 0.7, 0.35)


def fridge(cx, cy, rot=0):
    add(R(cx, cy, 7.2, 7.2, rot), Z_F, H_FRIDGE)
    fx, fy = _offset(cx, cy, 0.8, 0, rot)
    add(R(fx, fy, 1.6, 5.8, rot), Z_F + 2.0, H_FRIDGE - 3.2)


def toilet(cx, cy, rot=0):
    add(RR(cx, cy, 6.2, 7.4, rot, 1.6), Z_F, H_TOILET)
    tx, ty = _offset(cx, cy, 0, -3.8, rot)
    add(R(tx, ty, 5.8, 3.4, rot), Z_F, H_TANK)
    add(RR(cx, cy, 5.0, 4.2, rot, 1.4), Z_F + H_TOILET, 0.55)  # lid


def basin(cx, cy, rot=0):
    add(R(cx, cy, 6.5, 4.0, rot), Z_F, H_SINK - 1.4)  # pedestal
    add(RR(cx, cy, 7.4, 4.8, rot, 1.0), Z_F + H_SINK - 1.4, 1.5)
    add(C(cx, cy, 1.3), Z_F + H_SINK, 1.5)  # faucet


def shower(cx, cy, w=10, d=10, rot=0):
    """Tray + low L-curb — not a sealed stall that locks the bathroom."""
    add(R(cx, cy, w, d, rot), Z_F, H_TRAY)
    wx, wy = _offset(cx, cy, 0, -(d / 2 - 0.6), rot)
    add(R(wx, wy, w, 2.5, rot), Z_F, 3.4)
    wx, wy = _offset(cx, cy, -(w / 2 - 1.1), 0.4, rot)
    add(R(wx, wy, 2.5, d - 1.5, rot), Z_F, 3.4)


def wardrobe(cx, cy, w=16, d=6, rot=0):
    add(R(cx, cy, w, d, rot), Z_F, 9.8)
    gx, gy = _offset(cx, cy, 0, 0, rot)
    add(R(gx, gy, 1.6, d - 1.4, rot), Z_F + 1.6, 7.2)


def desk(cx, cy, w=14, d=7, rot=0):
    table_rect(cx, cy, w, d, rot, h=4.8)
    chair(*_offset(cx, cy, 0, d / 2 + 4.2, rot), rot=rot + 180)


def lounger(cx, cy, rot=0):
    z = GRASS_H - 0.05
    # chaise: foot / middle / raised head
    fx, fy = _offset(cx, cy, 0, 5.5, rot)
    add(RR(fx, fy, 7.2, 7.0, rot, 0.8), z, H_LOUNGE)
    add(RR(cx, cy, 7.2, 7.0, rot, 0.8), z, H_LOUNGE + 0.5)
    hx, hy = _offset(cx, cy, 0, -6.2, rot)
    add(RR(hx, hy, 7.2, 6.2, rot, 0.8), z, H_LOUNGE + 1.8)


def picnic(cx, cy, rot=0):
    z = GRASS_H - 0.05
    add(RR(cx, cy, 8.5, 16, rot, 0.6), z + 2.6, 1.1)
    _legs(cx, cy, 8.5, 16, rot, 2.6, inset=1.5)
    for s in (-1, 1):
        bx, by = _offset(cx, cy, s * 6.8, 0, rot)
        add(RR(bx, by, 3.4, 15, rot, 0.5), z + 1.6, 0.9)


def bench(cx, cy, w=16, rot=0):
    z = GRASS_H - 0.05
    add(RR(cx, cy, w, 5.2, rot, 0.7), z + 1.6, 0.9)
    bx, by = _offset(cx, cy, 0, -1.9, rot)
    add(RR(bx, by, w, 1.7, rot, 0.4), z + 2.2, 2.2)
    for s in (-1, 1):
        lx, ly = _offset(cx, cy, s * (w / 2 - 1.5), 0, rot)
        add(R(lx, ly, 1.6, 4.4, rot), z, 1.6)


def hammock(cx, cy, rot=0):
    z = GRASS_H - 0.05
    p1x, p1y = _offset(cx, cy, 0, -8, rot)
    p2x, p2y = _offset(cx, cy, 0, 8, rot)
    add(C(p1x, p1y, 1.35), z, 8.2)
    add(C(p2x, p2y, 1.35), z, 8.2)
    add(RR(cx, cy, 6.0, 13.5, rot, 1.8), z + 3.0, 1.15)


# ---------------------------------------------------------------------------
# Architecture
# ---------------------------------------------------------------------------

def lot_poly():
    # Jardim ao redor da casa e da piscina. Sem estacionamento / área leste.
    ring = [
        (6, 108),
        (6, 229),
        (160, 229),
        (160, 308),
        (318, 308),
        (318, 90),
        (160, 90),
        (160, 108),
    ]
    return Polygon([P(x, y) for x, y in ring])


def left_floor():
    return box(*P(6, 229), *P(157, 108)) if False else _rect(6, 108, 157, 229)


def right_floor():
    return _rect(160, 108, 312, 228)


def _rect(x1, y1, x2, y2):
    ax, ay = P(x1, y1)
    bx, by = P(x2, y2)
    return box(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))


def pool_shapes():
    # Afastada da casa (sul da parede y=227 / terraço y=240).
    deck = (
        C(256, 282, 22)
        .union(C(278, 284, 15))
        .union(_rect(236, 268, 290, 300))
        .buffer(3.0)
    )
    water = (
        C(256, 282, 17)
        .union(C(280, 286, 11))
        .union(_rect(240, 272, 282, 296))
        .buffer(0.5)
    )
    water = water.intersection(deck)
    steps = unary_union(
        [
            _rect(238, 275, 246, 289),
            _rect(242, 276, 250, 288),
        ]
    )
    return deck, water, steps


def _gaps(a, b, openings):
    """Split [a,b] around openings (each (lo, hi))."""
    cuts = sorted((min(lo, hi), max(lo, hi)) for lo, hi in openings)
    out, cur = [], a
    for lo, hi in cuts:
        if lo > cur + 0.4:
            out.append((cur, lo))
        cur = max(cur, hi)
    if b > cur + 0.4:
        out.append((cur, b))
    return out


def hwall(x1, x2, y, openings=()):
    return [((lo, y), (hi, y)) for lo, hi in _gaps(x1, x2, openings)]


def vwall(y1, y2, x, openings=()):
    return [((x, lo), (x, hi)) for lo, hi in _gaps(y1, y2, openings)]


def walls_and_doors():
    """Walls drawn with gaps — every room opens onto a hall or the living."""
    segs = []

    # ===== LEFT HOUSE — 3 quartos fechados + 3 banhos + corredor + estar =====
    segs += hwall(7, 155, 109)
    segs += hwall(7, 155, 226)
    segs += vwall(109, 226, 7)
    segs += vwall(109, 226, 155, openings=[(182, 194)])

    # Quarto 1 NW (cama+mesa) x=7-58 y=109-178 — só abre no corredor (sul)
    segs += vwall(109, 178, 58)
    segs += hwall(7, 58, 178, openings=[(22, 36)])

    # Banho 1 x=58-78 y=109-138 — porta sul p/ corredor
    segs += vwall(109, 138, 78)
    segs += hwall(58, 78, 138, openings=[(62, 74)])

    # Banho 2 x=78-100 y=109-138 — porta sul p/ corredor
    segs += vwall(109, 178, 100)
    segs += hwall(78, 100, 138, openings=[(84, 96)])

    # Quarto 2 NE (cama+mesa) x=100-155 y=109-178 — só abre no corredor (sul)
    segs += hwall(100, 155, 178, openings=[(118, 132)])

    # Corredor (laranja) x=58-100 y=138-178 — liga quartos, banhos e o estar
    segs += hwall(58, 100, 178, openings=[(70, 84)])

    # Estar sul x=7-100 y=178-226
    segs += vwall(178, 226, 100, openings=[(186, 198), (210, 222)])

    # Banho 3 x=100-128 y=178-202
    segs += hwall(100, 128, 202)
    segs += vwall(178, 202, 128, openings=[(186, 198)])
    # Quarto 3 L: (128-155,178-226)+(100-128,202-226)

    # ===== RIGHT HOUSE  (161,109)-(311,227) — open plan =====
    segs += hwall(161, 311, 109)
    segs += vwall(109, 227, 161, openings=[(172, 198)])  # passage from left house
    segs += vwall(109, 227, 311)
    # South wall: big sliding door to the pool
    segs += hwall(161, 311, 227, openings=[(210, 282)])

    # North baths + bedroom — doors into the salão
    segs += vwall(109, 134, 214)
    segs += vwall(109, 134, 256)
    segs += hwall(
        214,
        311,
        134,
        openings=[
            (222, 238),  # bath A
            (242, 252),  # bath B
            (272, 292),  # bedroom
        ],
    )

    # SW WC — door into the salão (east wall)
    segs += hwall(161, 192, 190)
    segs += vwall(190, 227, 192, openings=[(200, 216)])

    return unary_union([wall_seg(a, b) for a, b in segs])


def place_furniture():
    # Furniture stays off doorways. Hall / openings kept clear.

    # ===== LEFT HOUSE: 3 quartos fechados + 3 banhos + estar =====
    # Quarto 1 (NW estúdio) — cama no norte, mesa/pingue-pongue no sul, porta sul
    bed(30, 120, w=18, d=13, rot=0)
    nightstand(16, 120)
    nightstand(44, 120)
    pingpong(28, 152, rot=0)
    dining_rect(48, 152, w=10, d=7, n_long=2, n_short=0)

    # Banho 1
    shower(68, 118, 8, 8, rot=0)
    toilet(64, 132, rot=90)
    basin(72, 132, rot=-90)

    # Banho 2
    shower(88, 118, 8, 8, rot=0)
    toilet(84, 132, rot=90)
    basin(94, 132, rot=-90)

    # Quarto 2 (NE estúdio) — cama norte, estar sul, porta sul
    bed(128, 120, w=18, d=13, rot=0)
    nightstand(114, 120)
    nightstand(142, 120)
    wardrobe(150, 132, 5, 11, rot=90)
    dining_rect(118, 150, w=10, d=7, n_long=2, n_short=0)
    pingpong(140, 152, rot=90)
    tv(128, 162, w=10, rot=180)

    # Estar sul — porta leste p/ banho 3 e quarto 3
    sofa_l(24, 198, w=20, d=9, wing=11, rot=0)
    armchair(46, 210, rot=-20)
    coffee(32, 210, 9, 5.5)
    tv(16, 218, 12, rot=180)
    dining_rect(62, 200, w=12, d=8, n_long=2, n_short=0)
    counter(8, 220, 70, 225)
    stove(30, 222)
    sink_bowl(52, 222)
    fridge(14, 214)

    # Banho 3
    shower(114, 186, 8, 8, rot=0)
    toilet(106, 190, rot=90)
    basin(118, 196, rot=180)

    # Quarto 3 SE — cama, porta oeste e norte livres
    bed(142, 208, w=16, d=12, rot=90)
    nightstand(150, 194)
    wardrobe(148, 222, 9, 4.5, rot=0)

    # ===== RIGHT HOUSE — salão aberto =====
    # North baths — doors on south wall free
    shower(224, 118, 9, 9, rot=0)
    toilet(232, 128, rot=180)
    basin(218, 128, rot=90)
    shower(248, 118, 9, 9, rot=0)
    toilet(252, 128, rot=180)

    # NE bedroom — bed north, south door free
    bed(284, 118, w=22, d=14, rot=0)
    nightstand(270, 118)
    nightstand(298, 118)
    wardrobe(306, 122, 5, 12, rot=90)

    # Two banquet tables, chairs only on the long sides, aisle in the middle
    dining_rect(218, 160, w=20, d=11, rot=0, n_long=3, n_short=0)
    dining_rect(256, 160, w=20, d=11, rot=0, n_long=3, n_short=0)
    add(R(218, 160, 16, 3.5, 0), Z_F + H_TABLE, 0.45)

    # round table west, north of the passage so the link between houses stays open
    dining_round(180, 148, r=6.5, n=4)

    # kitchen west of the sliding door (south-center stays open to the pool)
    counter(194, 214, 208, 226)
    stove(201, 220)
    fridge(198, 206)
    table_rect(200, 198, 12, 6, h=H_COUNTER)  # island, still west of the aisle
    chair(200, 190, rot=180)

    # sofa / TV lounge SE — east of the garden opening
    sofa(294, 214, w=22, d=10, rot=180)
    armchair(278, 206, rot=35)
    coffee(294, 202, 10, 6)
    tv(306, 216, 11, rot=-90)

    # desk on the east wall, north of the sofa
    desk(302, 178, 11, 6, rot=-90)

    # SW WC — door on east wall (x=192) kept clear
    toilet(172, 204, rot=90)
    basin(172, 218, rot=90)


PLA_PRESET = "Anycubic PLA @Anycubic Kobra X 0.4 nozzle"
PRINT_PRESET = "0.20mm Standard @Anycubic Kobra X 0.4 nozzle"
PRINTER_PRESET = "Anycubic Kobra X 0.4 nozzle"
PLA_FILAMENT_ID = "GFPLA"
APP_METADATA = "BambuStudio-2.0.0.3"
ACE_TEMPLATE_3MF = Path.home() / "Downloads" / "Regular_ACE.3mf"
_OBJ_SUF = "61cb-4c03-9d28-80fed5dfa1dc"
_MESH_SUF = "81cb-4c03-9d28-80fed5dfa1dc"
_COMP_SUF = "b206-40ff-9872-83e8017abed1"
_ITEM_SUF = "b1ec-4553-aec9-835e5b724bb4"
_SYSTEM = (
    Path(os.environ.get("APPDATA", ""))
    / "AnycubicSlicerNext"
    / "system"
    / "Anycubic"
)
PLA_JSON = _SYSTEM / "filament" / f"{PLA_PRESET}.json"
PRINTER_JSON = _SYSTEM / "machine" / f"{PRINTER_PRESET}.json"
PROCESS_JSON = _SYSTEM / "process" / f"{PRINT_PRESET}.json"
_SKIP_PRESET_KEYS = {
    "type",
    "from",
    "setting_id",
    "inherits",
    "name",
    "instantiation",
    "version",
    "is_custom_defined",
    "compatible_printers",
    "compatible_prints",
    "compatible_printers_condition",
    "compatible_prints_condition",
}


def _load_preset(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k not in _SKIP_PRESET_KEYS}


def _expand_filament(preset: dict, n: int) -> dict:
    out = {}
    for key, raw in preset.items():
        if isinstance(raw, list):
            if len(raw) == 1:
                out[key] = [raw[0]] * n
            else:
                out[key] = raw
        elif key == "filament_id":
            out[key] = [raw] * n
        else:
            out[key] = raw
    return out


def _pla_project_settings(parts) -> str:
    """JSON project_settings in the same shape Anycubic Slicer Next 2.0 writes."""
    n = len(parts)
    colors = [f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}" for _, _, c in parts]
    cfg = None
    if ACE_TEMPLATE_3MF.is_file():
        with zipfile.ZipFile(ACE_TEMPLATE_3MF) as z:
            cfg = json.loads(z.read("Metadata/project_settings.config"))
    if cfg is None:
        cfg = {}
        cfg.update(_load_preset(PRINTER_JSON))
        cfg.update(_load_preset(PROCESS_JSON))
        cfg.update(_expand_filament(_load_preset(PLA_JSON), n))
    cfg["printer_model"] = "Anycubic Kobra X"
    cfg["printer_settings_id"] = PRINTER_PRESET
    cfg["print_settings_id"] = PRINT_PRESET
    cfg["printer_variant"] = "0.4"
    cfg["enable_support"] = "0"
    cfg["filament_settings_id"] = [PLA_PRESET] * n
    cfg["filament_type"] = ["PLA"] * n
    cfg["filament_vendor"] = ["Anycubic"] * n
    cfg["filament_id"] = [PLA_FILAMENT_ID] * n
    cfg["filament_ids"] = [PLA_FILAMENT_ID] * n
    cfg["filament_colour"] = colors
    cfg["filament_multi_colour"] = colors
    cfg["default_filament_colour"] = colors
    cfg["default_filament_profile"] = [PLA_PRESET] * n
    cfg["filament_map"] = list(range(1, n + 1))
    cfg["filament_map_mode"] = "Auto For Flush"
    if not isinstance(cfg.get("flush_volumes_matrix"), list) or len(cfg["flush_volumes_matrix"]) != n * n:
        flush = []
        for i in range(n):
            for j in range(n):
                flush.append("0" if i == j else "140")
        cfg["flush_volumes_matrix"] = flush
        cfg["flush_volumes_vector"] = ["140"] * (n * 2)
    return json.dumps(cfg, indent=4) + "\n"


def _slice_info(parts) -> str:
    fils = []
    for i, (_, _, c) in enumerate(parts, start=1):
        hexc = f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}"
        fils.append(
            f'    <filament id="{i}" tray_info_idx="{PLA_FILAMENT_ID}" '
            f'type="PLA" color="{hexc}" used_m="0" used_g="0"/>'
        )
    body = "\n".join(fils)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <header>
    <header_item key="X-ACNext-Client-Type" value="slicer"/>
    <header_item key="X-ACNext-Client-Version" value="2.0.0.3 20260904033713"/>
  </header>
  <plate>
    <metadata key="index" value="1"/>
    <metadata key="printer_model_id" value="Anycubic Kobra X"/>
    <metadata key="nozzle_diameters" value="0.4"/>
{body}
    <model_instance>
      <metadata key="object_id" value="2"/>
      <metadata key="instance_id" value="0"/>
    </model_instance>
  </plate>
</config>
"""


def _mesh_model_xml(mesh, obj_id: int, mesh_uuid: str) -> str:
    verts = "\n".join(
        f'     <vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x, y, z in mesh.vertices
    )
    tris = "\n".join(
        f'     <triangle v1="{int(a)}" v2="{int(b)}" v3="{int(c)}"/>' for a, b, c in mesh.faces
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
  <object id="{obj_id}" p:UUID="{mesh_uuid}" type="model">
   <mesh>
    <vertices>
{verts}
    </vertices>
    <triangles>
{tris}
    </triangles>
   </mesh>
  </object>
 </resources>
 <build/>
</model>
"""


def write_3mf(path: Path, parts, thumbnail: bytes) -> None:
    """Write an Anycubic Slicer Next 2.0 project 3MF (Bambu production layout)."""
    assembly_id = 2
    n = len(parts)
    bw = max(p[0].extents[0] for p in parts)
    bh = max(p[0].extents[1] for p in parts)
    cx, cy = (BED - bw) / 2.0, (BED - bh) / 2.0
    components, parts_meta, rel_lines, object_files = [], [], [], []
    for i, (mesh, name, _color) in enumerate(parts):
        mesh_id = 1 + i * 2
        fname = "".join(ch if ch.isalnum() else "_" for ch in name) + f"_{mesh_id}.model"
        obj_path = f"/3D/Objects/{fname}"
        mesh_uuid = f"{mesh_id:08x}-{_MESH_SUF}"
        comp_uuid = f"{mesh_id:08x}-{_COMP_SUF}"
        object_files.append((obj_path.lstrip("/"), _mesh_model_xml(mesh, mesh_id, mesh_uuid)))
        components.append(
            f'    <component p:path="{obj_path}" objectid="{mesh_id}" '
            f'p:UUID="{comp_uuid}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
        )
        rel_lines.append(
            f' <Relationship Target="{obj_path}" Id="rel-{i + 1}" '
            f'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        )
        parts_meta.append(
            f"""    <part id="{mesh_id}" subtype="normal_part">
      <metadata key="name" value="{escape(name)}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="extruder" value="{i + 1}"/>
      <mesh_stat edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>"""
        )
    asm_uuid = f"{assembly_id:08x}-{_OBJ_SUF}"
    item_uuid = f"{assembly_id:08x}-{_ITEM_SUF}"
    maps = " ".join(str(i + 1) for i in range(n))
    model_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">{APP_METADATA}</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">Casa de ferias</metadata>
 <metadata name="Description">4 PLA ACE. Kobra X 0.4 mm, sem suporte.</metadata>
 <metadata name="Thumbnail_Middle">/Metadata/plate_1.png</metadata>
 <metadata name="Thumbnail_Small">/Metadata/plate_1_small.png</metadata>
 <resources>
  <object id="{assembly_id}" p:UUID="{asm_uuid}" type="model">
   <components>
{chr(10).join(components)}
   </components>
  </object>
 </resources>
 <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">
  <item objectid="{assembly_id}" p:UUID="{item_uuid}" transform="1 0 0 0 1 0 0 0 1 {cx:.4f} {cy:.4f} 0" printable="1"/>
 </build>
</model>
"""
    model_settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="{assembly_id}">
    <metadata key="name" value="Casa de ferias"/>
    <metadata key="extruder" value="1"/>
{chr(10).join(parts_meta)}
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value="Kobra X"/>
    <metadata key="locked" value="false"/>
    <metadata key="filament_map_mode" value="Auto For Flush"/>
    <metadata key="filament_maps" value="{maps}"/>
    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>
    <model_instance>
      <metadata key="object_id" value="{assembly_id}"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="1"/>
    </model_instance>
  </plate>
  <assemble>
   <assemble_item object_id="{assembly_id}" instance_id="0" transform="1 0 0 0 1 0 0 0 1 {cx:.4f} {cy:.4f} 0" offset="0 0 0"/>
  </assemble>
</config>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Default Extension="gcode" ContentType="text/x.gcode"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
 <Relationship Target="/Metadata/plate_1.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>
</Relationships>
"""
    model_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        + "\n".join(rel_lines)
        + "\n</Relationships>\n"
    )
    custom_gcode = """<?xml version="1.0" encoding="utf-8"?>
<custom_gcodes_per_layer>
<plate>
<plate_info id="1"/>
<mode value="MultiExtruder"/>
</plate>
</custom_gcodes_per_layer>
"""
    filament_override = json.dumps(
        {
            "filament_settings_id": [PLA_PRESET],
            "filament_type": ["PLA"],
            "filament_vendor": ["Anycubic"],
            "filament_id": PLA_FILAMENT_ID,
            "from": "project",
            "inherits": PLA_PRESET,
            "name": PLA_PRESET,
        },
        indent=4,
    ) + "\n"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model_xml)
        z.writestr("3D/_rels/3dmodel.model.rels", model_rels)
        for obj_name, obj_xml in object_files:
            z.writestr(obj_name, obj_xml)
        z.writestr("Metadata/plate_1.png", thumbnail)
        z.writestr("Metadata/plate_1_small.png", thumbnail)
        z.writestr("Metadata/thumbnail.png", thumbnail)
        z.writestr("Metadata/model_settings.config", model_settings)
        z.writestr("Metadata/project_settings.config", _pla_project_settings(parts))
        z.writestr("Metadata/slice_info.config", _slice_info(parts))
        z.writestr("Metadata/custom_gcode_per_layer.xml", custom_gcode)
        for i in range(1, n + 1):
            z.writestr(f"Metadata/filament_settings_{i}.config", filament_override)


def draw_poly(d, shape, fill, outline, width=1):
    def to_px(mx, my):
        return mx / PX_TO_MM + OX, OY_SOUTH - my / PX_TO_MM

    for poly in iter_polygons(shape):
        pts = [to_px(x, y) for x, y in poly.exterior.coords]
        d.line(pts, fill=outline, width=width)


def overlay(grass, floors, deck, water, walls, furn):
    im = Image.open(SRC).convert("RGB").resize((800, 800), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(im)
    # draw in original px scaled 2x — helper uses original P so scale after
    src = Image.open(SRC).convert("RGBA")
    ov = src.copy()
    dr = ImageDraw.Draw(ov)

    def paint(shape, color, w=2):
        def to_px(mx, my):
            return mx / PX_TO_MM + OX, OY_SOUTH - my / PX_TO_MM

        for poly in iter_polygons(shape):
            pts = [to_px(x, y) for x, y in poly.exterior.coords]
            dr.line(pts, fill=color, width=w)

    paint(grass, (40, 160, 50, 255), 2)
    paint(floors, (200, 160, 80, 255), 2)
    paint(deck, (180, 150, 90, 255), 2)
    paint(water, (40, 90, 220, 255), 2)
    paint(walls, (220, 30, 30, 255), 2)
    paint(furn, (140, 60, 20, 255), 1)
    ov = ov.resize((800, 800), Image.Resampling.NEAREST)
    ov.convert("RGB").save(OUT_OVERLAY)
    print("overlay", OUT_OVERLAY)


def preview(grass, floors, deck, water, walls, furn) -> bytes:
    fig, ax = plt.subplots(figsize=(11, 8), dpi=130)
    fig.patch.set_facecolor("#3a3a3a")
    ax.set_facecolor("#3a3a3a")

    def add_s(shape, color, z=1):
        for poly in iter_polygons(shape):
            verts, codes = [], []
            ext = np.asarray(poly.exterior.coords)
            verts.extend(ext)
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(ext) - 2) + [MplPath.CLOSEPOLY])
            for interior in poly.interiors:
                hole = np.asarray(interior.coords)
                verts.extend(hole)
                codes.extend(
                    [MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 2) + [MplPath.CLOSEPOLY]
                )
            ax.add_patch(
                PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", zorder=z)
            )

    add_s(grass, "#4a7a3c", 1)
    add_s(floors, "#e8d6b5", 2)
    add_s(deck, "#d9c4a0", 3)
    add_s(water, "#3a8fd0", 4)
    add_s(walls, "#2a2a2a", 5)
    add_s(furn, "#8b4e2a", 6)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")
    ax.set_title("Casa de ferias  ·  1:150  ·  Kobra X  ·  sem carros/arvores", color="#ddd", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT_PREVIEW, dpi=130)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    _iso(grass, floors, deck, water, walls, furn)
    return buf.getvalue()


def _oblique(x, y, z, sx=0.38, sy=0.26):
    return x + z * sx, y + z * sy


def _iso_draw(ax, shape, z0, z1, top, side, zorder):
    for poly in iter_polygons(shape):
        ring = np.asarray(poly.exterior.coords)
        xs0, ys0 = _oblique(ring[:, 0], ring[:, 1], z0)
        xs1, ys1 = _oblique(ring[:, 0], ring[:, 1], z1)
        for i in range(len(ring) - 1):
            ax.fill(
                [xs0[i], xs0[i + 1], xs1[i + 1], xs1[i]],
                [ys0[i], ys0[i + 1], ys1[i + 1], ys1[i]],
                facecolor=side,
                edgecolor="none",
                zorder=zorder,
            )
        verts, codes = [], []
        ox, oy = _oblique(ring[:, 0], ring[:, 1], z1)
        verts.extend(np.column_stack([ox, oy]))
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(ring) - 2) + [MplPath.CLOSEPOLY])
        for interior in poly.interiors:
            hole = np.asarray(interior.coords)
            hx, hy = _oblique(hole[:, 0], hole[:, 1], z1)
            verts.extend(np.column_stack([hx, hy]))
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 2) + [MplPath.CLOSEPOLY])
        ax.add_patch(
            PathPatch(MplPath(verts, codes), facecolor=top, edgecolor="none", lw=0, zorder=zorder + 1)
        )


def _iso(grass, floors, deck, water, walls, furn):
    fig, ax = plt.subplots(figsize=(12, 8), dpi=140)
    fig.patch.set_facecolor("#3a3a3a")
    ax.set_facecolor("#3a3a3a")
    _iso_draw(ax, grass, 0, GRASS_H, "#4a7a3c", "#3a6230", 1)
    _iso_draw(ax, floors, 0, FLOOR_H, "#e8d6b5", "#c9b48e", 2)
    _iso_draw(ax, deck, 0, DECK_H, "#d9c4a0", "#bba37e", 3)
    _iso_draw(ax, water, 0, WATER_H, "#3a8fd0", "#2a6fa8", 4)
    _iso_draw(ax, walls, FLOOR_H, WALL_H, "#2a2a2a", "#1a1a1a", 5)
    _iso_draw(ax, furn, FLOOR_H, FLOOR_H + 5.5, "#9a5a32", "#6e3c20", 8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Relevo — paredes, camas, sofás, mesas, piscina", color="#ddd", fontsize=11)
    fig.tight_layout()
    fig.savefig(ROOT / "ferias_iso.png", dpi=140)
    plt.close(fig)


def union_layers(keys) -> object:
    polys = []
    for k in keys:
        polys.extend(LAYERS.get(k, []))
    if not polys:
        return None
    return unary_union(polys)


def extrude_layers(select=None):
    meshes = []
    for (z0, h), polys in sorted(LAYERS.items()):
        if select is not None and (z0, h) not in select:
            continue
        u = unary_union(polys)
        m = extrude(u, h, z0)
        if m is not None:
            meshes.append(m)
    if not meshes:
        return None
    out = trimesh.util.concatenate(meshes)
    try:
        out = trimesh.boolean.union([out], engine="manifold")
    except Exception:
        pass
    out.merge_vertices()
    out.update_faces(out.nondegenerate_faces())
    out.remove_unreferenced_vertices()
    out.fix_normals()
    return out


def build():
    print("Casa de ferias from ferias.png ...")
    grass = lot_poly()
    floors = unary_union(
        [
            left_floor(),
            right_floor(),
            _rect(154, 170, 163, 200),  # covered passage
            _rect(210, 227, 282, 240),  # terraço — não encosta na piscina
        ]
    )
    deck, water, steps = pool_shapes()
    deck = deck.difference(floors)
    water = water.difference(floors)
    steps = steps.intersection(deck).difference(water)
    # buraco no gramado para a água azul assentar
    grass = grass.difference(water.buffer(0.35))
    deck = deck.difference(water.buffer(0.15))
    walls = walls_and_doors()

    place_furniture()
    furn = unary_union([p for polys in LAYERS.values() for p in polys])

    overlay(grass, floors, deck, water, walls, furn)
    thumb = preview(grass, floors, deck, water, walls, furn)

    print("Extruding parts...")
    grass_m = extrude(grass, GRASS_H, 0)
    floor_m = extrude(floors, FLOOR_H, 0)
    deck_m = extrude(deck, DECK_H, 0)
    water_m = extrude(water, WATER_H + 0.15, 0)
    step_m = extrude(steps, 1.35, 0)
    piso_bits = [m for m in (floor_m, deck_m, step_m) if m is not None]
    piso = trimesh.util.concatenate(piso_bits)
    try:
        piso = trimesh.boolean.union(piso_bits, engine="manifold")
    except Exception:
        pass
    piso.merge_vertices()
    piso.update_faces(piso.nondegenerate_faces())
    piso.remove_unreferenced_vertices()

    wall_m = extrude(walls, WALL_H - FLOOR_H + OVERLAP, FLOOR_H - OVERLAP)
    furn_m = extrude_layers()
    # ACE has 4 slots. Furniture stays 3D but shares the beige PLA with floors
    # so the slicer never creates a 5th filament (Kobra X slot 5 is TPU).
    piso = trimesh.util.concatenate([piso, furn_m])
    piso.merge_vertices()
    piso.update_faces(piso.nondegenerate_faces())
    piso.remove_unreferenced_vertices()

    parts = []
    for name, m, col in [
        ("Gramado", grass_m, C_GRASS),
        ("Pisos e moveis", piso, C_FLOOR),
        ("Paredes", wall_m, C_WALL),
        ("Piscina", water_m, C_POOL),
    ]:
        b = m.bounds
        s = b[1] - b[0]
        print(
            f"  {name:16s} tris={len(m.faces):6d} watertight={m.is_watertight} "
            f"size={s[0]:6.1f} x {s[1]:6.1f} x {s[2]:5.2f} mm"
        )
        if s[0] > BED + 1 or s[1] > BED + 1:
            raise RuntimeError(f"{name} exceeds Kobra X bed")
        parts.append((m, name, col))

    write_3mf(OUT_3MF, parts, thumb)
    print(f"Wrote {OUT_3MF} ({OUT_3MF.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    build()
