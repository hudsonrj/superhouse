#!/usr/bin/env python3
"""Tesla Cybercab desk model 3MF — Anycubic Kobra X, PLA, ACE.

~104 mm long (~1:43). Silver body + disc covers, black glass/tires,
white LED bars. Sits on the wheels, no supports.
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
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT_3MF = ROOT / "Cybercab_KobraX.3mf"
OUT_PREVIEW = ROOT / "cybercab_preview.png"

BED = 260.0
NOZZLE = 0.4
MIN_T = 1.20

# Official-ish exterior: 4445 x 1754 x 1408 mm (175" x 69" x 55.4")
REAL = np.array([4445.0, 1754.0, 1408.0])
L = 104.0
S = L / REAL[0]
W = REAL[1] * S
H = REAL[2] * S

C_SILVER = (0xC9, 0xCD, 0xD2, 255)
C_BLACK = (0x1A, 0x1A, 0x1A, 255)
C_LIGHT = (0xEAF2, 0xF8, 0xFF, 255) if False else (0xEA, 0xF2, 0xFF, 255)

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


def cleanup(m: trimesh.Trimesh) -> trimesh.Trimesh:
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices()
    m.fix_normals()
    return m


def cat(meshes):
    meshes = [m for m in meshes if m is not None and len(m.faces)]
    if not meshes:
        raise RuntimeError("no meshes")
    out = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0].copy()
    return cleanup(out)


def try_bool(op, meshes, engine="manifold"):
    try:
        out = getattr(trimesh.boolean, op)(meshes, engine=engine)
        return cleanup(out)
    except Exception:
        return None


def box_mesh(xmin, xmax, ymin, ymax, zmin, zmax) -> trimesh.Trimesh:
    c = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2])
    e = np.array([xmax - xmin, ymax - ymin, zmax - zmin])
    m = trimesh.creation.box(extents=e)
    m.apply_translation(c)
    return m


def cyl(radius, height, sections=48) -> trimesh.Trimesh:
    return trimesh.creation.cylinder(radius=radius, height=height, sections=sections)


def resample_ring(pts: np.ndarray, n: int) -> np.ndarray:
    pts = np.asarray(pts, float)
    if np.linalg.norm(pts[0] - pts[-1]) > 1e-9:
        pts = np.vstack([pts, pts[0]])
    d = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(d)])
    keep = np.ones(len(s), dtype=bool)
    keep[1:] = np.diff(s) > 1e-9
    s, pts = s[keep], pts[keep]
    if s[-1] < 1e-9:
        return np.repeat(pts[:1], n, axis=0)
    t = np.linspace(0.0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, pts[:, i]) for i in range(pts.shape[1])])


def rounded_yz(half_w: float, z0: float, z1: float, r: float, n: int = 32) -> np.ndarray:
    r = min(r, half_w * 0.55, (z1 - z0) * 0.35)
    # clockwise from bottom-center so loft rings share parameterization
    ang = np.linspace(0, np.pi / 2, 8)
    # bottom-right corner
    br = np.column_stack([half_w - r + r * np.cos(-ang), z0 + r + r * np.sin(-ang)])
    # top-right
    tr = np.column_stack([half_w - r + r * np.cos(ang), z1 - r + r * np.sin(ang)])
    # top-left
    tl = np.column_stack([-half_w + r + r * np.cos(np.pi / 2 + ang), z1 - r + r * np.sin(np.pi / 2 + ang)])
    # bottom-left
    bl = np.column_stack([-half_w + r + r * np.cos(np.pi + ang), z0 + r + r * np.sin(np.pi + ang)])
    ring = np.vstack([br, tr, tl, bl])
    return resample_ring(ring, n)


def loft(xs: np.ndarray, rings: list[np.ndarray]) -> trimesh.Trimesh:
    n = rings[0].shape[0]
    verts = []
    for x, ring in zip(xs, rings):
        verts.append(np.column_stack([np.full(n, x), ring[:, 0], ring[:, 1]]))
    V = np.vstack(verts)
    F = []
    for i in range(len(xs) - 1):
        a = i * n
        b = (i + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            F.append([a + k, a + k2, b + k2])
            F.append([a + k, b + k2, b + k])
    # caps
    for start, rev in ((0, True), ((len(xs) - 1) * n, False)):
        ring = V[start : start + n]
        c = ring.mean(0)
        ci = len(V)
        V = np.vstack([V, c])
        for k in range(n):
            k2 = (k + 1) % n
            if rev:
                F.append([ci, start + k2, start + k])
            else:
                F.append([ci, start + k, start + k2])
    return cleanup(trimesh.Trimesh(vertices=V, faces=np.array(F), process=True))


def quad_slab(p00, p10, p11, p01, thick: float) -> trimesh.Trimesh:
    q = np.array([p00, p10, p11, p01], float)
    nrm = np.cross(q[1] - q[0], q[3] - q[0])
    nrm = nrm / (np.linalg.norm(nrm) + 1e-9)
    off = nrm * thick
    V = np.vstack([q, q + off])
    F = [
        [0, 1, 2],
        [0, 2, 3],
        [4, 6, 5],
        [4, 7, 6],
        [0, 4, 5],
        [0, 5, 1],
        [1, 5, 6],
        [1, 6, 2],
        [2, 6, 7],
        [2, 7, 3],
        [3, 7, 4],
        [3, 4, 0],
    ]
    return cleanup(trimesh.Trimesh(vertices=V, faces=F, process=True))


def body_shell() -> trimesh.Trimesh:
    # x: 0 rear → L front. Soft teardrop like the production Cybercab.
    stations = [
        # x, half_w, z0, z1, corner
        (0.00 * L, 0.375 * W, 0.12 * H, 0.70 * H, 0.055 * W),
        (0.06 * L, 0.405 * W, 0.11 * H, 0.76 * H, 0.060 * W),
        (0.16 * L, 0.455 * W, 0.105 * H, 0.86 * H, 0.065 * W),
        (0.28 * L, 0.485 * W, 0.100 * H, 0.96 * H, 0.070 * W),
        (0.42 * L, 0.498 * W, 0.100 * H, 1.00 * H, 0.072 * W),
        (0.55 * L, 0.500 * W, 0.102 * H, 0.99 * H, 0.070 * W),
        (0.68 * L, 0.478 * W, 0.108 * H, 0.84 * H, 0.062 * W),
        (0.78 * L, 0.445 * W, 0.110 * H, 0.58 * H, 0.070 * W),
        (0.88 * L, 0.405 * W, 0.110 * H, 0.48 * H, 0.085 * W),
        (0.95 * L, 0.360 * W, 0.112 * H, 0.42 * H, 0.095 * W),
        (1.00 * L, 0.325 * W, 0.115 * H, 0.38 * H, 0.100 * W),
    ]
    xs = np.array([s[0] for s in stations])
    rings = [rounded_yz(hw, z0, z1, r, n=40) for _, hw, z0, z1, r in stations]
    hull = loft(xs, rings)
    nose = trimesh.creation.icosphere(subdivisions=3, radius=0.24 * W)
    nose.apply_scale([0.70, 1.02, 0.72])
    nose.apply_translation([0.94 * L, 0.0, 0.25 * H])
    merged = try_bool("union", [hull, nose])
    return merged if merged is not None else hull


def wheel(x, y, z, r_tire, r_disc, width, sections=40):
    tire = cyl(r_tire, width, sections)
    tire.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    tire.apply_translation([x, y, z])
    # hole so the silver disc reads as a cover
    hole = cyl(r_disc + 0.15, width + 0.6, sections)
    hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    hole.apply_translation([x, y, z])
    cut = try_bool("difference", [tire, hole])
    if cut is None:
        cut = tire
    disc = cyl(r_disc, width - 1.15, sections)
    disc.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    disc.apply_translation([x, y, z])
    ring = cyl(r_disc * 0.22, width - 0.55, 24)
    ring.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    ring.apply_translation([x, y, z])
    return cut, cat([disc, ring])


def well_side(x, y, z, r, width):
    c = cyl(r, width, 40)
    c.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    c.apply_translation([x, y, z])
    return c


def glass_and_trim():
    hw = 0.455 * W
    # windshield — raked quad, slightly inset
    z_hood, z_roof = 0.44 * H, 0.935 * H
    x_hood, x_roof = 0.79 * L, 0.64 * L
    y_hood, y_roof = hw * 0.80, hw * 0.52
    wind = quad_slab(
        [x_hood, -y_hood, z_hood],
        [x_hood, y_hood, z_hood],
        [x_roof, y_roof, z_roof],
        [x_roof, -y_roof, z_roof],
        1.10,
    )
    # side glass (closed butterfly doors)
    side = []
    for s in (-1, 1):
        side.append(
            quad_slab(
                [0.36 * L, s * hw * 0.93, 0.47 * H],
                [0.60 * L, s * hw * 0.91, 0.49 * H],
                [0.64 * L, s * hw * 0.84, 0.87 * H],
                [0.42 * L, s * hw * 0.86, 0.89 * H],
                1.05,
            )
        )
    # roof glass strip (Cybercab has a dark canopy band)
    canopy = quad_slab(
        [0.42 * L, -hw * 0.50, 0.992 * H],
        [0.42 * L, hw * 0.50, 0.992 * H],
        [0.62 * L, hw * 0.44, 0.988 * H],
        [0.62 * L, -hw * 0.44, 0.988 * H],
        0.70,
    )
    return cat([wind, canopy] + side)


def light_bars():
    # front full-width bar, slightly wrapping
    z = 0.27 * H
    front = box_mesh(0.965 * L, L + 0.35, -0.30 * W, 0.30 * W, z - 0.85, z + 0.85)
    wrap = []
    for s in (-1, 1):
        wrap.append(box_mesh(0.93 * L, 0.985 * L, s * 0.33 * W - 0.7, s * 0.33 * W + 0.7, z - 0.7, z + 0.7))
    # rear bar + two down-strikes
    zr = 0.48 * H
    rear = box_mesh(-0.25, 0.9, -0.36 * W, 0.36 * W, zr - 0.7, zr + 0.7)
    down = []
    for s in (-1, 1):
        down.append(box_mesh(-0.15, 0.7, s * 0.38 * W - 0.55, s * 0.38 * W + 0.55, 0.18 * H, zr))
    return cat([front, rear] + wrap + down)


def black_cladding(r_f, r_r, x_f, x_r, z_axle_f, z_axle_r, y_f, y_r, tw):
    parts = []
    # splitter / lower front
    parts.append(box_mesh(0.90 * L, L + 0.2, -0.32 * W, 0.32 * W, 0.09 * H, 0.20 * H))
    # rear valence
    parts.append(box_mesh(-0.2, 0.10 * L, -0.34 * W, 0.34 * W, 0.09 * H, 0.20 * H))
    # rocker
    parts.append(box_mesh(0.18 * L, 0.78 * L, -0.505 * W, -0.455 * W, 0.10 * H, 0.22 * H))
    parts.append(box_mesh(0.18 * L, 0.78 * L, 0.455 * W, 0.505 * W, 0.10 * H, 0.22 * H))
    # camera pills on the front fenders
    for s in (-1, 1):
        cam = cyl(1.15, 2.4, 16)
        cam.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
        cam.apply_translation([0.84 * L, s * 0.36 * W, 0.38 * H])
        parts.append(cam)
        # butterfly-door shutline
        parts.append(
            quad_slab(
                [0.33 * L, s * 0.50 * W, 0.22 * H],
                [0.67 * L, s * 0.49 * W, 0.24 * H],
                [0.67 * L, s * 0.48 * W, 0.92 * H],
                [0.38 * L, s * 0.49 * W, 0.94 * H],
                0.55,
            )
        )
    return cat(parts)


def build_meshes():
    print(f"Cybercab  {L:.1f} x {W:.1f} x {H:.1f} mm  (1:{1/S:.0f})")
    body = body_shell()

    r_f = 0.248 * H * 1.05  # ~18" + 60-series
    r_r = 0.285 * H * 1.05  # larger rear
    tw_f = 0.125 * W
    tw_r = 0.132 * W
    x_f = 0.78 * L
    x_r = 0.22 * L
    z_f = r_f
    z_r = r_r
    y_f = 0.50 * W - tw_f * 0.52
    y_r = 0.47 * W - tw_r * 0.52  # rear track slightly narrower

    # wheel wells — pockets from each side, not a tunnel through the cabin
    well_w = 8.8
    y_well_f = 0.50 * W - well_w * 0.28
    y_well_r = 0.47 * W - well_w * 0.28
    wells = cat(
        [
            well_side(x_f, s * y_well_f, z_f, r_f + 1.55, well_w)
            for s in (-1.0, 1.0)
        ]
        + [
            well_side(x_r, s * y_well_r, z_r, r_r + 1.70, well_w)
            for s in (-1.0, 1.0)
        ]
    )
    cut = try_bool("difference", [body, wells])
    body = cut if cut is not None else body

    tires, discs = [], []
    for s in (-1.0, 1.0):
        t, d = wheel(x_f, s * y_f, z_f, r_f, r_f * 0.84, tw_f)
        tires.append(t)
        discs.append(d)
        t, d = wheel(x_r, s * y_r, z_r, r_r, r_r * 0.84, tw_r)
        tires.append(t)
        discs.append(d)

    glass = glass_and_trim()
    lights = light_bars()
    clad = black_cladding(r_f, r_r, x_f, x_r, z_f, z_r, y_f, y_r, tw_f)

    silver = cat([body] + discs)
    black = cat(tires + [glass, clad])
    # drop anything below the bed
    def clip_z(m, zmin=-0.02):
        return m.slice_plane(plane_origin=[0, 0, zmin], plane_normal=[0, 0, 1]) or m

    silver = clip_z(silver)
    black = clip_z(black)
    lights = clip_z(lights)
    return silver, black, lights


def preview(silver, black, lights) -> bytes:
    fig = plt.figure(figsize=(11.2, 8.4), dpi=130)
    fig.patch.set_facecolor("#2c2c2c")

    def draw(ax, elev, azim, title):
        ax.set_facecolor("#2c2c2c")
        for mesh, col, alpha in (
            (silver, "#c9cdd2", 1.0),
            (black, "#1a1a1a", 1.0),
            (lights, "#eaf2ff", 1.0),
        ):
            tris = mesh.vertices[mesh.faces]
            pc = Poly3DCollection(tris, linewidths=0.0)
            pc.set_facecolor(col)
            pc.set_edgecolor("none")
            pc.set_alpha(alpha)
            ax.add_collection3d(pc)
        b = np.vstack([silver.bounds, black.bounds, lights.bounds])
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

    specs = [(22, 35, "iso"), (8, 90, "side"), (8, 0, "front"), (90, 90, "top")]
    for i, (e, a, t) in enumerate(specs, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        draw(ax, e, a, t)
    fig.suptitle("Cybercab  ·  PLA prata  ·  Kobra X", color="#eee", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT_PREVIEW, dpi=130, facecolor=fig.get_facecolor())
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


# --- Anycubic Slicer Next 3MF ---
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
 <metadata name="Title">Cybercab</metadata>
 <metadata name="Description">Tesla Cybercab 1:43 desk model. PLA, Kobra X 0.4 mm, no supports. Fan print.</metadata>
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
    <metadata key="name" value="Cybercab"/>
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


def build():
    silver, black, lights = build_meshes()
    parts = []
    for name, m, col in [
        ("Carroceria prata", silver, C_SILVER),
        ("Vidros e pneus", black, C_BLACK),
        ("Barras de LED", lights, C_LIGHT),
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
    thumb = preview(silver, black, lights)
    write_3mf(OUT_3MF, parts, thumb)
    print(f"Wrote {OUT_3MF} ({OUT_3MF.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build()
