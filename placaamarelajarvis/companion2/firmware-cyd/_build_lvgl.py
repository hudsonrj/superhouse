"""Compile atlas_lvgl (LVGL 8 + CONTROL tiles) and optionally flash COM5."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.abspath(__file__))
INO = os.path.join(ROOT, "atlas_lvgl", "atlas_lvgl.ino")
BUILD = os.path.join(ROOT, "atlas_lvgl", "build", "esp32.esp32.esp32")
SKETCH_CPP = os.path.join(BUILD, "sketch", "atlas_lvgl.ino.cpp")
ARDUINO = r"C:\Users\hudson.santos\AppData\Local\Arduino15"
ATOM = r"C:\Users\hudson.santos\AppData\Local\arduino\sketches\2566598A9071A83314FDB6F62524F9E0"
HW = os.path.join(ARDUINO, r"packages\esp32\hardware\esp32\3.3.12")
SDK = os.path.join(ARDUINO, r"packages\esp32\tools\esp32-arduino-libs\idf-release_v5.5-07e9bf49-v1\esp32")
BINDIR = os.path.join(ARDUINO, r"packages\esp32\tools\esp-x32\2507\bin")
ESPTOOL = os.path.join(ARDUINO, r"packages\esp32\tools\esptool_py\5.3.1\esptool.exe")
GENPART = os.path.join(HW, "tools", "gen_esp32part.exe")
GXX = os.path.join(BINDIR, "xtensa-esp32-elf-g++.exe")
GCC = os.path.join(BINDIR, "xtensa-esp32-elf-gcc.exe")
LVGL = os.path.join(ROOT, "libs", "lvgl")

os.makedirs(BUILD, exist_ok=True)
for name in ("build_opt.h", "file_opts"):
    path = os.path.join(BUILD, name)
    if not os.path.exists(path):
        open(path, "w").close()

COMMON = [
    "-MMD",
    "-c",
    "-w",
    "-Os",
    "-Werror=return-type",
    "-DF_CPU=240000000L",
    "-DARDUINO=10607",
    "-DARDUINO_ESP32_DEV",
    "-DARDUINO_ARCH_ESP32",
    '-DARDUINO_BOARD="ESP32_DEV"',
    '-DARDUINO_VARIANT="esp32"',
    "-DARDUINO_PARTITION_huge_app",
    '-DARDUINO_HOST_OS="windows"',
    '-DARDUINO_FQBN="esp32:esp32:esp32"',
    "-DESP32=ESP32",
    "-DCORE_DEBUG_LEVEL=0",
    "-DARDUINO_RUNNING_CORE=1",
    "-DARDUINO_EVENT_RUNNING_CORE=1",
    "-DARDUINO_USB_CDC_ON_BOOT=0",
    "-DLV_CONF_INCLUDE_SIMPLE",
    f"@{SDK}/flags/defines",
    f"-I{os.path.join(ROOT, 'atlas_lvgl')}",
    f"-I{LVGL}",
    f"-I{os.path.join(LVGL, 'src')}",
    f"-iprefix{SDK}/include/",
    f"@{SDK}/flags/includes",
    f"-I{SDK}/qio_qspi/include",
    f"-I{HW}/cores/esp32",
    f"-I{HW}/variants/esp32",
    f"-I{HW}/libraries/SPI/src",
    f"-I{HW}/libraries/FS/src",
    f"-I{HW}/libraries/WiFi/src",
    f"-I{HW}/libraries/ESPmDNS/src",
    f"-I{HW}/libraries/Network/src",
    f"-I{HW}/libraries/HTTPClient/src",
    f"-I{HW}/libraries/NetworkClientSecure/src",
    f"-I{os.path.join(ROOT, 'libs', 'Adafruit_GFX_Library')}",
    f"-I{os.path.join(ROOT, 'libs', 'Adafruit_BusIO')}",
    f"-I{HW}/libraries/Wire/src",
    f"-I{os.path.join(ROOT, 'libs', 'Adafruit_ILI9341')}",
    f"-I{os.path.join(ROOT, 'libs', 'XPT2046_Touchscreen')}",
    f"@{BUILD}/build_opt.h",
    f"@{BUILD}/file_opts",
]

SKIP_DIR = (
    "arm2d",
    "nxp",
    "sdl",
    "stm32_dma2d",
    "swm341_dma2d",
    "renesas",
    os.path.join("extra", "libs"),
    os.path.join("extra", "others"),
    os.path.join("themes", "basic"),
    os.path.join("themes", "mono"),
    os.path.join("widgets", "animimg"),
    os.path.join("widgets", "calendar"),
    os.path.join("widgets", "chart"),
    os.path.join("widgets", "colorwheel"),
    os.path.join("widgets", "imgbtn"),
    os.path.join("widgets", "led"),
    os.path.join("widgets", "menu"),
    os.path.join("widgets", "meter"),
    os.path.join("widgets", "msgbox"),
    os.path.join("widgets", "spinbox"),
    os.path.join("widgets", "spinner"),
    os.path.join("widgets", "tabview"),
    os.path.join("widgets", "tileview"),
    os.path.join("widgets", "win"),
)
SKIP_FILE = {
    "lv_templ.c",
    "lv_objx_templ.c",
    "lv_font_dejavu_16_persian_hebrew.c",
    "lv_font_simsun_16_cjk.c",
    "lv_font_unscii_8.c",
    "lv_font_unscii_16.c",
    "lv_font_montserrat_8.c",
    "lv_font_montserrat_10.c",
    "lv_font_montserrat_12.c",
    "lv_font_montserrat_12_subpx.c",
    "lv_font_montserrat_16.c",
    "lv_font_montserrat_18.c",
    "lv_font_montserrat_22.c",
    "lv_font_montserrat_24.c",
    "lv_font_montserrat_26.c",
    "lv_font_montserrat_28.c",
    "lv_font_montserrat_28_compressed.c",
    "lv_font_montserrat_30.c",
    "lv_font_montserrat_32.c",
    "lv_font_montserrat_34.c",
    "lv_font_montserrat_36.c",
    "lv_font_montserrat_38.c",
    "lv_font_montserrat_40.c",
    "lv_font_montserrat_42.c",
    "lv_font_montserrat_44.c",
    "lv_font_montserrat_46.c",
    "lv_font_montserrat_48.c",
}

COPY_LIBS = [
    "Adafruit_BusIO",
    "Adafruit_GFX_Library",
    "Adafruit_ILI9341",
    "HTTPClient",
    "Network",
    "NetworkClientSecure",
    "SPI",
    "WiFi",
    "Wire",
    "XPT2046_Touchscreen",
]


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if r.returncode != 0:
        sys.stderr.write(r.stdout.decode("utf-8", "replace"))
        raise SystemExit(r.returncode)
    return r


def compile_cpp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    run([GXX, f"@{SDK}/flags/cpp_flags", *COMMON, src, "-o", dst])


def compile_c(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    run([GCC, f"@{SDK}/flags/c_flags", *COMMON, src, "-o", dst])


def skip_lvgl(path: str) -> bool:
    rel = os.path.relpath(path, os.path.join(LVGL, "src"))
    name = os.path.basename(path)
    if name in SKIP_FILE:
        return True
    low = rel.replace("/", os.sep)
    for part in SKIP_DIR:
        if part in low:
            return True
    return False


def lvgl_sources():
    src_root = os.path.join(LVGL, "src")
    out = []
    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d not in ("arm2d", "nxp", "sdl", "stm32_dma2d", "swm341_dma2d", "renesas")]
        for name in files:
            if name.endswith(".c"):
                path = os.path.join(root, name)
                if not skip_lvgl(path):
                    out.append(path)
    return out


def copy_old_libs():
    src_lib = os.path.join(ATOM, "libraries")
    dst_lib = os.path.join(BUILD, "libraries")
    os.makedirs(dst_lib, exist_ok=True)
    n = 0
    for lib in COPY_LIBS:
        s = os.path.join(src_lib, lib)
        d = os.path.join(dst_lib, lib)
        if not os.path.isdir(s):
            print("will compile", lib)
            continue
        os.makedirs(d, exist_ok=True)
        for root, _, files in os.walk(s):
            for name in files:
                if name.endswith(".o"):
                    rel = os.path.relpath(os.path.join(root, name), s)
                    dest = os.path.join(d, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(os.path.join(root, name), dest)
                    n += 1
    core_src = os.path.join(ATOM, "core", "core.a")
    core_dst = os.path.join(BUILD, "core", "core.a")
    os.makedirs(os.path.dirname(core_dst), exist_ok=True)
    shutil.copy2(core_src, core_dst)
    print("copied", n, "lib objs + core.a")


def extra_sources():
    roots = [
        ("spi", os.path.join(HW, "libraries", "SPI", "src")),
        ("wire", os.path.join(HW, "libraries", "Wire", "src")),
        ("fs", os.path.join(HW, "libraries", "FS", "src")),
        ("mdns", os.path.join(HW, "libraries", "ESPmDNS", "src")),
        ("gfx", os.path.join(ROOT, "libs", "Adafruit_GFX_Library")),
        ("busio", os.path.join(ROOT, "libs", "Adafruit_BusIO")),
        ("ili", os.path.join(ROOT, "libs", "Adafruit_ILI9341")),
        ("touch", os.path.join(ROOT, "libs", "XPT2046_Touchscreen")),
    ]
    skip = ("examples", "example", "test", "extras")
    out = []
    for tag, base in roots:
        if not os.path.isdir(base):
            print("missing src", base)
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d.lower() not in skip]
            for name in files:
                if name.endswith((".c", ".cpp")):
                    src = os.path.join(root, name)
                    rel = os.path.relpath(src, base)
                    dst = os.path.join(BUILD, "extra", tag, rel + ".o")
                    kind = "cpp" if name.endswith(".cpp") else "c"
                    out.append((kind, src, dst))
    return out


def main():
    os.makedirs(os.path.join(BUILD, "sketch"), exist_ok=True)
    src = open(INO, encoding="utf-8").read()
    with open(SKETCH_CPP, "w", encoding="utf-8", newline="\n") as f:
        f.write('#line 1 "C:\\\\Users\\\\hudsons\\\\placamarela\\\\companion2\\\\firmware-cyd\\\\atlas_lvgl\\\\atlas_lvgl.ino"\n')
        f.write(src)

    copy_old_libs()

    jobs = []
    sketch_o = os.path.join(BUILD, "sketch", "atlas_lvgl.ino.cpp.o")
    jobs.append(("cpp", SKETCH_CPP, sketch_o))
    jobs.extend(extra_sources())
    for src in lvgl_sources():
        rel = os.path.relpath(src, os.path.join(LVGL, "src"))
        dst = os.path.join(BUILD, "libraries", "lvgl", rel + ".o")
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        jobs.append(("c", src, dst))

    print("compile jobs", len(jobs))
    failed = None
    workers = max(2, min(8, os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {}
        for kind, src, dst in jobs:
            fn = compile_cpp if kind == "cpp" else compile_c
            futs[ex.submit(fn, src, dst)] = src
        done = 0
        for fut in as_completed(futs):
            done += 1
            src = futs[fut]
            try:
                fut.result()
            except SystemExit as e:
                failed = (src, e.code)
                print("FAIL", src)
                break
            except Exception as e:
                failed = (src, e)
                print("FAIL", src, e)
                break
            if done % 10 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)} {os.path.basename(src)}")
    if failed:
        sys.exit(1)

    objs = [sketch_o]
    for folder in ("libraries", "extra"):
        base = os.path.join(BUILD, folder)
        if not os.path.isdir(base):
            continue
        for root, _, files in os.walk(base):
            for name in files:
                if name.endswith(".o"):
                    objs.append(os.path.join(root, name))
    core = os.path.join(BUILD, "core", "core.a")
    elf = os.path.join(BUILD, "atlas_lvgl.ino.elf")
    cmd = [
        GXX,
        f"-Wl,--Map={BUILD}/atlas_lvgl.ino.map",
        f"-L{SDK}/lib",
        f"-L{SDK}/ld",
        f"-L{SDK}/qio_qspi",
        f"@{SDK}/flags/ld_flags",
        f"@{SDK}/flags/ld_scripts",
        "-Wl,--start-group",
        *objs,
        core,
        f"@{SDK}/flags/ld_libs",
        "-Wl,--end-group",
        "-Wl,-EL",
        "-o",
        elf,
    ]
    print("linking", len(objs), "objs")
    run(cmd)
    bin_path = os.path.join(BUILD, "atlas_lvgl.ino.bin")
    run(
        [
            ESPTOOL,
            "--chip",
            "esp32",
            "elf2image",
            "--flash_mode",
            "dio",
            "--flash_freq",
            "80m",
            "--flash_size",
            "4MB",
            "--elf-sha256-offset",
            "0xb0",
            "-o",
            bin_path,
            elf,
        ]
    )
    size = os.path.getsize(bin_path)
    print("BIN", size, bin_path)
    if size > 0x300000:
        print("TOO BIG for huge_app")
        sys.exit(2)
    if "--flash" in sys.argv:
        port = "COM5"
        for a in sys.argv:
            if a.startswith("COM"):
                port = a
        boot = os.path.join(ATOM, "atom_echo_arduino.ino.bootloader.bin")
        parts = os.path.join(BUILD, "huge_app.partitions.bin")
        run([GENPART, "-q", os.path.join(HW, "tools", "partitions", "huge_app.csv"), parts])
        boot0 = os.path.join(HW, "tools", "partitions", "boot_app0.bin")
        run(
            [
                ESPTOOL,
                "--chip",
                "esp32",
                "--port",
                port,
                "--baud",
                "921600",
                "--before",
                "default_reset",
                "--after",
                "hard_reset",
                "write_flash",
                "-z",
                "--flash_mode",
                "dio",
                "--flash_freq",
                "80m",
                "--flash_size",
                "4MB",
                "0x1000",
                boot,
                "0x8000",
                parts,
                "0xe000",
                boot0,
                "0x10000",
                bin_path,
            ]
        )
        print("FLASH_OK", port)


if __name__ == "__main__":
    main()
