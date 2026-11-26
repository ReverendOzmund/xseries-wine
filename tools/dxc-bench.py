#!/usr/bin/env python3
"""Does DXC's optimiser finish on the compute shaders NVIDIA takes minutes to build?

TuxBox compiles every cs_6_6 program with `dxc -O0` (444368a), because some of
them sit in DXC's optimiser for longer than its 15 s cap. Unoptimised DXIL then
leaves all of that work to the NVIDIA driver at pipeline creation, which is
where runs spend 5-15 minutes per shader.

This takes the slowest pipelines from a run log, translates their recorded Xbox
shaders with the same xshader the game used, and compiles each one with DXC at
-O0 and at the default optimisation. It prints only timings and sizes: no
shader code or game data leaves the machine.

Usage: python3 dxc-bench.py LOG [--top N] [--cap SECONDS]
"""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

TUXBOX = Path.home() / "Downloads/TuxBox"
PREFIXES = Path.home() / ".local/share/project-tuxbox/prefixes"


def slowest(log, top):
    best = {}
    with open(log, "rb") as stream:
        for line in stream:
            for found in re.finditer(rb"CS ([0-9a-f]{8}) finished in ([0-9]+)s", line):
                key, seconds = found.group(1).decode(), int(found.group(2))
                best[key] = max(best.get(key, 0), seconds)
    return sorted(best.items(), key=lambda item: -item[1])[:top]


def request_index():
    """Every recorded Xbox shader request, by the first 8 hex digits of its hash."""
    index = {}
    for path in PREFIXES.glob("*/**/projectscarlett/*/requests/*.dxbc"):
        if re.fullmatch(r"[0-9a-f]{64}", path.stem):
            index.setdefault(path.stem[:8], path)
    return index


def find_xshader():
    if os.environ.get("TUXBOX_XSHADER"):
        return Path(os.environ["TUXBOX_XSHADER"])
    found = sorted(TUXBOX.glob("build/shader-compiler/*/release/xshader"), key=lambda p: p.stat().st_mtime)
    if not found:
        sys.exit("xshader not found under ~/Downloads/TuxBox/build/shader-compiler; launch the game once first")
    return found[-1]


def dxc_once(dxc, profile, hlsl, out, extra, cap):
    started = time.monotonic()
    entry = [] if profile.startswith("lib_") else ["-E", "main"]
    try:
        result = subprocess.run([str(dxc), "-T", profile, *entry, *extra, "-Fo", str(out), str(hlsl)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=cap)
    except subprocess.TimeoutExpired:
        return f">{cap}s", "-"
    seconds = time.monotonic() - started
    if result.returncode or not out.is_file():
        return "error", "-"
    return f"{seconds:.1f}s", f"{out.stat().st_size // 1024} KiB"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--cap", type=int, default=120, help="seconds to give the default optimiser")
    args = parser.parse_args()

    dxc = Path(os.environ.get("DXC", Path.home() / "dxc/bin/dxc"))
    if not dxc.is_file():
        sys.exit(f"DXC not found at {dxc}; set DXC=/path/to/dxc")
    xshader = find_xshader()
    pipelines = slowest(args.log, args.top)
    if not pipelines:
        sys.exit("no 'CS ... finished in Ns' lines in that log")
    index = request_index()
    print(f"xshader {xshader}\ndxc     {dxc}\n{len(index)} recorded shader requests\n")
    print(f"{'CS':8s}  {'driver':>7s}  {'HLSL lines':>10s}  {'-O0':>8s} {'size':>9s}  {'default':>8s} {'size':>9s}")
    for key, driver in pipelines:
        source = index.get(key)
        row = f"{key:8s}  {driver:6d}s"
        if source is None:
            print(f"{row}  request not recorded")
            continue
        with tempfile.TemporaryDirectory(prefix="dxc-bench-") as tmp:
            work = Path(tmp)
            hlsl, profile = work / "shader.hlsl", work / "profile"
            translated = subprocess.run([str(xshader), str(source), "--hlsl-out", str(hlsl), "--profile-out", str(profile)],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            if translated.returncode or not hlsl.is_file():
                print(f"{row}  xshader refused it")
                continue
            target = profile.read_text().strip()
            lines = sum(1 for _ in hlsl.open("rb"))
            o0 = dxc_once(dxc, target, hlsl, work / "o0.cso", ["-O0"], 60)
            opt = dxc_once(dxc, target, hlsl, work / "opt.cso", [], args.cap)
            print(f"{row}  {lines:10d}  {o0[0]:>8s} {o0[1]:>9s}  {opt[0]:>8s} {opt[1]:>9s}  {target}")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
