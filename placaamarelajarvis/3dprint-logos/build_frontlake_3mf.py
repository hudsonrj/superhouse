#!/usr/bin/env python3
"""Frontlake apartment 3MF for Anycubic Kobra X — 1:50, ACE 4-color PLA.

Traced from fl.jpg.
  1 piso preto · 2 paredes brancas · 3 móveis prata · 4 bancada branca
"""

from __future__ import annotations

import io
import json
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
from shapely.affinity import rotate, scale, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "fl.jpg"
OUT_3MF = ROOT / "Frontlake_KobraX.3mf"
OUT_OVERLAY = ROOT / "frontlake_overlay.png"
OUT_PREVIEW = ROOT / "frontlake_preview.png"

# fl.jpg: quarto 2.80 m ≈ 295 px → 105 px/m. Print at 1:50 so furniture reads.
PX_PER_M = 105.0
OX, OY_SOUTH = 28.0, 879.0
MM_PER_M = 20.0  # 1 m → 20 mm  (1:50)
BED = 260.0

WALL_T = 2.80  # ~14 cm
WALL_H = 22.0
FLOOR_H = 2.00
OVERLAP = 0.18
SILL_H = 6.50
RAIL_H = 7.00
DOOR_CUT = 3.40

Z0 = FLOOR_H - 0.10
H_SEAT = 8.40
H_CUSH = 10.20
H_BACK = 16.20
H_ARM = 12.60
H_TABLE = 11.60
H_TOP = 2.00
H_BED = 6.60
H_MATT = 9.60
H_HEAD = 17.40
H_PILLOW = 11.80
H_WARD = 21.40
H_COUNTER = 12.60
H_UPPER = 20.60
H_FRIDGE = 21.80
H_TV = 15.20
H_STOOL = 9.20
H_TOILET = 7.40
H_TANK = 13.20
H_SINK = 13.60
H_TRAY = 3.00

C_FLOOR = (0x14, 0x14, 0x14, 255)  # preto
C_WALL = (0xF5, 0xF5, 0xF3, 255)  # paredes brancas
C_FURN = (0xC5, 0xC9, 0xCE, 255)  # móveis prata
C_FIXT = (0xF7, 0xF7, 0xF5, 255)  # bancada branca

FURN: dict[tuple[float, float], list] = defaultdict(list)
FIXT: dict[tuple[float, float], list] = defaultdict(list)

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


def P(x: float, y: float) -> tuple[float, float]:
    return ((x - OX) * MM_PER_M / PX_PER_M, (OY_SOUTH - y) * MM_PER_M / PX_PER_M)


def wall_line(a, b, t: float = WALL_T) -> Polygon:
    return LineString([P(*a), P(*b)]).buffer(t / 2.0, cap_style=2, join_style=2)


def door_cut(a, b) -> Polygon:
    return LineString([P(*a), P(*b)]).buffer(DOOR_CUT / 2.0, cap_style=2, join_style=2)


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


def clean_polygon(poly: Polygon, min_area: float = 0.20) -> Polygon | None:
    if poly is None or poly.is_empty:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly is None or poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        parts = [clean_polygon(g, min_area) for g in poly.geoms]
        parts = [p for p in parts if p is not None]
        return unary_union(parts) if parts else None
    if poly.area < min_area:
        return None
    holes = [h for h in poly.interiors if Polygon(h).area >= min_area]
    poly = Polygon(poly.exterior, holes).simplify(0.06, preserve_topology=True)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if poly and not poly.is_empty and poly.area >= min_area else None


def extrude_shape(shape, height: float, z0: float = 0.0) -> trimesh.Trimesh:
    meshes = []
    for poly in iter_polygons(shape):
        poly = clean_polygon(poly)
        if poly is None:
            continue
        if poly.geom_type == "MultiPolygon":
            meshes.append(extrude_shape(poly, height, z0))
            continue
        try:
            m = trimesh.creation.extrude_polygon(poly, height)
        except Exception:
            simple = Polygon(poly.exterior).buffer(0)
            if simple.is_empty or simple.geom_type != "Polygon":
                continue
            m = trimesh.creation.extrude_polygon(simple, height)
        if z0:
            m.apply_translation([0.0, 0.0, z0])
        meshes.append(m)
    if not meshes:
        raise RuntimeError("extrusion produced no mesh")
    out = trimesh.util.concatenate(meshes)
    out.merge_vertices()
    out.update_faces(out.nondegenerate_faces())
    out.remove_unreferenced_vertices()
    out.fix_normals()
    return out


def rb(x1, y1, x2, y2, r: float = 0.0) -> Polygon:
    ax, ay = P(x1, y1)
    bx, by = P(x2, y2)
    g = box(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))
    if r > 0:
        g = g.buffer(r, join_style=1).buffer(-r, join_style=1)
    return g


def mm_box(cx, cy, w, d, rot=0.0, r=0.0) -> Polygon:
    g = box(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2)
    if r > 0:
        g = g.buffer(r, join_style=1).buffer(-r, join_style=1)
    if rot:
        g = rotate(g, rot, origin=(cx, cy), use_radians=False)
    return g


def add(bucket, poly, z0, h):
    if poly is None or poly.is_empty:
        return
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return
    bucket[(round(float(z0), 3), round(float(h), 3))].append(poly)


def extrude_bucket(bucket) -> trimesh.Trimesh:
    meshes = []
    for (z0, h), polys in bucket.items():
        shape = unary_union(polys)
        if shape is None or shape.is_empty:
            continue
        meshes.append(extrude_shape(shape, h, z0))
    if not meshes:
        raise RuntimeError("empty furniture bucket")
    out = trimesh.util.concatenate(meshes)
    out.merge_vertices()
    out.update_faces(out.nondegenerate_faces())
    out.remove_unreferenced_vertices()
    return out


# --- walls / floor (same trace as the walls-only planta) ---
def building_walls():
    segs = [
        ((32, 360), (32, 879)),
        ((32, 879), (206, 879)),
        ((206, 879), (281, 879)),
        ((32, 360), (122, 360)),
        ((216, 360), (281, 360)),
        ((281, 360), (281, 733)),
        ((281, 733), (281, 879)),
        ((206, 675), (281, 675)),
        ((206, 675), (206, 786)),
        ((206, 857), (206, 879)),
        ((281, 733), (330, 733)),
        ((330, 733), (330, 780)),
        ((330, 850), (330, 879)),
        ((281, 879), (330, 879)),
        ((107, 33), (461, 33)),
        ((107, 33), (107, 360)),
        ((461, 33), (461, 114)),
        ((461, 114), (575, 114)),
        ((575, 114), (1192, 114)),
        ((1192, 114), (1192, 737)),
        ((575, 114), (575, 260)),
        ((868, 114), (868, 260)),
        ((575, 260), (603, 260)),
        ((674, 260), (930, 260)),
        ((1000, 260), (1192, 260)),
        ((590, 368), (590, 737)),
        ((685, 368), (890, 368)),
        ((890, 368), (890, 737)),
        ((590, 737), (604, 737)),
        ((754, 737), (902, 737)),
        ((1054, 737), (1192, 737)),
        ((330, 737), (334, 737)),
    ]
    walls = unary_union([wall_line(a, b) for a, b in segs])
    doors = unary_union(
        [
            door_cut((122, 360), (216, 360)),
            door_cut((206, 786), (206, 857)),
            door_cut((603, 260), (674, 260)),
            door_cut((930, 260), (1000, 260)),
            door_cut((590, 368), (685, 368)),
            door_cut((334, 737), (576, 737)),
            door_cut((330, 780), (330, 850)),
        ]
    )
    walls = walls.difference(doors)
    sills = unary_union(
        [
            wall_line((604, 737), (754, 737)),
            wall_line((902, 737), (1054, 737)),
        ]
    )
    return walls, sills, doors


def varanda_shapes():
    curve_px = [
        (330, 879),
        (330, 998),
        (350, 1006),
        (370, 1010),
        (390, 1013),
        (410, 1017),
        (430, 1021),
        (450, 1025),
        (470, 1029),
        (490, 1033),
        (510, 1037),
        (530, 1041),
        (550, 1045),
        (570, 1049),
        (590, 1052),
        (610, 1055),
        (630, 1057),
        (650, 1056),
        (670, 1055),
        (690, 1051),
        (710, 1046),
        (730, 1039),
        (750, 1030),
        (770, 1019),
        (790, 1006),
        (810, 989),
        (830, 970),
        (850, 944),
        (870, 911),
        (885, 860),
        (890, 800),
        (890, 737),
        (330, 737),
    ]
    floor = Polygon([P(x, y) for x, y in curve_px]).buffer(0)
    rail = LineString([P(x, y) for x, y in curve_px[:-1]]).buffer(
        WALL_T / 2.0, cap_style=2, join_style=1
    )
    return floor, rail


def footprint(varanda_floor: Polygon) -> Polygon:
    def r(x1, y1, x2, y2):
        ax, ay = P(x1, y1)
        bx, by = P(x2, y2)
        return box(min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))

    parts = [
        r(28, 879, 281, 360),
        r(103, 360, 461, 28),
        r(103, 742, 590, 360),
        r(461, 360, 590, 114),
        r(564, 742, 1196, 114),
        r(281, 879, 334, 733),
        varanda_floor,
    ]
    return unary_union(parts).buffer(0.25).buffer(-0.25)


# --- modern furniture (all silver) ---
def oval(cx, cy, rx, ry, rot=0.0) -> Polygon:
    g = translate(scale(Point(0, 0).buffer(1.0, resolution=28), rx, ry, origin=(0, 0)), cx, cy)
    if rot:
        g = rotate(g, rot, origin=(cx, cy), use_radians=False)
    return g


def placed(cx, cy, dx, dy, w, d, rot=0.0, r=0.0) -> Polygon:
    g = mm_box(cx + dx, cy + dy, w, d, 0.0, r)
    if rot:
        g = rotate(g, rot, origin=(cx, cy), use_radians=False)
    return g


def chair(cx, cy, rot=0.0):
    add(FURN, placed(cx, cy, 0, 0, 7.6, 7.6, rot, 1.6), Z0, H_SEAT - 1.5)
    add(FURN, placed(cx, cy, 0, 0.15, 7.0, 6.8, rot, 1.5), Z0 + H_SEAT - 1.5, 1.7)
    add(FURN, placed(cx, cy, 0, 2.7, 7.4, 2.3, rot, 1.0), Z0, H_BACK - 2.4)
    add(FURN, placed(cx, cy, 0, 2.85, 6.6, 1.7, rot, 0.8), Z0 + H_BACK - 2.4, 2.6)


def stool(cx, cy):
    add(FURN, mm_box(cx, cy, 6.4, 6.4, r=1.7), Z0, H_STOOL - 1.4)
    add(FURN, mm_box(cx, cy, 5.8, 5.8, r=1.6), Z0 + H_STOOL - 1.4, 1.6)


def sofa(cx, cy, length, depth, rot=0.0, seats=3):
    """Sofa facing local +Y (back on −Y)."""
    add(FURN, placed(cx, cy, 0, 0, length, depth, rot, 1.8), Z0, H_SEAT - 1.6)
    add(FURN, placed(cx, cy, 0, -depth / 2 + 1.6, length - 0.8, 3.2, rot, 1.1), Z0, H_BACK)
    add(FURN, placed(cx, cy, -length / 2 + 1.5, 0.15, 2.8, depth - 1.4, rot, 0.9), Z0, H_ARM)
    add(FURN, placed(cx, cy, length / 2 - 1.5, 0.15, 2.8, depth - 1.4, rot, 0.9), Z0, H_ARM)
    span = length - 6.2
    for i in range(seats):
        dx = -span / 2 + span * (i + 0.5) / seats
        add(FURN, placed(cx, cy, dx, 0.55, span / seats - 0.7, depth - 4.4, rot, 1.2), Z0 + H_SEAT - 1.6, 1.9)
        add(FURN, placed(cx, cy, dx, -1.5, span / seats - 1.4, 3.2, rot, 1.0), Z0 + H_SEAT, 3.6)


def armchair(cx, cy, rot=0.0):
    sofa(cx, cy, 12.2, 11.0, rot, seats=1)


def table_rect(cx, cy, w, d, h=H_TABLE, rot=0.0):
    add(FURN, mm_box(cx, cy, w * 0.58, d * 0.58, rot, r=1.0), Z0, h - H_TOP)
    add(FURN, mm_box(cx, cy, w, d, rot, r=2.0), Z0 + h - H_TOP, H_TOP)


def table_oval(cx, cy, w, d, h=H_TABLE, rot=0.0):
    add(FURN, oval(cx, cy, w * 0.28, d * 0.28, rot), Z0, h - H_TOP)
    add(FURN, oval(cx, cy, w / 2, d / 2, rot), Z0 + h - H_TOP, H_TOP)
    add(FURN, oval(cx, cy, 2.4, 2.4), Z0 + h, 1.1)  # centerpiece


def table_round(cx, cy, radius, h=H_TABLE):
    add(FURN, Point(cx, cy).buffer(radius * 0.42, resolution=22), Z0, h - H_TOP)
    add(FURN, Point(cx, cy).buffer(radius, resolution=32), Z0 + h - H_TOP, H_TOP)
    add(FURN, Point(cx, cy).buffer(2.2, resolution=16), Z0 + h, 1.0)


def coffee(cx, cy, w, d, rot=0.0):
    add(FURN, oval(cx, cy, w * 0.36, d * 0.36, rot), Z0, 4.2)
    add(FURN, oval(cx, cy, w / 2, d / 2, rot), Z0 + 4.2, 1.7)
    add(FURN, oval(cx, cy, w * 0.38, d * 0.38, rot), Z0 + 1.5, 1.2)
    add(FURN, oval(cx, cy, 2.0, 1.4, rot), Z0 + 5.9, 0.8)  # tray


def platform_bed(cx, cy, w, d, rot=0.0, king=False):
    add(FURN, placed(cx, cy, 0, 0, w, d, rot, 1.5), Z0, H_BED)
    add(FURN, placed(cx, cy, 0, 0.5, w - 1.8, d - 2.6, rot, 1.3), Z0 + H_BED - 0.15, H_MATT - H_BED)
    add(FURN, placed(cx, cy, 0, -d / 2 + 1.6, w + 1.2, 3.4, rot, 0.7), Z0, H_HEAD)
    # headboard slats
    n_slat = 5 if king else 4
    span = w - 2.4
    for i in range(n_slat):
        dx = -span / 2 + span * (i + 0.5) / n_slat
        add(FURN, placed(cx, cy, dx, -d / 2 + 1.6, 1.5, 2.4, rot, 0.3), Z0 + 2.0, H_HEAD - 3.2)
    pw = 6.8 if king else 5.6
    py = -d / 2 + 5.4
    if king:
        add(FURN, placed(cx, cy, -(pw / 2 + 0.8), py, pw, 4.8, rot, 1.3), Z0 + H_MATT - 0.15, 2.6)
        add(FURN, placed(cx, cy, pw / 2 + 0.8, py, pw, 4.8, rot, 1.3), Z0 + H_MATT - 0.15, 2.6)
    else:
        add(FURN, placed(cx, cy, 0, py, pw, 4.6, rot, 1.2), Z0 + H_MATT - 0.15, 2.4)
    # folded throw at the foot
    add(FURN, placed(cx, cy, 0, d / 2 - 3.2, w - 2.4, 4.4, rot, 1.0), Z0 + H_MATT - 0.1, 1.8)


def wardrobe(x1, y1, x2, y2, grooves=3):
    g = rb(x1, y1, x2, y2, r=0.5)
    add(FURN, g, Z0, H_WARD)
    ax, ay = P(x1, y1)
    bx, by = P(x2, y2)
    minx, maxx = min(ax, bx), max(ax, bx)
    miny, maxy = min(ay, by), max(ay, by)
    w, d = maxx - minx, maxy - miny
    long_x = w >= d
    for i in range(1, grooves):
        if long_x:
            t = minx + w * i / grooves
            add(FURN, box(t - 0.50, miny + 0.9, t + 0.50, maxy - 0.9), Z0 + 1.4, H_WARD - 2.4)
        else:
            t = miny + d * i / grooves
            add(FURN, box(minx + 0.9, t - 0.50, maxx - 0.9, t + 0.50), Z0 + 1.4, H_WARD - 2.4)
    # handle nubs
    if long_x:
        for i in range(grooves):
            t = minx + w * (i + 0.72) / grooves
            add(FURN, box(t - 0.7, (miny + maxy) / 2 - 1.1, t + 0.7, (miny + maxy) / 2 + 1.1), Z0 + 9.0, 2.4)
    else:
        for i in range(grooves):
            t = miny + d * (i + 0.72) / grooves
            add(FURN, box((minx + maxx) / 2 - 1.1, t - 0.7, (minx + maxx) / 2 + 1.1, t + 0.7), Z0 + 9.0, 2.4)


def nightstand(cx, cy, rot=0.0):
    add(FURN, mm_box(cx, cy, 7.0, 6.0, rot, r=0.9), Z0, 6.4)
    add(FURN, mm_box(cx, cy, 7.4, 6.4, rot, r=0.9), Z0 + 6.4, 1.5)
    add(FURN, mm_box(cx, cy, 6.2, 1.2, rot, r=0.3), Z0 + 3.2, 1.1)  # drawer


def tv_console(cx, cy, w, d, rot=0.0):
    add(FURN, placed(cx, cy, 0, 0, w, d, rot, 1.0), Z0, 6.2)
    add(FURN, placed(cx, cy, 0, 0, w + 0.6, d + 0.3, rot, 1.0), Z0 + 6.2, 1.6)
    add(FURN, placed(cx, cy, 0, 0.15, w * 0.78, 1.7, rot, 0.3), Z0 + 8.0, H_TV - 8.0)
    add(FURN, placed(cx, cy, 0, 0.15, w * 0.55, 1.3, rot, 0.2), Z0 + H_TV - 0.4, 1.1)


def desk(cx, cy, w, d, rot=0.0):
    table_rect(cx, cy, w, d, h=10.8, rot=rot)
    add(FURN, placed(cx, cy, 1.4, 0.2, 5.6, 3.8, rot, 0.5), Z0 + 10.8, 1.0)
    add(FURN, placed(cx, cy, 1.4, -0.6, 5.6, 0.9, rot, 0.2), Z0 + 11.8, 2.4)  # screen


def sideboard(x1, y1, x2, y2):
    add(FURN, rb(x1, y1, x2, y2, r=0.7), Z0, 8.8)
    add(FURN, rb(x1 - 3, y1 - 3, x2 + 3, y2 + 3, r=0.7), Z0 + 8.8, 1.6)
    ax, ay = P(x1, y1)
    bx, by = P(x2, y2)
    miny, maxy = min(ay, by), max(ay, by)
    minx, maxx = min(ax, bx), max(ax, bx)
    for i in range(1, 3):
        t = miny + (maxy - miny) * i / 3
        add(FURN, box(minx + 0.7, t - 0.4, maxx - 0.7, t + 0.4), Z0 + 1.6, 6.6)


def planter(cx, cy, r=4.2):
    add(FURN, Point(cx, cy).buffer(r, resolution=20), Z0, 5.6)
    add(FURN, Point(cx, cy).buffer(r - 1.0, resolution=18), Z0 + 4.6, 2.4)
    add(FURN, Point(cx, cy).buffer(r * 0.45, resolution=12), Z0 + 6.6, 3.2)


def faucet(cx, cy, z0=None, h=4.2):
    if z0 is None:
        z0 = Z0 + H_COUNTER
    add(FIXT, Point(cx, cy).buffer(0.85, resolution=10), z0, h)


def toilet(cx, cy, rot=0.0):
    add(FIXT, placed(cx, cy, 0, 0.8, 6.4, 8.2, rot, 1.8), Z0, H_TOILET)
    add(FIXT, placed(cx, cy, 0, 0.8, 5.6, 7.2, rot, 1.6), Z0 + H_TOILET - 0.2, 1.2)
    add(FIXT, placed(cx, cy, 0, -3.6, 6.8, 3.4, rot, 0.7), Z0, H_TANK)


def kitchen_run():
    # west: sink / cooktop / washer as separate cabinets + one white top
    add(FURN, rb(42, 378, 108, 478, r=0.4), Z0, H_COUNTER - 1.7)
    add(FURN, rb(42, 498, 108, 618, r=0.4), Z0, H_COUNTER - 1.7)
    add(FURN, rb(42, 638, 108, 738, r=0.4), Z0, H_COUNTER - 1.7)
    add(FIXT, rb(40, 376, 110, 740, r=0.5), Z0 + H_COUNTER - 1.7, 1.7)
    add(FIXT, rb(54, 396, 96, 458, r=1.0), Z0 + H_COUNTER - 0.15, 1.5)
    add(FIXT, rb(60, 404, 90, 450, r=0.8), Z0 + H_COUNTER - 1.4, 1.2)
    faucet(*P(75, 400), h=4.6)
    add(FIXT, rb(50, 512, 100, 604, r=0.5), Z0 + H_COUNTER, 1.2)
    for x, y in ((62, 534), (88, 534), (62, 580), (88, 580)):
        add(FIXT, Point(*P(x, y)).buffer(1.75, resolution=14), Z0 + H_COUNTER + 0.5, 0.85)
    # washer door
    add(FURN, rb(52, 660, 98, 716, r=1.4), Z0 + 2.0, 7.2)
    add(FURN, Point(*P(75, 688)).buffer(2.8, resolution=16), Z0 + 4.4, 1.4)
    # fridge on the east, north of the stools (door at y=360 kept clear)
    add(FURN, rb(216, 378, 272, 498, r=0.5), Z0, H_FRIDGE)
    add(FURN, rb(218, 440, 268, 444, r=0.0), Z0 + 10.4, 1.3)
    add(FURN, rb(258, 400, 266, 430, r=0.3), Z0 + 12.0, 3.0)  # handle
    # peninsula + stools
    add(FURN, rb(200, 518, 272, 648, r=0.5), Z0, H_COUNTER - 1.7)
    add(FIXT, rb(198, 516, 274, 650, r=0.5), Z0 + H_COUNTER - 1.7, 1.7)
    stool(*P(236, 545))
    stool(*P(236, 620))
    # upper cabinets
    add(FURN, rb(42, 378, 76, 618, r=0.3), Z0 + 16.0, H_UPPER - 16.0)
    add(FURN, rb(42, 452, 76, 456, r=0.0), Z0 + 16.4, H_UPPER - 17.0)


def wet_rooms():
    # WC — vanity north, toilet south
    add(FURN, rb(214, 688, 274, 742, r=0.6), Z0, 8.6)
    add(FIXT, rb(224, 698, 264, 724, r=1.1), Z0 + 8.6, 2.1)
    faucet(*P(244, 694), z0=Z0 + 8.6 + 2.0, h=3.6)
    toilet(*P(246, 820), rot=0)
    # Banho social: sink | toilet | shower
    add(FURN, rb(590, 130, 662, 246, r=0.5), Z0, 8.8)
    add(FIXT, oval(*P(626, 168), 5.6, 4.2), Z0 + 8.8, 2.1)
    faucet(*P(626, 148), z0=Z0 + 8.8 + 2.0, h=3.8)
    toilet(*P(716, 188), rot=180)
    add(FIXT, rb(768, 128, 856, 250, r=1.0), Z0, H_TRAY)
    add(FIXT, Point(*P(812, 188)).buffer(1.6, resolution=12), Z0 + H_TRAY - 0.4, 0.7)
    add(FURN, rb(766, 126, 786, 252, r=0.25), Z0, 15.2)
    # Banho suíte
    add(FURN, rb(884, 130, 956, 246, r=0.5), Z0, 8.8)
    add(FIXT, oval(*P(920, 168), 5.6, 4.2), Z0 + 8.8, 2.1)
    faucet(*P(920, 148), z0=Z0 + 8.8 + 2.0, h=3.8)
    toilet(*P(1016, 188), rot=180)
    add(FIXT, rb(1076, 128, 1180, 250, r=1.0), Z0, H_TRAY)
    add(FIXT, Point(*P(1128, 188)).buffer(1.6, resolution=12), Z0 + H_TRAY - 0.4, 0.7)
    add(FURN, rb(1074, 126, 1094, 252, r=0.25), Z0, 15.2)


def place_furniture():
    kitchen_run()
    wet_rooms()

    tcx, tcy = P(282, 152)
    table_oval(tcx, tcy, 36.0, 18.0, h=H_TABLE)
    chair(tcx - 8.4, tcy + 12.0, rot=0)
    chair(tcx + 8.4, tcy + 12.0, rot=0)
    chair(tcx - 8.4, tcy - 12.0, rot=180)
    chair(tcx + 8.4, tcy - 12.0, rot=180)
    chair(tcx - 20.4, tcy, rot=90)
    chair(tcx + 20.4, tcy, rot=-90)
    sideboard(118, 52, 174, 312)
    planter(*P(142, 50), r=3.8)

    armchair(*P(338, 422), rot=48)
    armchair(*P(330, 618), rot=132)
    coffee(*P(438, 528), 18.5, 10.2, rot=8)
    sofa(*P(532, 528), 46.0, 13.8, rot=90, seats=3)
    tv_console(*P(348, 528), 16.5, 5.2, rot=90)
    nightstand(*P(548, 692))

    # quarto: pillows toward the varanda (south)
    platform_bed(*P(688, 575), 16.2, 37.0, rot=0, king=False)
    platform_bed(*P(822, 575), 16.2, 37.0, rot=0, king=False)
    nightstand(*P(754, 688))
    wardrobe(622, 376, 872, 432, grooves=3)

    # suíte: headboard / pillows to the east wall
    platform_bed(*P(1070, 545), 30.0, 38.0, rot=90, king=True)
    nightstand(*P(958, 500))
    nightstand(*P(958, 600))
    wardrobe(972, 374, 1180, 428, grooves=4)
    wardrobe(1140, 428, 1186, 545, grooves=3)
    desk(*P(1088, 705), 18.0, 7.6, rot=0)
    tv_console(*P(916, 500), 13.5, 5.0, rot=90)

    vcx, vcy = P(612, 942)
    table_round(vcx, vcy, 10.6, h=11.0)
    chair(vcx, vcy + 14.4, rot=0)
    chair(vcx, vcy - 14.4, rot=180)
    chair(vcx - 14.4, vcy, rot=90)
    chair(vcx + 14.4, vcy, rot=-90)
    add(FURN, rb(336, 788, 404, 870, r=0.6), Z0, 8.6)
    add(FIXT, rb(348, 800, 392, 840, r=1.0), Z0 + 8.6, 1.9)
    faucet(*P(370, 796), z0=Z0 + 8.6 + 1.8, h=3.4)
    planter(*P(748, 905), r=4.2)
    planter(*P(798, 858), r=3.5)


# --- 3MF (Anycubic Slicer Next / Bambu production) ---
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
    maps = " ".join(str(i + 1) for i in range(n))
    model_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">{APP_METADATA}</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">Frontlake</metadata>
 <metadata name="Description">Apartamento 1:50, 4 PLA ACE. Moveis na mesma cor. Kobra X 0.4 mm, sem suporte.</metadata>
 <metadata name="Thumbnail_Middle">/Metadata/plate_1.png</metadata>
 <metadata name="Thumbnail_Small">/Metadata/plate_1_small.png</metadata>
 <resources>
  <object id="{assembly_id}" p:UUID="{assembly_id:08x}-{_OBJ_SUF}" type="model">
   <components>
{chr(10).join(components)}
   </components>
  </object>
 </resources>
 <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">
  <item objectid="{assembly_id}" p:UUID="{assembly_id:08x}-{_ITEM_SUF}" transform="1 0 0 0 1 0 0 0 1 {cx:.4f} {cy:.4f} 0" printable="1"/>
 </build>
</model>
"""
    model_settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="{assembly_id}">
    <metadata key="name" value="Frontlake"/>
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
    filament_override = (
        json.dumps(
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
        )
        + "\n"
    )
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


def overlay(floor, walls, furn, fixt):
    im = Image.open(SRC).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")

    def to_px(mx, my):
        return mx * PX_PER_M / MM_PER_M + OX, OY_SOUTH - my * PX_PER_M / MM_PER_M

    def paint(shape, color, w=2):
        for poly in iter_polygons(shape):
            pts = [to_px(x, y) for x, y in poly.exterior.coords]
            d.line(pts, fill=color, width=w)

    paint(floor, (20, 20, 20, 255), 2)
    paint(walls, (240, 40, 40, 255), 3)
    furn_s = unary_union([p for polys in FURN.values() for p in polys])
    fixt_s = unary_union([p for polys in FIXT.values() for p in polys])
    paint(furn_s, (40, 180, 220, 255), 2)
    paint(fixt_s, (240, 240, 240, 255), 2)
    im.save(OUT_OVERLAY)
    print("overlay", OUT_OVERLAY)


def preview(floor, walls, sills, rail) -> bytes:
    fig, ax = plt.subplots(figsize=(11, 9.2), dpi=130)
    fig.patch.set_facecolor("#5a5a5a")
    ax.set_facecolor("#5a5a5a")

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

    add_s(floor, "#141414", 1)
    add_s(unary_union([p for polys in FIXT.values() for p in polys]), "#f7f7f5", 2)
    add_s(unary_union([p for polys in FURN.values() for p in polys]), "#c5c9ce", 3)
    add_s(walls, "#f5f5f3", 4)
    add_s(sills, "#f5f5f3", 4)
    add_s(rail, "#f5f5f3", 4)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")
    ax.set_title("Frontlake  1:50  ·  preto / branco / prata", color="#ddd", fontsize=12, pad=8)
    fig.tight_layout()
    fig.savefig(OUT_PREVIEW, dpi=130)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return buf.getvalue()


def build():
    print("Frontlake 1:50 from fl.jpg ...")
    walls, sills, doors = building_walls()
    varanda_floor, rail = varanda_shapes()
    floor = footprint(varanda_floor)
    rail = rail.difference(walls.buffer(0.5))
    FURN.clear()
    FIXT.clear()
    place_furniture()
    overlay(floor, walls, FURN, FIXT)
    thumb = preview(floor, walls, sills, rail)

    print("Extruding...")
    floor_m = extrude_shape(floor, FLOOR_H, 0.0)
    wall_m = extrude_shape(walls, WALL_H - FLOOR_H + OVERLAP, FLOOR_H - OVERLAP)
    sill_m = extrude_shape(sills, SILL_H - FLOOR_H + OVERLAP, FLOOR_H - OVERLAP)
    rail_m = extrude_shape(rail, RAIL_H - FLOOR_H + OVERLAP, FLOOR_H - OVERLAP)
    try:
        walls_all = trimesh.boolean.union([wall_m, sill_m, rail_m], engine="manifold")
    except Exception:
        walls_all = trimesh.util.concatenate([wall_m, sill_m, rail_m])
    walls_all.merge_vertices()
    walls_all.update_faces(walls_all.nondegenerate_faces())
    walls_all.remove_unreferenced_vertices()
    furn_m = extrude_bucket(FURN)
    fixt_m = extrude_bucket(FIXT)

    parts = []
    for name, m, col in [
        ("Piso", floor_m, C_FLOOR),
        ("Paredes", walls_all, C_WALL),
        ("Moveis", furn_m, C_FURN),
        ("Bancadas e loucas", fixt_m, C_FIXT),
    ]:
        b = m.bounds
        s = b[1] - b[0]
        print(
            f"  {name:20s} tris={len(m.faces):6d} watertight={m.is_watertight} "
            f"size={s[0]:6.1f} x {s[1]:6.1f} x {s[2]:5.2f} mm"
        )
        if s[0] > BED + 1 or s[1] > BED + 1:
            raise RuntimeError(f"{name} exceeds Kobra X bed")
        parts.append((m, name, col))

    write_3mf(OUT_3MF, parts, thumb)
    print(f"Wrote {OUT_3MF} ({OUT_3MF.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build()
