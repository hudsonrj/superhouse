#!/usr/bin/env python3
"""Tesla Cybertruck desk model — Anycubic Kobra X, PLA prata.

Faceted stainless-steel planes (the real body language). ~118 mm long,
sits on the wheels, no supports. Silver body, black glass/tires, white LEDs.
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

ROOT = Path(__file__).resolve().parent
OUT_3MF = ROOT / "Cybertruck_KobraX.3mf"
OUT_PREVIEW = ROOT / "cybertruck_preview.png"

BED = 260.0

# Tesla manual: 5682.9 x 2031.6 x 1793.8 mm, WB 3635, tire 285/65R20
REAL_L, REAL_W, REAL_H = 5682.9, 2031.6, 1793.8
REAL_WB, REAL_OH_F, REAL_OH_R = 3635.0, 878.3, 1169.6
REAL_TIRE = 20 * 25.4 + 2 * 285 * 0.65  # ~878.5 mm

L = 118.0
S = L / REAL_L
W = REAL_W * S
H = REAL_H * S
WB = REAL_WB * S
OH_F = REAL_OH_F * S
OH_R = REAL_OH_R * S
R_TIRE = REAL_TIRE * S / 2.0

C_SILVER = (0xC5, 0xC9, 0xCE, 255)
C_BLACK = (0x16, 0x16, 0x16, 255)
C_LIGHT = (0xEA, 0xF2, 0xFF, 255)

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
    meshes = [m for m in meshes if m is not None and len(getattr(m, "faces", []))]
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
    e = np.array([abs(xmax - xmin), abs(ymax - ymin), abs(zmax - zmin)])
    m = trimesh.creation.box(extents=np.maximum(e, 0.2))
    m.apply_translation(c)
    return m


def cyl(radius, height, sections=36) -> trimesh.Trimesh:
    return trimesh.creation.cylinder(radius=radius, height=height, sections=sections)


def trap_yz(hb, ht, z0, z1) -> np.ndarray:
    """4 corners, shared parameterization between stations → origami panels."""
    return np.array(
        [[hb, z0], [ht, z1], [-ht, z1], [-hb, z0]],
        dtype=float,
    )


def loft(xs, rings) -> trimesh.Trimesh:
    n = rings[0].shape[0]
    verts = []
    for x, ring in zip(xs, rings):
        verts.append(np.column_stack([np.full(n, x), ring[:, 0], ring[:, 1]]))
    V = np.vstack(verts)
    F = []
    for i in range(len(xs) - 1):
        a, b = i * n, (i + 1) * n
        for k in range(n):
            k2 = (k + 1) % n
            F.append([a + k, a + k2, b + k2])
            F.append([a + k, b + k2, b + k])
    for start, rev in ((0, True), ((len(xs) - 1) * n, False)):
        ring = V[start : start + n]
        c = ring.mean(0)
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


def hull() -> trimesh.Trimesh:
    """Stainless origami: 4-vertex stations loft into flat panels."""
    # x=0 rear bumper, x=L nose. z=0 ground.
    z_rock = 0.145 * H  # ~ground clearance
    stations = [
        # x, half_bottom, half_top, z0, z1
        (0.00 * L, 0.36 * W, 0.22 * W, 0.22 * H, 0.50 * H),  # tail / vault end
        (0.18 * L, 0.45 * W, 0.27 * W, z_rock, 0.56 * H),  # bed
        (0.36 * L, 0.48 * W, 0.22 * W, z_rock, 0.86 * H),  # C-pillar / rear glass
        (0.50 * L, 0.495 * W, 0.11 * W, z_rock, 1.00 * H),  # knife-edge roof
        (0.74 * L, 0.470 * W, 0.34 * W, z_rock, 0.50 * H),  # windshield base
        (0.90 * L, 0.400 * W, 0.36 * W, 0.165 * H, 0.34 * H),  # hood
        (1.00 * L, 0.300 * W, 0.28 * W, 0.185 * H, 0.295 * H),  # pointed nose
    ]
    xs = np.array([s[0] for s in stations])
    rings = [trap_yz(hb, ht, z0, z1) for _, hb, ht, z0, z1 in stations]
    return loft(xs, rings)


def wheel(x, y, z, r, width):
    tire = cyl(r, width, 32)
    tire.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    tire.apply_translation([x, y, z])
    hole = cyl(r * 0.78, width + 0.8, 28)
    hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    hole.apply_translation([x, y, z])
    cut = try_bool("difference", [tire, hole]) or tire
    disc = cyl(r * 0.76, width - 1.3, 28)
    disc.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    disc.apply_translation([x, y, z])
    # angular hub — hex nut
    hub = trimesh.creation.cylinder(radius=r * 0.22, height=width - 0.4, sections=6)
    hub.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
    hub.apply_translation([x, y, z])
    return cut, cat([disc, hub])


def arch(x, y_sign, r):
    """Angular wheel-arch pocket cut from the side (not a tunnel)."""
    depth = 7.4
    y0 = y_sign * (0.52 * W)
    y1 = y_sign * (0.52 * W - y_sign * depth)
    ymin, ymax = min(y0, y1), max(y0, y1)
    return box_mesh(x - r * 1.20, x + r * 1.20, ymin, ymax, -0.4, r * 1.55)


def glass():
    hw = 0.48 * W
    # windshield — the big forward plane
    wind = quad_slab(
        [0.74 * L, -0.32 * W, 0.50 * H],
        [0.74 * L, 0.32 * W, 0.50 * H],
        [0.505 * L, 0.11 * W, 0.975 * H],
        [0.505 * L, -0.11 * W, 0.975 * H],
        1.10,
    )
    # rear cab glass
    rear = quad_slab(
        [0.495 * L, -0.11 * W, 0.975 * H],
        [0.495 * L, 0.11 * W, 0.975 * H],
        [0.365 * L, 0.21 * W, 0.84 * H],
        [0.365 * L, -0.21 * W, 0.84 * H],
        1.05,
    )
    sides = []
    for s in (-1, 1):
        sides.append(
            quad_slab(
                [0.42 * L, s * hw * 0.90, 0.50 * H],
                [0.68 * L, s * hw * 0.86, 0.50 * H],
                [0.68 * L, s * hw * 0.70, 0.76 * H],
                [0.44 * L, s * hw * 0.58, 0.86 * H],
                1.00,
            )
        )
    return cat([wind, rear] + sides)


def lights():
    zf = 0.255 * H
    front = box_mesh(0.985 * L, L + 0.45, -0.33 * W, 0.33 * W, zf - 0.75, zf + 0.75)
    zr = 0.40 * H
    rear = box_mesh(-0.25, 0.85, -0.28 * W, 0.28 * W, zr - 0.65, zr + 0.65)
    return cat([front, rear])


def cladding(x_f, x_r, r):
    parts = []
    # front splitter
    parts.append(box_mesh(0.92 * L, L + 0.15, -0.34 * W, 0.34 * W, 0.145 * H, 0.21 * H))
    # rear valence
    parts.append(box_mesh(-0.1, 0.08 * L, -0.30 * W, 0.30 * W, 0.16 * H, 0.23 * H))
    # side steps
    parts.append(box_mesh(0.34 * L, 0.70 * L, -0.52 * W, -0.47 * W, 0.145 * H, 0.20 * H))
    parts.append(box_mesh(0.34 * L, 0.70 * L, 0.47 * W, 0.52 * W, 0.145 * H, 0.20 * H))
    # fender cameras
    for s in (-1, 1):
        cam = box_mesh(0.86 * L, 0.90 * L, s * 0.40 * W - 1.1, s * 0.40 * W + 1.1, 0.36 * H, 0.42 * H)
        parts.append(cam)
        # door shutline
        parts.append(
            quad_slab(
                [0.40 * L, s * 0.495 * W, 0.20 * H],
                [0.70 * L, s * 0.475 * W, 0.20 * H],
                [0.70 * L, s * 0.455 * W, 0.82 * H],
                [0.42 * L, s * 0.430 * W, 0.92 * H],
                0.50,
            )
        )
    return cat(parts)


def build_meshes():
    print(f"Cybertruck  {L:.1f} x {W:.1f} x {H:.1f} mm  (1:{1/S:.0f})")
    print(f"  WB={WB:.1f}  tire R={R_TIRE:.2f}  OH F/R={OH_F:.1f}/{OH_R:.1f}")
    body = hull()
    x_r = OH_R
    x_f = L - OH_F
    z_ax = R_TIRE
    y_w = 0.50 * W - 3.6

    wells = cat([arch(x_f, s, R_TIRE) for s in (-1.0, 1.0)] + [arch(x_r, s, R_TIRE) for s in (-1.0, 1.0)])
    cut = try_bool("difference", [body, wells])
    body = cut if cut is not None else body

    tires, discs = [], []
    tw = 5.8
    for s in (-1.0, 1.0):
        t, d = wheel(x_f, s * y_w, z_ax, R_TIRE, tw)
        tires.append(t)
        discs.append(d)
        t, d = wheel(x_r, s * y_w, z_ax, R_TIRE, tw)
        tires.append(t)
        discs.append(d)

    g = glass()
    led = lights()
    black_trim = cladding(x_f, x_r, R_TIRE)

    def clip_z(m):
        sl = m.slice_plane(plane_origin=[0, 0, -0.02], plane_normal=[0, 0, 1])
        return sl if sl is not None and len(sl.faces) else m

    silver = clip_z(cat([body] + discs))
    black = clip_z(cat(tires + [g, black_trim]))
    return silver, black, clip_z(led)


def preview(silver, black, lights) -> bytes:
    fig = plt.figure(figsize=(11.2, 8.4), dpi=130)
    fig.patch.set_facecolor("#2a2a2a")

    def draw(ax, elev, azim, title):
        ax.set_facecolor("#2a2a2a")
        for mesh, col in ((silver, "#c5c9ce"), (black, "#161616"), (lights, "#eaf2ff")):
            pc = Poly3DCollection(mesh.vertices[mesh.faces], linewidths=0.0)
            pc.set_facecolor(col)
            pc.set_edgecolor("none")
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

    for i, (e, a, t) in enumerate(
        [(22, 35, "iso"), (8, 90, "side"), (8, 0, "front"), (90, 90, "top")], 1
    ):
        draw(fig.add_subplot(2, 2, i, projection="3d"), e, a, t)
    fig.suptitle("Cybertruck  ·  PLA prata  ·  Kobra X", color="#eee", fontsize=13)
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
        flush = ["0" if i == j else "140" for i in range(n) for j in range(n)]
        cfg["flush_volumes_matrix"] = flush
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
 <metadata name="Title">Cybertruck</metadata>
 <metadata name="Description">Tesla Cybertruck 1:48 desk model. PLA silver, Kobra X 0.4 mm, no supports. Fan print.</metadata>
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
    <metadata key="name" value="Cybertruck"/>
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
    silver, black, led = build_meshes()
    parts = []
    for name, m, col in [
        ("Carroceria inox", silver, C_SILVER),
        ("Vidros e pneus", black, C_BLACK),
        ("Barras de LED", led, C_LIGHT),
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
    thumb = preview(silver, black, led)
    write_3mf(OUT_3MF, parts, thumb)
    print(f"Wrote {OUT_3MF} ({OUT_3MF.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build()
