#!/usr/bin/env python3
"""Small 1:100 apartment floor-plan 3MF for Anycubic Kobra X.

Rooms and walls only — no furniture. Traced from fl.jpg using the
metre callouts on the plan (cozinha, sala, quarto, suíte, banheiros, varanda).
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "fl.jpg"
OUT_3MF = ROOT / "Planta_Apartamento_KobraX.3mf"
OUT_OVERLAY = ROOT / "planta_overlay.png"
OUT_PREVIEW = ROOT / "planta_preview.png"

# Image calibration: quarto 2.80 m spans ~295 px → 105 px/m
PX_PER_M = 105.0
OX, OY_SOUTH = 28.0, 879.0  # kitchen SW in image pixels
SCALE = 1.0 / 100.0  # 1:100 → 1 m = 10 mm
MM_PER_M = 1000.0 * SCALE  # 10 mm per metre

BED = 260.0
WALL_T = 1.50  # mm (~15 cm real)
WALL_H = 12.0  # mm, readable rooms, still a small print
FLOOR_H = 1.60
OVERLAP = 0.20
SILL_H = 3.60  # window parapet
RAIL_H = 3.60  # varanda railing
LABEL_H = 0.60
LABEL_SIZE = 3.4  # mm
DOOR_CUT = 2.2  # mm, wider than wall so openings are clean

COLOR_FLOOR = (0xF2, 0xEB, 0xD8, 255)
COLOR_WALLS = (0x2A, 0x2A, 0x2A, 255)


def P(x: float, y: float) -> tuple[float, float]:
    """Image pixel (Y down) → model mm (origin kitchen SW, Y north)."""
    return ((x - OX) * MM_PER_M / PX_PER_M, (OY_SOUTH - y) * MM_PER_M / PX_PER_M)


def wall_line(a, b, t: float = WALL_T) -> Polygon:
    return LineString([P(*a), P(*b)]).buffer(t / 2.0, cap_style=2, join_style=2)


def door_cut(a, b) -> Polygon:
    """Rectangle across a wall segment, slightly longer than the opening."""
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


def clean_polygon(poly: Polygon, min_area: float = 0.15) -> Polygon | None:
    if poly is None or poly.is_empty:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        parts = [clean_polygon(g, min_area) for g in poly.geoms]
        parts = [p for p in parts if p is not None]
        return unary_union(parts) if parts else None
    if poly.area < min_area:
        return None
    holes = [h for h in poly.interiors if Polygon(h).area >= min_area]
    poly = Polygon(poly.exterior, holes).simplify(0.08, preserve_topology=True)
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


def text_poly(msg: str, cx: float, cy: float, size: float = LABEL_SIZE) -> Polygon | MultiPolygon:
    fp = FontProperties(family="DejaVu Sans", weight="bold")
    path = TextPath((0, 0), msg, size=size, prop=fp)
    polys = []
    for ring in path.to_polygons():
        if len(ring) < 4:
            continue
        p = Polygon(ring)
        if not p.is_valid:
            p = p.buffer(0)
        if not p.is_empty and p.area > 0.02:
            polys.append(p)
    if not polys:
        raise RuntimeError(f"no text geometry for {msg!r}")
    g = unary_union(polys)
    minx, miny, maxx, maxy = g.bounds
    dx = cx - 0.5 * (minx + maxx)
    dy = cy - 0.5 * (miny + maxy)
    from shapely.affinity import translate

    return translate(g, xoff=dx, yoff=dy)


def mesh_to_3mf_object(mesh, obj_id, name, pid, pindex) -> str:
    lines = [
        f'    <object id="{obj_id}" name="{escape(name)}" type="model" pid="{pid}" pindex="{pindex}">',
        "      <mesh>",
        "        <vertices>",
    ]
    for x, y, z in mesh.vertices:
        lines.append(f'          <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>')
    lines.append("        </vertices>")
    lines.append("        <triangles>")
    for a, b, c in mesh.faces:
        lines.append(
            f'          <triangle v1="{int(a)}" v2="{int(b)}" v3="{int(c)}" pid="{pid}" p1="{pindex}"/>'
        )
    lines.append("        </triangles>")
    lines.append("      </mesh>")
    lines.append("    </object>")
    return "\n".join(lines)


def write_3mf(path: Path, parts, thumbnail: bytes) -> None:
    pid, assembly_id, first = 10, 1, 2
    objects_xml, components_xml, parts_meta = [], [], []
    for i, (mesh, name, color) in enumerate(parts):
        oid = first + i
        objects_xml.append(mesh_to_3mf_object(mesh, oid, name, pid, i))
        components_xml.append(
            f'        <component objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
        )
        parts_meta.append(
            f"""    <part id="{oid}" subtype="normal_part">
      <metadata key="name" value="{escape(name)}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="extruder" value="{i + 1}"/>
    </part>"""
        )
    materials = "\n".join(
        f'      <m:base name="{escape(n)}" displaycolor="#{c[0]:02X}{c[1]:02X}{c[2]:02X}{c[3]:02X}"/>'
        for _, n, c in parts
    )
    bw = max(p[0].extents[0] for p in parts)
    bh = max(p[0].extents[1] for p in parts)
    cx, cy = (BED - bw) / 2.0, (BED - bh) / 2.0
    model_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="pt-BR"
  xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
  xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">
  <metadata name="Title">Planta apartamento 1:100</metadata>
  <metadata name="Description">Cômodos e paredes a partir de fl.jpg. Sem mobília. Kobra X.</metadata>
  <metadata name="Application">Grok 3MF Builder</metadata>
  <resources>
    <m:basematerials id="{pid}">
{materials}
    </m:basematerials>
    <object id="{assembly_id}" name="Planta apartamento" type="model">
      <components>
{chr(10).join(components_xml)}
      </components>
    </object>
{chr(10).join(objects_xml)}
  </resources>
  <build>
    <item objectid="{assembly_id}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
  </build>
</model>
"""
    model_settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="{assembly_id}">
    <metadata key="name" value="Planta apartamento 1:100"/>
    <metadata key="extruder" value="1"/>
{chr(10).join(parts_meta)}
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value="Kobra X"/>
    <model_instance>
      <metadata key="object_id" value="{assembly_id}"/>
      <metadata key="instance_id" value="0"/>
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
  <Default Extension="config" ContentType="application/octet-stream"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
  <Relationship Target="/Metadata/thumbnail.png" Id="rel1" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>
</Relationships>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model_xml)
        z.writestr("Metadata/thumbnail.png", thumbnail)
        z.writestr("Metadata/model_settings.config", model_settings)


def building_walls() -> tuple[Polygon, Polygon, Polygon]:
    """Return (full walls, window sills, door cuts) in model mm."""
    # Pixel coords traced from fl.jpg (structural black walls + metre callouts).
    segs = [
        # Cozinha / WC
        ((32, 360), (32, 879)),          # west
        ((32, 879), (206, 879)),         # kitchen south
        ((206, 879), (281, 879)),        # WC south
        ((32, 360), (122, 360)),         # kitchen north (left of door)
        ((216, 360), (281, 360)),        # kitchen north (right of door)
        ((281, 360), (281, 733)),        # kitchen / sala
        ((281, 733), (281, 879)),        # WC east / tanque west
        ((206, 675), (281, 675)),        # WC north
        ((206, 675), (206, 786)),        # WC west (above door)
        ((206, 857), (206, 879)),        # WC west (below door)
        # Tanque
        ((281, 733), (330, 733)),
        ((330, 733), (330, 780)),        # tanque east (door to varanda below)
        ((330, 850), (330, 879)),
        ((281, 879), (330, 879)),
        # Sala / jantar
        ((107, 33), (461, 33)),          # dining north
        ((107, 33), (107, 360)),         # dining west
        ((461, 33), (461, 114)),         # dining NE jog
        ((461, 114), (575, 114)),        # sala north (setback)
        # Banheiros + bloco leste
        ((575, 114), (1192, 114)),       # north
        ((1192, 114), (1192, 737)),      # east
        ((575, 114), (575, 260)),        # banho west
        ((868, 114), (868, 260)),        # parede banho / banho suíte
        # Banho south (doors cut later)
        ((575, 260), (603, 260)),
        ((674, 260), (930, 260)),
        ((1000, 260), (1192, 260)),
        # Quarto
        ((590, 368), (590, 737)),        # west (sala / quarto)
        ((685, 368), (890, 368)),        # north (east of door)
        ((890, 368), (890, 737)),        # quarto / suíte
        # Fachada sul — trechos de parede (janelas viram peitoril)
        ((590, 737), (604, 737)),
        ((754, 737), (902, 737)),
        ((1054, 737), (1192, 737)),
        ((330, 737), (334, 737)),        # tanque NE corner
    ]
    walls = unary_union([wall_line(a, b) for a, b in segs])

    doors = unary_union(
        [
            door_cut((122, 360), (216, 360)),     # cozinha
            door_cut((206, 786), (206, 857)),     # WC
            door_cut((603, 260), (674, 260)),     # banho
            door_cut((930, 260), (1000, 260)),    # banho suíte
            door_cut((590, 368), (685, 368)),     # quarto (pelo circ.)
            door_cut((334, 737), (576, 737)),     # sala → varanda (correr)
            door_cut((330, 780), (330, 850)),     # tanque → varanda
        ]
    )
    walls = walls.difference(doors)

    sills = unary_union(
        [
            wall_line((604, 737), (754, 737)),    # janela quarto
            wall_line((902, 737), (1054, 737)),   # janela suíte
        ]
    )
    return walls, sills, doors


def varanda_shapes() -> tuple[Polygon, Polygon]:
    """Varanda floor + outer railing from the beige terrace edge."""
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
    rail_px = curve_px[:-1]  # skip closing along the facade
    rail = LineString([P(x, y) for x, y in rail_px]).buffer(WALL_T / 2.0, cap_style=2, join_style=1)
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
    return unary_union(parts).buffer(0.2).buffer(-0.2)


def labels() -> Polygon | MultiPolygon:
    # Pixel centres of each room, converted to mm.
    items = [
        ("COZINHA", 155, 530, 3.4),
        ("WC", 245, 790, 2.8),
        ("SALA", 400, 480, 3.6),
        ("VARANDA", 580, 900, 3.4),
        ("QUARTO", 740, 540, 3.4),
        ("SUITE", 1040, 540, 3.4),
        ("BANHO", 720, 185, 2.6),
        ("B.SUITE", 1045, 185, 2.6),
        ("CIRC", 720, 315, 2.6),
    ]
    bits = []
    for t, x, y, sz in items:
        g = text_poly(t, *P(x, y), size=sz)
        g = g.buffer(0.16, join_style=1).buffer(-0.02)
        bits.append(g)
    return unary_union(bits)


def save_overlay(walls, sills, doors, floor, labels_g) -> None:
    im = Image.open(SRC).convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")

    def to_px(mx, my):
        x = mx * PX_PER_M / MM_PER_M + OX
        y = OY_SOUTH - my * PX_PER_M / MM_PER_M
        return x, y

    def draw_shape(shape, fill, outline=None, width=1):
        for poly in iter_polygons(shape):
            pts = [to_px(x, y) for x, y in poly.exterior.coords]
            d.line(pts, fill=outline or fill, width=width)
            for hole in poly.interiors:
                d.line([to_px(x, y) for x, y in hole.coords], fill=outline or fill, width=width)

    draw_shape(floor, (40, 140, 255, 80), (30, 90, 200, 255), 2)
    draw_shape(walls, (220, 30, 30, 255), (220, 30, 30, 255), 3)
    draw_shape(sills, (40, 180, 70, 255), (40, 180, 70, 255), 3)
    draw_shape(doors, (255, 180, 0, 255), (255, 160, 0, 255), 2)
    draw_shape(labels_g, (80, 0, 120, 255), (80, 0, 120, 255), 1)
    im.save(OUT_OVERLAY)
    print(f"overlay {OUT_OVERLAY}")


def preview_png(floor, walls, sills, rail, labels_g) -> bytes:
    fig, ax = plt.subplots(figsize=(10.5, 9.0), dpi=140)
    fig.patch.set_facecolor("#3d3d3d")
    ax.set_facecolor("#3d3d3d")

    def add(shape, color, z=1):
        from matplotlib.patches import PathPatch
        from matplotlib.path import Path as MplPath

        for poly in iter_polygons(shape):
            verts, codes = [], []
            ext = np.asarray(poly.exterior.coords)
            verts.extend(ext)
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(ext) - 2) + [MplPath.CLOSEPOLY])
            for interior in poly.interiors:
                hole = np.asarray(interior.coords)
                verts.extend(hole)
                codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 2) + [MplPath.CLOSEPOLY])
            ax.add_patch(PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", zorder=z))

    add(floor, "#e8dcc3", 1)
    add(walls, "#2a2a2a", 3)
    add(sills, "#2a2a2a", 3)
    add(rail, "#2a2a2a", 3)
    add(labels_g, "#2a2a2a", 4)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")
    ax.set_title("Planta 1:100  ·  Kobra X  ·  só cômodos", color="#ddd", fontsize=12, pad=8)
    fig.tight_layout()
    fig.savefig(OUT_PREVIEW, dpi=140)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return buf.getvalue()


def build():
    print("Building apartment plan at 1:100 from fl.jpg ...")
    walls, sills, doors = building_walls()
    varanda_floor, rail = varanda_shapes()
    floor = footprint(varanda_floor)
    # railing only outside the building walls
    rail = rail.difference(walls.buffer(0.4))
    lab = labels()
    # keep labels inside rooms, not on walls
    lab = lab.difference(walls.buffer(0.15))

    save_overlay(walls, sills, doors, floor, lab)

    print("Extruding...")
    floor_m = extrude_shape(floor, FLOOR_H, 0.0)
    wall_m = extrude_shape(walls, WALL_H - FLOOR_H + OVERLAP, FLOOR_H - OVERLAP)
    sill_m = extrude_shape(sills, SILL_H - FLOOR_H + OVERLAP, FLOOR_H - OVERLAP)
    rail_m = extrude_shape(rail, RAIL_H - FLOOR_H + OVERLAP, FLOOR_H - OVERLAP)
    lab_m = extrude_shape(lab, LABEL_H + OVERLAP, FLOOR_H - OVERLAP)

    try:
        walls_all = trimesh.boolean.union([wall_m, sill_m, rail_m, lab_m], engine="manifold")
    except Exception:
        walls_all = trimesh.util.concatenate([wall_m, sill_m, rail_m, lab_m])
    walls_all.merge_vertices()
    walls_all.update_faces(walls_all.nondegenerate_faces())
    walls_all.remove_unreferenced_vertices()
    walls_all.fix_normals()

    for name, m in [("Piso", floor_m), ("Paredes", walls_all)]:
        b = m.bounds
        s = b[1] - b[0]
        print(
            f"  {name:8s} tris={len(m.faces):5d} watertight={m.is_watertight} "
            f"size={s[0]:6.1f} x {s[1]:6.1f} x {s[2]:5.2f} mm"
        )
        if s[0] > BED or s[1] > BED:
            raise RuntimeError("model larger than Kobra X bed")

    thumb = preview_png(floor, walls, sills, rail, lab)
    parts = [
        (floor_m, "Piso", COLOR_FLOOR),
        (walls_all, "Paredes e nomes", COLOR_WALLS),
    ]
    write_3mf(OUT_3MF, parts, thumb)
    print(f"Wrote {OUT_3MF} ({OUT_3MF.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build()
