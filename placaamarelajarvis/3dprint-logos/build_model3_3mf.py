#!/usr/bin/env python3
"""Tesla Model 3 desk model — Anycubic Kobra X, PLA prata.

Pre-Highland Performance look: fastback sedan, C-headlights, aero wheels,
red calipers. ~115 mm, sits on the wheels, no supports.
"""

from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib.pyplot as plt
import numpy as np
import trimesh
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
OUT_3MF = ROOT / "Model3_KobraX.3mf"
OUT_PREVIEW = ROOT / "model3_preview.png"
OUT_OVERLAY = ROOT / "model3_overlay.png"
SIDE_SRC = ROOT / "src" / "m3_side.jpg"

BED = 260.0

# 2019-2023 Model 3
REAL_L, REAL_W, REAL_H = 4694.0, 1850.0, 1443.0
REAL_WB, REAL_OH_F, REAL_OH_R = 2875.0, 860.0, 959.0
REAL_TIRE = 18 * 25.4 + 2 * 235 * 0.45  # 235/45R18

L = 115.0
S = L / REAL_L
W = REAL_W * S
H = REAL_H * S
WB = REAL_WB * S
OH_F = REAL_OH_F * S
OH_R = REAL_OH_R * S
R_TIRE = REAL_TIRE * S / 2.0

C_SILVER = (0xD0, 0xD3, 0xD6, 255)
C_BLACK = (0x14, 0x14, 0x14, 255)
C_RED = (0xC4, 0x1E, 0x2A, 255)

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
    "type", "from", "setting_id", "inherits", "name", "instantiation",
    "version", "is_custom_defined", "compatible_printers", "compatible_prints",
    "compatible_printers_condition", "compatible_prints_condition",
}


def cleanup(m: trimesh.Trimesh) -> trimesh.Trimesh:
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    m.fix_normals()
    return m


def cat(meshes):
    meshes = [m for m in meshes if m is not None and len(getattr(m, "faces", []))]
    if not meshes:
        raise RuntimeError("no meshes")
    out = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0].copy()
    return cleanup(out)


def try_bool(op, meshes, engine="manifold"):
    try:
        return cleanup(getattr(trimesh.boolean, op)(meshes, engine=engine))
    except Exception:
        return None


def box_mesh(xmin, xmax, ymin, ymax, zmin, zmax) -> trimesh.Trimesh:
    c = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2])
    e = np.array([abs(xmax - xmin), abs(ymax - ymin), abs(zmax - zmin)])
    m = trimesh.creation.box(extents=np.maximum(e, 0.18))
    m.apply_translation(c)
    return m


def cyl(radius, height, sections=36) -> trimesh.Trimesh:
    return trimesh.creation.cylinder(radius=radius, height=height, sections=sections)


def loft(xs, rings) -> trimesh.Trimesh:
    n = rings[0].shape[0]
    verts = [np.column_stack([np.full(n, x), ring[:, 0], ring[:, 1]]) for x, ring in zip(xs, rings)]
    V = np.vstack(verts)
    F = []
    for i in range(len(xs) - 1):
        a, b = i * n, (i + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            F.append([a + k, a + k2, b + k2])
            F.append([a + k, b + k2, b + k])
    for start, rev in ((0, True), ((len(xs) - 1) * n, False)):
        c = V[start : start + n].mean(0)
        ci = len(V)
        V = np.vstack([V, c])
        for k in range(n):
            k2 = (k + 1) % n
            F.append([ci, start + k2, start + k] if rev else [ci, start + k, start + k2])
    return cleanup(trimesh.Trimesh(vertices=V, faces=np.array(F), process=True))


def quad_slab(p00, p10, p11, p01, thick: float) -> trimesh.Trimesh:
    q = np.array([p00, p10, p11, p01], float)
    nrm = np.cross(q[1] - q[0], q[3] - q[0])
    nrm = nrm / (np.linalg.norm(nrm) + 1e-9)
    V = np.vstack([q, q + nrm * thick])
    F = [
        [0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6],
        [0, 4, 5], [0, 5, 1], [1, 5, 6], [1, 6, 2],
        [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0],
    ]
    return cleanup(trimesh.Trimesh(vertices=V, faces=F, process=True))


def section(hb, hr, z0, zb, z1) -> np.ndarray:
    """Shoulder + greenhouse: 6-point ring."""
    return np.array(
        [
            [hb, z0],
            [hb, zb],
            [hr, z1],
            [-hr, z1],
            [-hb, zb],
            [-hb, z0],
        ],
        dtype=float,
    )


def interp_curve(xn, xz, n=16):
    x = np.linspace(0.0, 1.0, n)
    return x, np.interp(x, xn, xz)


def hull() -> trimesh.Trimesh:
    """Smooth fastback sedan, Model 3 proportions."""
    z_rock = 0.125 * H
    z_belt = 0.52 * H
    # upper silhouette (roof/hood/trunk), x 0=rear → 1=front
    ux = np.array([0.00, 0.05, 0.12, 0.20, 0.30, 0.40, 0.50, 0.58, 0.66, 0.74, 0.82, 0.90, 0.96, 1.00])
    uz = np.array([0.50, 0.58, 0.64, 0.78, 0.92, 0.985, 1.00, 0.985, 0.90, 0.68, 0.52, 0.44, 0.36, 0.31]) * H
    # body half-width
    wx = np.array([0.00, 0.15, 0.35, 0.55, 0.75, 0.90, 1.00])
    wb = np.array([0.40, 0.47, 0.50, 0.50, 0.47, 0.42, 0.36]) * W
    wr = np.array([0.22, 0.26, 0.32, 0.33, 0.28, 0.20, 0.16]) * W
    xs = np.linspace(0.0, L, 18)
    rings = []
    for x in xs:
        t = x / L
        z1 = float(np.interp(t, ux, uz))
        hb = float(np.interp(t, wx, wb))
        hr = float(np.interp(t, wx, wr))
        z0 = z_rock
        if t < 0.06 or t > 0.94:
            z0 = 0.18 * H
        rings.append(section(hb, hr, z0, min(z_belt, z1 - 0.8), z1))
    return loft(xs, rings)


def aero_wheel(x, y, z, r, width):
    tire = cyl(r, width, 36)
    tire.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    tire.apply_translation([x, y, z])
    hole = cyl(r * 0.78, width + 0.8, 32)
    hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    hole.apply_translation([x, y, z])
    tire = try_bool("difference", [tire, hole]) or tire
    disc = cyl(r * 0.76, width - 1.4, 32)
    disc.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    disc.apply_translation([x, y, z])
    # 5 turbine spokes as raised silver bars
    spokes = []
    for i in range(5):
        a = i * 2 * np.pi / 5
        sp = box_mesh(-0.7, 0.7, -r * 0.08, r * 0.08, 0, r * 0.62)
        rot = trimesh.transformations.rotation_matrix(a, [0, 1, 0])
        sp.apply_transform(rot)
        sp.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        sp.apply_translation([x, y, z])
        spokes.append(sp)
    hub = cyl(r * 0.16, width - 0.5, 20)
    hub.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    hub.apply_translation([x, y, z])
    # caliper
    cal = box_mesh(x - r * 0.22, x + r * 0.22, y - width * 0.15, y + width * 0.15, z + r * 0.15, z + r * 0.55)
    return tire, cat([disc, hub] + spokes), cal


def arch(x, y_sign, r):
    depth = 6.8
    y0 = y_sign * (0.51 * W)
    y1 = y_sign * (0.51 * W - y_sign * depth)
    return box_mesh(x - r * 1.15, x + r * 1.15, min(y0, y1), max(y0, y1), -0.3, r * 1.45)


def glass():
    # windshield
    wind = quad_slab(
        [0.76 * L, -0.30 * W, 0.54 * H],
        [0.76 * L, 0.30 * W, 0.54 * H],
        [0.60 * L, 0.31 * W, 0.96 * H],
        [0.60 * L, -0.31 * W, 0.96 * H],
        1.05,
    )
    # backlight / rear window
    back = quad_slab(
        [0.14 * L, -0.24 * W, 0.66 * H],
        [0.14 * L, 0.24 * W, 0.66 * H],
        [0.30 * L, 0.30 * W, 0.93 * H],
        [0.30 * L, -0.30 * W, 0.93 * H],
        1.00,
    )
    sides = []
    for s in (-1, 1):
        # rear door glass
        sides.append(
            quad_slab(
                [0.28 * L, s * 0.49 * W, 0.55 * H],
                [0.44 * L, s * 0.50 * W, 0.55 * H],
                [0.44 * L, s * 0.42 * W, 0.90 * H],
                [0.32 * L, s * 0.38 * W, 0.88 * H],
                0.95,
            )
        )
        # front door glass
        sides.append(
            quad_slab(
                [0.46 * L, s * 0.50 * W, 0.55 * H],
                [0.66 * L, s * 0.48 * W, 0.55 * H],
                [0.62 * L, s * 0.40 * W, 0.90 * H],
                [0.46 * L, s * 0.42 * W, 0.92 * H],
                0.95,
            )
        )
    # black roof glass (Model 3 glass roof)
    roof = quad_slab(
        [0.34 * L, -0.28 * W, 0.995 * H],
        [0.34 * L, 0.28 * W, 0.995 * H],
        [0.58 * L, 0.28 * W, 0.998 * H],
        [0.58 * L, -0.28 * W, 0.998 * H],
        0.65,
    )
    return cat([wind, back, roof] + sides)


def headlights():
    """Signature Model 3 C-shaped lamps wrapping the nose."""
    parts = []
    for s in (-1, 1):
        parts.append(
            quad_slab(
                [0.96 * L, s * 0.34 * W, 0.30 * H],
                [0.99 * L, s * 0.18 * W, 0.28 * H],
                [0.99 * L, s * 0.16 * W, 0.36 * H],
                [0.94 * L, s * 0.32 * W, 0.40 * H],
                1.15,
            )
        )
        parts.append(
            box_mesh(0.93 * L, 0.97 * L, s * 0.36 * W - 1.0, s * 0.36 * W + 1.0, 0.26 * H, 0.38 * H)
        )
    # lower grille / splitter black
    parts.append(box_mesh(0.94 * L, L + 0.2, -0.22 * W, 0.22 * W, 0.125 * H, 0.22 * H))
    # taillights
    for s in (-1, 1):
        parts.append(box_mesh(-0.15, 1.1, s * 0.38 * W - 1.3, s * 0.38 * W + 1.3, 0.40 * H, 0.50 * H))
    return cat(parts)


def mirrors_and_trim():
    parts = []
    for s in (-1, 1):
        # stalk
        parts.append(box_mesh(0.70 * L, 0.74 * L, s * 0.50 * W, s * 0.56 * W, 0.58 * H, 0.64 * H))
        # cap
        parts.append(box_mesh(0.68 * L, 0.76 * L, s * 0.54 * W, s * 0.62 * W, 0.56 * H, 0.66 * H))
        # door handle
        parts.append(box_mesh(0.54 * L, 0.60 * L, s * 0.505 * W - 0.4, s * 0.505 * W + 0.4, 0.48 * H, 0.52 * H))
    return cat(parts)


def build_meshes():
    print(f"Model 3  {L:.1f} x {W:.1f} x {H:.1f} mm  (1:{1/S:.0f})")
    print(f"  WB={WB:.1f}  tire R={R_TIRE:.2f}")
    body = hull()
    x_r = OH_R
    x_f = L - OH_F
    z_ax = R_TIRE
    y_w = 0.50 * W - 3.2
    wells = cat([arch(x_f, s, R_TIRE) for s in (-1.0, 1.0)] + [arch(x_r, s, R_TIRE) for s in (-1.0, 1.0)])
    cut = try_bool("difference", [body, wells])
    body = cut if cut is not None else body

    tires, discs, cals = [], [], []
    tw = 5.4
    for s in (-1.0, 1.0):
        t, d, c = aero_wheel(x_f, s * y_w, z_ax, R_TIRE, tw)
        tires.append(t)
        discs.append(d)
        cals.append(c)
        t, d, c = aero_wheel(x_r, s * y_w, z_ax, R_TIRE, tw)
        tires.append(t)
        discs.append(d)
        cals.append(c)

    g = glass()
    lamps = headlights()
    mir = mirrors_and_trim()

    def clip_z(m):
        sl = m.slice_plane(plane_origin=[0, 0, -0.02], plane_normal=[0, 0, 1])
        return sl if sl is not None and len(sl.faces) else m

    silver = clip_z(cat([body, mir] + discs))
    black = clip_z(cat(tires + [g, lamps]))
    red = clip_z(cat(cals))
    return silver, black, red


def preview(silver, black, red) -> bytes:
    fig = plt.figure(figsize=(11.2, 8.4), dpi=130)
    fig.patch.set_facecolor("#2a2a2a")

    def draw(ax, elev, azim, title):
        ax.set_facecolor("#2a2a2a")
        for mesh, col in ((silver, "#d0d3d6"), (black, "#141414"), (red, "#c41e2a")):
            pc = Poly3DCollection(mesh.vertices[mesh.faces], linewidths=0.0)
            pc.set_facecolor(col)
            pc.set_edgecolor("none")
            ax.add_collection3d(pc)
        b = np.vstack([silver.bounds, black.bounds, red.bounds])
        mn, mx = b.min(0), b.max(0)
        c = (mn + mx) / 2
        r = (mx - mn).max() * 0.62
        ax.set_xlim(c[0] - r, c[0] + r)
        ax.set_ylim(c[1] - r, c[1] + r)
        ax.set_zlim(c[2] - r, c[2] + r)
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(title, color="#ddd", fontsize=10, pad=2)
        try:
            ax.set_box_aspect((1, 1, 1))
        except Exception:
            pass

    for i, (e, a, t) in enumerate(
        [(22, 35, "iso"), (8, 90, "side"), (8, 0, "front"), (90, 90, "top")], 1
    ):
        draw(fig.add_subplot(2, 2, i, projection="3d"), e, a, t)
    fig.suptitle("Tesla Model 3  ·  PLA prata  ·  Kobra X", color="#eee", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT_PREVIEW, dpi=130, facecolor=fig.get_facecolor())
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _load_preset(path: Path) -> dict:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k not in _SKIP_PRESET_KEYS}


def _expand_filament(preset: dict, n: int) -> dict:
    out = {}
    for key, raw in preset.items():
        if isinstance(raw, list):
            out[key] = [raw[0]] * n if len(raw) == 1 else raw
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
        cfg["flush_volumes_matrix"] = ["0" if i == j else "140" for i in range(n) for j in range(n)]
        cfg["flush_volumes_vector"] = ["140"] * (n * 2)
    return json.dumps(cfg, indent=4) + "\n"


def _slice_info(parts) -> str:
    fils = "\n".join(
        f'    <filament id="{i}" tray_info_idx="{PLA_FILAMENT_ID}" type="PLA" '
        f'color="#{c[0]:02X}{c[1]:02X}{c[2]:02X}" used_m="0" used_g="0"/>'
        for i, (_, _, c) in enumerate(parts, start=1)
    )
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
{fils}
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
        object_files.append(
            (obj_path.lstrip("/"), _mesh_model_xml(mesh, mesh_id, f"{mesh_id:08x}-{_MESH_SUF}"))
        )
        components.append(
            f'    <component p:path="{obj_path}" objectid="{mesh_id}" '
            f'p:UUID="{mesh_id:08x}-{_COMP_SUF}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
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
 <metadata name="Title">Tesla Model 3</metadata>
 <metadata name="Description">Tesla Model 3 1:41 desk model. PLA silver, Kobra X 0.4 mm, no supports. Fan print.</metadata>
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
    <metadata key="name" value="Tesla Model 3"/>
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


def build():
    silver, black, red = build_meshes()
    parts = []
    for name, m, col in [
        ("Carroceria prata", silver, C_SILVER),
        ("Vidros e pneus", black, C_BLACK),
        ("Pinças vermelhas", red, C_RED),
    ]:
        b = m.bounds
        s = b[1] - b[0]
        print(
            f"  {name:20s} tris={len(m.faces):6d} watertight={m.is_watertight} "
            f"size={s[0]:6.1f} x {s[1]:6.1f} x {s[2]:5.2f} mm  z0={b[0,2]:.2f}"
        )
        if s[0] > BED + 1 or s[1] > BED + 1:
            raise RuntimeError(f"{name} exceeds Kobra X bed")
        parts.append((m, name, col))
    thumb = preview(silver, black, red)
    write_3mf(OUT_3MF, parts, thumb)
    print(f"Wrote {OUT_3MF} ({OUT_3MF.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build()
