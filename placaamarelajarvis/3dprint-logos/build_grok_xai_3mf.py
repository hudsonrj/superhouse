#!/usr/bin/env python3
"""Build a dual-logo Grok + xAI 3MF plaque for Anycubic Kobra X.

Printer: Anycubic Kobra X (260 x 260 x 260 mm, 0.4 mm nozzle, ACE 4-color)
Logos: official Grok mark + wordmark (Feb 2025) and xAI geometric monogram.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MplPath
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from svgpathtools import parse_path

ROOT = Path(__file__).resolve().parent
OUT_3MF = ROOT / "Grok_xAI_KobraX.3mf"
OUT_PREVIEW = ROOT / "preview_top.png"
OUT_ISO = ROOT / "preview_iso.png"

# --- Kobra X / FDM constraints ---
BED = 260.0
NOZZLE = 0.4
BASE_H = 3.0
LOGO_H = 0.80
LOGO_OVERLAP = 0.20  # logos sink into the base so ACE parts fuse
MARGIN = 12.0
GAP_MARK_WORD = 7.0
GAP_GROUPS = 18.0
CORNER_R = 7.0
GROK_MARK_H = 40.0
GROK_WORD_H = 18.0
XAI_H = 40.0
MIN_FEATURE = 0.80  # 2 * 0.4 mm nozzle
SIMPLIFY = 0.06

# Brand colors (xAI / Grok: black + white)
COLOR_BASE = (0x11, 0x11, 0x11, 255)
COLOR_GROK = (0xF5, 0xF5, 0xF5, 255)
COLOR_XAI = (0xF5, 0xF5, 0xF5, 255)

# Official Grok mark + wordmark paths (Feb 2025, from grok.com / Wikimedia)
GROK_MARK_PATHS = [
    (
        "M13.2371 21.0407L24.3186 12.8506C24.8619 12.4491 25.6384 12.6057 "
        "25.8973 13.2294C27.2597 16.5185 26.651 20.4712 23.9403 23.1851C21.2297 "
        "25.8989 17.4581 26.4941 14.0108 25.1386L10.2449 26.8843C15.6463 30.5806 "
        "22.2053 29.6665 26.304 25.5601C29.5551 22.3051 30.562 17.8683 29.6205 "
        "13.8673L29.629 13.8758C28.2637 7.99809 29.9647 5.64871 33.449 0.844576"
        "C33.5314 0.730667 33.6139 0.616757 33.6964 0.5L29.1113 5.09055V5.07631"
        "L13.2343 21.0436"
    ),
    (
        "M10.9503 23.0313C7.07343 19.3235 7.74185 13.5853 11.0498 10.2763C13.4959 "
        "7.82722 17.5036 6.82767 21.0021 8.2971L24.7595 6.55998C24.0826 6.07017 "
        "23.215 5.54334 22.2195 5.17313C17.7198 3.31926 12.3326 4.24192 8.67479 "
        "7.90126C5.15635 11.4239 4.0499 16.8403 5.94992 21.4622C7.36924 24.9165 "
        "5.04257 27.3598 2.69884 29.826C1.86829 30.7002 1.0349 31.5745 0.36364 "
        "32.5L10.9474 23.0341"
    ),
]

GROK_WORD_PATHS = [
    # G
    (
        "M45.7187 25.009C40.8101 25.009 37.8834 21.4448 37.8834 16.5846C37.8834 "
        "11.6788 40.9146 8.02795 45.8145 8.02795C49.6433 8.02795 52.4466 9.99027 "
        "53.1075 13.6411H50.1675C49.7345 11.5647 48.0024 10.401 45.8145 10.401"
        "C42.282 10.401 40.7322 13.4586 40.7322 16.5846C40.7322 19.7106 42.282 "
        "22.7454 45.8145 22.7454C49.1875 22.7454 50.6689 20.3039 50.7828 18.2731"
        "H45.7006V15.9105H53.381L53.3684 17.1457C53.3684 21.7359 51.4978 25.009 "
        "45.7187 25.009Z"
    ),
    # r
    "M55.5659 24.7077V14.782L57.731 12.9109H62.3347V15.1014H58.1413V24.7077H55.5659Z",
    # o (outer + inner)
    (
        "M68.6362 24.9815C64.8074 24.9815 62.7335 22.2662 62.7335 18.7979C62.7335 "
        "15.3068 64.8074 12.6143 68.6362 12.6143C72.4878 12.6143 74.5389 15.3068 "
        "74.5389 18.7979C74.5389 22.2662 72.4878 24.9815 68.6362 24.9815ZM65.4228 "
        "18.7979C65.4228 21.4904 66.8813 22.8366 68.6362 22.8366C70.4139 22.8366 "
        "71.8497 21.4904 71.8497 18.7979C71.8497 16.1054 70.4139 14.7363 68.6362 "
        "14.7363C66.8813 14.7363 65.4228 16.1054 65.4228 18.7979Z"
    ),
    # k
    (
        "M76.4462 24.7077V8.41584H79.0216V19.1679L84.4685 12.9109H87.5908L82.6908 "
        "18.2731L87.6364 24.7077H84.5596L80.5539 19.1788L79.0216 19.1679V24.7077"
        "H76.4462Z"
    ),
]

# Official xAI geometric monogram (x.ai, Wikimedia File:XAI-Logo.svg)
XAI_POLYGONS = [
    [(0.12, 182.71), (234.14, 516.92), (338.15, 516.92), (104.13, 182.71)],
    [(0.0, 516.92), (104.08, 516.92), (156.08, 442.67), (104.04, 368.34)],
    [(466.04, 0.0), (361.96, 0.0), (182.1, 256.86), (234.15, 331.18)],
    [(380.78, 516.92), (466.04, 516.92), (466.04, 37.16), (380.78, 158.92)],
]


def sample_subpath(sub, samples_per_unit: float = 14.0) -> np.ndarray:
    length = float(sub.length())
    n = max(32, int(length * samples_per_unit) + 1)
    ts = np.linspace(0.0, 1.0, n, endpoint=False)
    pts = np.array([[sub.point(t).real, sub.point(t).imag] for t in ts], dtype=float)
    if np.linalg.norm(pts[0] - pts[-1]) > 1e-6:
        pts = np.vstack([pts, pts[0]])
    return pts


def rings_from_d(d: str) -> list[np.ndarray]:
    path = parse_path(d)
    subs = path.continuous_subpaths() if hasattr(path, "continuous_subpaths") else [path]
    rings = []
    for sub in subs:
        if sub.length() < 1e-6:
            continue
        rings.append(sample_subpath(sub))
    return rings


def evenodd_from_rings(rings: list[np.ndarray]) -> Polygon | MultiPolygon | None:
    polys: list[Polygon] = []
    for ring in rings:
        if len(ring) < 4:
            continue
        p = Polygon(ring)
        if not p.is_valid:
            p = p.buffer(0)
        if p.is_empty:
            continue
        polys.append(p)
    if not polys:
        return None
    result = polys[0]
    for p in polys[1:]:
        result = result.symmetric_difference(p)
    if result.is_empty:
        return None
    return result


def svg_paths_to_shape(ds: list[str]) -> Polygon | MultiPolygon:
    parts = []
    for d in ds:
        geom = evenodd_from_rings(rings_from_d(d))
        if geom is not None:
            parts.append(geom)
    if not parts:
        raise RuntimeError("no geometry from SVG paths")
    return unary_union(parts)


def polygons_to_shape(polys: list[list[tuple[float, float]]]) -> Polygon | MultiPolygon:
    return unary_union([Polygon(pts).buffer(0) for pts in polys])


def flip_y(shape):
    return shapely_scale(shape, 1.0, -1.0)


def shapely_scale(shape, sx: float, sy: float):
    from shapely.affinity import scale

    return scale(shape, xfact=sx, yfact=sy, origin=(0.0, 0.0))


def shapely_translate(shape, x: float, y: float):
    from shapely.affinity import translate

    return translate(shape, xoff=x, yoff=y)


def normalize_origin(shape):
    minx, miny, _, _ = shape.bounds
    return shapely_translate(shape, -minx, -miny)


def fit_height(shape, height: float):
    minx, miny, maxx, maxy = shape.bounds
    h = maxy - miny
    if h <= 0:
        raise RuntimeError("empty bounds")
    s = height / h
    return shapely_scale(shape, s, s)


def rounded_rect_buf(w: float, h: float, r: float) -> Polygon:
    from shapely.geometry import box

    r = min(r, w / 2.0 - 0.2, h / 2.0 - 0.2)
    return box(r, r, w - r, h - r).buffer(r, resolution=16)


def iter_polygons(shape):
    if shape.is_empty:
        return
    if shape.geom_type == "Polygon":
        yield shape
    elif shape.geom_type == "MultiPolygon":
        for g in shape.geoms:
            yield g
    else:
        for g in getattr(shape, "geoms", []):
            if g.geom_type in ("Polygon", "MultiPolygon"):
                yield from iter_polygons(g)


def clean_polygon(poly: Polygon, min_area: float = 0.08) -> Polygon | None:
    if poly.is_empty:
        return None
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        return None
    if poly.geom_type == "MultiPolygon":
        parts = [clean_polygon(g, min_area) for g in poly.geoms]
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        return unary_union(parts)
    if poly.area < min_area:
        return None
    holes = []
    for interior in poly.interiors:
        hp = Polygon(interior)
        if hp.area >= min_area:
            holes.append(interior)
    poly = Polygon(poly.exterior, holes)
    poly = poly.simplify(SIMPLIFY, preserve_topology=True)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly if poly and not poly.is_empty and poly.area >= min_area else None


def thicken_if_needed(shape, min_width: float = MIN_FEATURE):
    """Slightly thicken needle-thin tips without ballooning the logo."""
    # Hydraulic-radius heuristic: 2*area/perimeter ~ min width for ribbons.
    for poly in list(iter_polygons(shape)):
        if poly.area <= 0:
            continue
        hr = 2.0 * poly.area / max(poly.length, 1e-6)
        if hr < min_width * 0.55:
            return shape.buffer(0.12, join_style=1).buffer(-0.06, join_style=1)
    return shape


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
            # Fallback: drop holes if triangulation fails
            simple = Polygon(poly.exterior)
            simple = simple.buffer(0)
            if simple.is_empty or simple.area < 0.08:
                continue
            if simple.geom_type != "Polygon":
                meshes.append(extrude_shape(simple, height, z0))
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


def mesh_stats(m: trimesh.Trimesh, name: str) -> None:
    watertight = bool(m.is_watertight)
    vol = float(m.volume) if watertight else float("nan")
    b = m.bounds
    size = b[1] - b[0]
    print(
        f"  {name:12s}  tris={len(m.faces):6d}  watertight={watertight}  "
        f"vol={vol:8.1f} mm3  size={size[0]:6.2f} x {size[1]:6.2f} x {size[2]:5.2f} mm"
    )
    if size[0] > BED or size[1] > BED or size[2] > BED:
        raise RuntimeError(f"{name} exceeds Kobra X bed {BED} mm")


def rgba_hex(rgba) -> str:
    r, g, b, a = rgba
    return f"#{r:02X}{g:02X}{b:02X}{a:02X}"


def mesh_to_3mf_object(mesh: trimesh.Trimesh, obj_id: int, name: str, pid: int, pindex: int) -> str:
    v = mesh.vertices
    f = mesh.faces
    lines = [
        f'    <object id="{obj_id}" name="{escape(name)}" type="model" pid="{pid}" pindex="{pindex}">',
        "      <mesh>",
        "        <vertices>",
    ]
    for x, y, z in v:
        lines.append(f'          <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>')
    lines.append("        </vertices>")
    lines.append("        <triangles>")
    for a, b, c in f:
        lines.append(
            f'          <triangle v1="{int(a)}" v2="{int(b)}" v3="{int(c)}" pid="{pid}" p1="{pindex}"/>'
        )
    lines.append("        </triangles>")
    lines.append("      </mesh>")
    lines.append("    </object>")
    return "\n".join(lines)


def identity_transform(tx=0.0, ty=0.0, tz=0.0) -> str:
    return f"1 0 0 0 1 0 0 0 1 {tx:.4f} {ty:.4f} {tz:.4f}"


def write_3mf(
    path: Path,
    parts: list[tuple[trimesh.Trimesh, str, tuple[int, int, int, int]]],
    thumbnail: bytes,
    plate_w: float,
    plate_h: float,
) -> None:
    """Write a 3MF with materials + Orca/Anycubic-style assembly metadata."""
    pid_materials = 10
    assembly_id = 1
    first_mesh_id = 2

    objects_xml = []
    components_xml = []
    parts_meta = []
    for i, (mesh, name, color) in enumerate(parts):
        oid = first_mesh_id + i
        objects_xml.append(mesh_to_3mf_object(mesh, oid, name, pid_materials, i))
        components_xml.append(
            f'        <component objectid="{oid}" transform="{identity_transform()}"/>'
        )
        parts_meta.append(
            f"""    <part id="{oid}" subtype="normal_part">
      <metadata key="name" value="{escape(name)}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value=""/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="{i}"/>
      <metadata key="extruder" value="{i + 1}"/>
    </part>"""
        )

    materials = "\n".join(
        f'      <m:base name="{escape(name)}" displaycolor="{rgba_hex(color)}"/>'
        for _, name, color in parts
    )

    model_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US"
  xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
  xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">
  <metadata name="Title">Grok + xAI Logos</metadata>
  <metadata name="Designer">placamarela</metadata>
  <metadata name="Description">Dual-logo plaque for Anycubic Kobra X (260x260x260 mm, 0.4 mm nozzle)</metadata>
  <metadata name="Application">Grok 3MF Builder</metadata>
  <metadata name="License">Personal fan print. Grok and xAI are trademarks of xAI / SpaceXAI.</metadata>
  <resources>
    <m:basematerials id="{pid_materials}">
{materials}
    </m:basematerials>
    <object id="{assembly_id}" name="Grok xAI Plaque" type="model">
      <components>
{chr(10).join(components_xml)}
      </components>
    </object>
{chr(10).join(objects_xml)}
  </resources>
  <build>
    <item objectid="{assembly_id}" transform="{identity_transform()}"/>
  </build>
</model>
"""

    # Center on the 260 mm Kobra X bed (origin = front-left).
    cx = (BED - plate_w) / 2.0
    cy = (BED - plate_h) / 2.0
    model_settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="{assembly_id}">
    <metadata key="name" value="Grok xAI Plaque"/>
    <metadata key="extruder" value="1"/>
{chr(10).join(parts_meta)}
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value="Kobra X"/>
    <metadata key="locked" value="false"/>
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
  <Default Extension="config" ContentType="application/octet-stream"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
  <Relationship Target="/Metadata/thumbnail.png" Id="rel1" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>
</Relationships>
"""
    model_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/Metadata/thumbnail.png" Id="rel1" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/>
</Relationships>
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model_xml)
        z.writestr("3D/_rels/3dmodel.model.rels", model_rels)
        z.writestr("Metadata/thumbnail.png", thumbnail)
        z.writestr("Metadata/model_settings.config", model_settings)


def add_shape_to_ax(ax, shape, facecolor, edgecolor=None, lw=0.0, zorder=1):
    for poly in iter_polygons(shape):
        verts = []
        codes = []
        ext = np.asarray(poly.exterior.coords)
        verts.extend(ext)
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(ext) - 2) + [MplPath.CLOSEPOLY])
        for interior in poly.interiors:
            hole = np.asarray(interior.coords)
            verts.extend(hole)
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 2) + [MplPath.CLOSEPOLY])
        path = MplPath(verts, codes)
        ax.add_patch(
            PathPatch(
                path,
                facecolor=facecolor,
                edgecolor=edgecolor or facecolor,
                lw=lw,
                zorder=zorder,
            )
        )


def render_preview(plate, grok, xai, w, h) -> bytes:
    fig, ax = plt.subplots(figsize=(10.4, 4.2), dpi=160)
    fig.patch.set_facecolor("#2a2a2a")
    ax.set_facecolor("#2a2a2a")
    add_shape_to_ax(ax, plate, "#111111", zorder=1)
    add_shape_to_ax(ax, grok, "#F5F5F5", zorder=2)
    add_shape_to_ax(ax, xai, "#F5F5F5", zorder=2)
    ax.set_xlim(-4, w + 4)
    ax.set_ylim(-4, h + 4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Grok + xAI  ·  placa para Anycubic Kobra X",
        color="#dddddd",
        fontsize=12,
        pad=10,
        fontfamily="DejaVu Sans",
    )
    fig.tight_layout(pad=0.4)
    fig.savefig(OUT_PREVIEW, dpi=160)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    return buf.getvalue()


def _oblique(x, y, z, sx=0.42, sy=0.28):
    return x + z * sx, y + z * sy


def _draw_extrusion(ax, shape, z0, z1, top, side, zorder):
    """Cheap 2.5D extrusion so the 0.8 mm logo relief is visible."""
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
        # Top face, remapped into oblique coordinates.
        verts = []
        codes = []
        ext = np.asarray(poly.exterior.coords)
        ox, oy = _oblique(ext[:, 0], ext[:, 1], z1)
        verts.extend(np.column_stack([ox, oy]))
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(ext) - 2) + [MplPath.CLOSEPOLY])
        for interior in poly.interiors:
            hole = np.asarray(interior.coords)
            hx, hy = _oblique(hole[:, 0], hole[:, 1], z1)
            verts.extend(np.column_stack([hx, hy]))
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(hole) - 2) + [MplPath.CLOSEPOLY])
        ax.add_patch(
            PathPatch(
                MplPath(verts, codes),
                facecolor=top,
                edgecolor=top,
                lw=0.0,
                zorder=zorder + 1,
            )
        )


def render_iso(plate, grok, xai, w, h, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11.2, 5.4), dpi=150)
    fig.patch.set_facecolor("#3a3a3a")
    ax.set_facecolor("#3a3a3a")
    _draw_extrusion(ax, plate, 0.0, BASE_H, "#1a1a1a", "#0a0a0a", zorder=1)
    _draw_extrusion(ax, grok, BASE_H - LOGO_OVERLAP, BASE_H + LOGO_H, "#f4f4f4", "#c8c8c8", zorder=5)
    _draw_extrusion(ax, xai, BASE_H - LOGO_OVERLAP, BASE_H + LOGO_H, "#f4f4f4", "#c8c8c8", zorder=5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Relevo 0,8 mm  ·  base 3,0 mm  ·  Kobra X 260 mm",
        color="#dddddd",
        fontsize=11,
        pad=8,
    )
    fig.tight_layout(pad=0.5)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build():
    print("Parsing official logo vectors...")
    grok_mark = normalize_origin(flip_y(svg_paths_to_shape(GROK_MARK_PATHS)))
    grok_word = normalize_origin(flip_y(svg_paths_to_shape(GROK_WORD_PATHS)))
    xai = normalize_origin(flip_y(polygons_to_shape(XAI_POLYGONS)))

    grok_mark = thicken_if_needed(fit_height(grok_mark, GROK_MARK_H))
    grok_word = thicken_if_needed(fit_height(grok_word, GROK_WORD_H))
    xai = thicken_if_needed(fit_height(xai, XAI_H))

    gm = grok_mark.bounds
    gw = grok_word.bounds
    xb = xai.bounds
    gm_w, gm_h = gm[2] - gm[0], gm[3] - gm[1]
    gw_w, gw_h = gw[2] - gw[0], gw[3] - gw[1]
    xa_w, xa_h = xb[2] - xb[0], xb[3] - xb[1]

    content_h = max(gm_h, gw_h, xa_h)
    plate_h = content_h + 2 * MARGIN
    # Horizontal pack: [mark] [word] .... [xAI]
    x = MARGIN
    y_mark = MARGIN + (content_h - gm_h) / 2.0
    grok_mark = shapely_translate(grok_mark, x - gm[0], y_mark - gm[1])
    x += gm_w + GAP_MARK_WORD
    y_word = MARGIN + (content_h - gw_h) / 2.0
    grok_word = shapely_translate(grok_word, x - gw[0], y_word - gw[1])
    x += gw_w + GAP_GROUPS
    y_xai = MARGIN + (content_h - xa_h) / 2.0
    xai = shapely_translate(xai, x - xb[0], y_xai - xb[1])
    x += xa_w + MARGIN
    plate_w = x

    plate = rounded_rect_buf(plate_w, plate_h, CORNER_R)
    grok = unary_union([grok_mark, grok_word])

    print(f"Plate {plate_w:.2f} x {plate_h:.2f} x {BASE_H + LOGO_H - LOGO_OVERLAP:.2f} mm")
    print("Extruding...")
    base_mesh = extrude_shape(plate, BASE_H, 0.0)
    grok_mesh = extrude_shape(grok, LOGO_H + LOGO_OVERLAP, BASE_H - LOGO_OVERLAP)
    xai_mesh = extrude_shape(xai, LOGO_H + LOGO_OVERLAP, BASE_H - LOGO_OVERLAP)

    print("Mesh stats:")
    mesh_stats(base_mesh, "Base")
    mesh_stats(grok_mesh, "Grok")
    mesh_stats(xai_mesh, "xAI")

    parts = [
        (base_mesh, "Base (preto)", COLOR_BASE),
        (grok_mesh, "Logo Grok", COLOR_GROK),
        (xai_mesh, "Logo xAI", COLOR_XAI),
    ]

    print("Rendering preview...")
    thumb = render_preview(plate, grok, xai, plate_w, plate_h)
    render_iso(plate, grok, xai, plate_w, plate_h, OUT_ISO)

    print("Writing 3MF...")
    write_3mf(OUT_3MF, parts, thumb, plate_w, plate_h)
    print(f"Wrote {OUT_3MF}  ({OUT_3MF.stat().st_size / 1024:.1f} KB)")
    print(f"Preview: {OUT_PREVIEW}")
    print(f"Iso:     {OUT_ISO}")
    print("Done.")


if __name__ == "__main__":
    build()
