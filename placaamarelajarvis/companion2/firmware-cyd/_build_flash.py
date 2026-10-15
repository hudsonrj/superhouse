"""Compile sketch + SD/FS, link, elf2image, optional flash COM15."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
INO = os.path.join(ROOT, "atlas_cyd", "atlas_cyd.ino")
BUILD = os.path.join(ROOT, "atlas_cyd", "build", "esp32.esp32.esp32")
SKETCH_CPP = os.path.join(BUILD, "sketch", "atlas_cyd.ino.cpp")
HW = r"C:\Users\hudsons\AppData\Local\Arduino15\packages\esp32\hardware\esp32\3.3.10"
SDK = r"C:\Users\hudsons\AppData\Local\Arduino15\packages\esp32\tools\esp32-libs\3.3.10"
BINDIR = r"C:\Users\hudsons\AppData\Local\Arduino15\packages\esp32\tools\esp-x32\2601\bin"
ESPTOOL = r"C:\Users\hudsons\AppData\Local\Arduino15\packages\esp32\tools\esptool_py\4.5.1\esptool.exe"
GXX = os.path.join(BINDIR, "xtensa-esp32-elf-g++.exe")
GCC = os.path.join(BINDIR, "xtensa-esp32-elf-gcc.exe")

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
    "-DARDUINO_PARTITION_default",
    '-DARDUINO_HOST_OS="windows"',
    '-DARDUINO_FQBN="esp32:esp32:esp32"',
    "-DESP32=ESP32",
    "-DCORE_DEBUG_LEVEL=0",
    "-DARDUINO_RUNNING_CORE=1",
    "-DARDUINO_EVENT_RUNNING_CORE=1",
    "-DARDUINO_USB_CDC_ON_BOOT=0",
    f"@{SDK}/flags/defines",
    f"-I{os.path.join(ROOT, 'atlas_cyd')}",
    f"-iprefix{SDK}/include/",
    f"@{SDK}/flags/includes",
    f"-I{SDK}/qio_qspi/include",
    f"-I{HW}/cores/esp32",
    f"-I{HW}/variants/esp32",
    f"-I{HW}/libraries/SPI/src",
    f"-I{HW}/libraries/FS/src",
    f"-I{HW}/libraries/SD/src",
    f"-I{HW}/libraries/Preferences/src",
    f"-I{HW}/libraries/WiFi/src",
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


def run(cmd):
    print("+", cmd[0], os.path.basename(cmd[-2]) if len(cmd) > 2 else "")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(r.returncode)


def compile_cpp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    run([GXX, f"@{SDK}/flags/cpp_flags", *COMMON, src, "-o", dst])


def compile_c(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    run([GCC, f"@{SDK}/flags/c_flags", *COMMON, src, "-o", dst])


def main():
    os.makedirs(os.path.join(BUILD, "sketch"), exist_ok=True)
    src = open(INO, encoding="utf-8").read()
    with open(SKETCH_CPP, "w", encoding="utf-8", newline="\n") as f:
        f.write('#line 1 "C:\\\\Users\\\\hudsons\\\\placamarela\\\\companion2\\\\firmware-cyd\\\\atlas_cyd\\\\atlas_cyd.ino"\n')
        f.write(src)
    compile_cpp(SKETCH_CPP, os.path.join(BUILD, "sketch", "atlas_cyd.ino.cpp.o"))

    extras = [
        (f"{HW}/libraries/FS/src/FS.cpp", "libraries/FS/FS.cpp.o", True),
        (f"{HW}/libraries/FS/src/vfs_api.cpp", "libraries/FS/vfs_api.cpp.o", True),
        (f"{HW}/libraries/SD/src/SD.cpp", "libraries/SD/SD.cpp.o", True),
        (f"{HW}/libraries/SD/src/sd_diskio.cpp", "libraries/SD/sd_diskio.cpp.o", True),
        (f"{HW}/libraries/SD/src/sd_diskio_crc.c", "libraries/SD/sd_diskio_crc.c.o", False),
    ]
    for src, rel, is_cpp in extras:
        dst = os.path.join(BUILD, rel)
        if os.path.exists(dst):
            print("skip", rel)
            continue
        if is_cpp:
            compile_cpp(src, dst)
        else:
            compile_c(src, dst)

    objs = [os.path.join(BUILD, "sketch", "atlas_cyd.ino.cpp.o")]
    for root, _, files in os.walk(os.path.join(BUILD, "libraries")):
        for name in files:
            if name.endswith(".o"):
                objs.append(os.path.join(root, name))
    core = os.path.join(BUILD, "core", "core.a")
    elf = os.path.join(BUILD, "atlas_cyd.ino.elf")
    gxx = GXX
    cmd = [
        gxx,
        f"-Wl,--Map={BUILD}/atlas_cyd.ino.map",
        f"-L{SDK}/lib",
        f"-L{SDK}/ld",
        f"-L{SDK}/qio_qspi",
        "-Wl,--wrap=esp_panic_handler",
        "-Wl,--wrap=esp_bt_mem_release",
        "-Wl,--wrap=esp_bt_controller_mem_release",
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
    bin_path = os.path.join(BUILD, "atlas_cyd.ino.bin")
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
    print("BIN", os.path.getsize(bin_path), bin_path)
    if "--flash" in sys.argv:
        run(
            [
                ESPTOOL,
                "--chip",
                "esp32",
                "--port",
                "COM15",
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
                "0x10000",
                bin_path,
            ]
        )
        print("FLASH_OK")


if __name__ == "__main__":
    main()
