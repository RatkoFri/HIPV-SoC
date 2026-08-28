#!/usr/bin/env python3
"""Flatten the HIPV RTL into a scratch Anvil project and run the flow.

Everything is assembled into ONE temporary project directory that is
**wiped at the start of every run**, so a build can never pick up stale
Verilog from a previous one. Nothing in it is meant to be edited or
committed; the sources of truth stay in rtl/, fpga/anvil/ and sw/.

Why flatten:

  * Anvil collects sources with os.listdir, not a directory walk, so a
    nested tree like rtl/core/ifu/ is invisible to it. Flat is the only
    layout it can see.
  * Anvil converts each .sv with its own sv2v invocation, and a file
    holding `import hipv_pkg::*;` has no package in scope when converted
    alone. This script instead runs sv2v ONCE over the whole design, so
    packages resolve, and hands Anvil finished .v files.

With everything flat and already converted, no Anvil modules or
`installmodule` steps are needed: the project root holds plain Verilog,
which Anvil uses as-is.

Layout produced (default build/anvil-work/):

    top.v                    converted board wrapper
    <every other module>.v   converted RTL, flat
    firmware.hex             program image baked in by $readmemh
    config.json              copied, with an empty module list
    *.xdc                    pin constraints

Usage:
    scripts/anvil_flow.py build            # flatten, convert, anvil build
    scripts/anvil_flow.py program          # ... then flash the board
    scripts/anvil_flow.py prepare          # stop after flattening
    scripts/anvil_flow.py build --firmware sw/examples/hello/build/hello.hex
    scripts/anvil_flow.py build --keep     # do not wipe first (debugging)
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PROJECT = os.path.join(ROOT, "fpga", "anvil")     # source project files
DEFAULT_WORK = os.path.join(ROOT, "build", "anvil-work")

# Packages first: sv2v needs them in the same invocation to resolve
# imports. They produce no module of their own — their constants are
# inlined into every importer.
PACKAGES = [
    "config/hipv_pkg.sv",
    "config/hipv_soc_pkg.sv",
]

# Every synthesisable module, in dependency-friendly order (order does
# not matter to sv2v, but it keeps the listing readable).
RTL = [
    # generic leaf cells
    "rtl/generic/flopenr.sv",
    "rtl/generic/mux2.sv",
    "rtl/generic/mux3.sv",
    "rtl/generic/adder.sv",
    # std-lib primitives used by the peripheral cores
    "rtl/stdlib/register.sv",
    "rtl/stdlib/register_wclear.sv",
    "rtl/stdlib/cntr.sv",
    # unified memory
    "rtl/mem/sync_dual_port_RAM.sv",
    "rtl/mem/obi_ram_port.sv",
    "rtl/mem/obi_ram.sv",
    # core
    "rtl/core/regfile/regfile.sv",
    "rtl/core/ifu/ifuctrl.sv",
    "rtl/core/ifu/ifu.sv",
    "rtl/core/idu/extend.sv",
    "rtl/core/idu/idudec.sv",
    "rtl/core/idu/idu.sv",
    "rtl/core/ieu/alu.sv",
    "rtl/core/ieu/branchcmp.sv",
    "rtl/core/ieu/ieu.sv",
    "rtl/core/lsu/lsu.sv",
    "rtl/core/wbu/wbu.sv",
    "rtl/core/hazard/hazard.sv",
    "rtl/core/hipv_core.sv",
    # interconnect
    "rtl/interconnect/obi_decoder.sv",
    "rtl/interconnect/obi_arbiter.sv",
    "rtl/interconnect/obi_xbar.sv",
    # peripherals
    "rtl/periph/obi_uart.sv",
    "rtl/periph/uart_system.sv",
    "rtl/periph/uart.sv",
    "rtl/periph/obi_timer.sv",
    "rtl/periph/timer.sv",
    "rtl/periph/obi_gpio.sv",
    "rtl/periph/gpio.sv",
    # SoC and board wrapper
    "rtl/top/hipv_soc.sv",
    "fpga/anvil/top.sv",
]

DEFAULT_FIRMWARE = "sw/examples/hello/build/hello.hex"


def die(msg):
    sys.exit(f"[ERROR] {msg}")


def find_tool(name, extra=()):
    found = shutil.which(name)
    if found:
        return found
    for cand in extra:
        cand = os.path.expanduser(cand)
        if os.path.isfile(cand):
            return cand
    return None


def check_unique_basenames(paths):
    """Flattening only works if every file has a distinct name."""
    seen = {}
    for p in paths:
        b = os.path.basename(p)
        if b in seen:
            die(f"filename collision when flattening: {b}\n"
                f"        {seen[b]}\n        {p}")
        seen[b] = p


def run(cmd, cwd=None, quiet=False):
    if not quiet:
        print("  $ " + " ".join(cmd) + (f"   (in {cwd})" if cwd else ""))
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        die(f"command failed with exit {result.returncode}: {' '.join(cmd)}")


def prepare(work, firmware, sv2v, keep=False):
    """Wipe the scratch project, flatten, convert, and assemble it."""
    if not keep and os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)
    print(f"scratch project: {work}" + ("  (kept)" if keep else "  (wiped)"))

    sources = [os.path.join(ROOT, f) for f in PACKAGES + RTL]
    missing = [f for f in sources if not os.path.isfile(f)]
    if missing:
        die("missing sources:\n  " + "\n  ".join(missing))
    check_unique_basenames(sources)

    # one sv2v pass over the whole design, straight into the project root
    print(f"sv2v: converting {len(sources)} files in one pass")
    run([sv2v] + sources + ["-w", work])

    produced = sorted(glob.glob(os.path.join(work, "*.v")))
    if not produced:
        die("sv2v produced no .v files; check the sv2v version and flags")

    # A package converts to nothing — its constants are inlined into each
    # importer — so sv2v leaves an empty file behind. Remove exactly
    # those, by name, rather than every empty .v in the directory.
    removed = 0
    for pkg in PACKAGES:
        out = os.path.join(work, os.path.splitext(os.path.basename(pkg))[0] + ".v")
        if os.path.isfile(out) and os.path.getsize(out) == 0:
            os.remove(out)
            removed += 1

    # An empty output for anything else means the conversion went wrong.
    for p in sorted(glob.glob(os.path.join(work, "*.v"))):
        if os.path.getsize(p) == 0:
            die(f"sv2v produced an empty {os.path.basename(p)} — expected a module")

    kept = len(glob.glob(os.path.join(work, "*.v")))
    print(f"  {kept} Verilog modules"
          + (f", {removed} empty package file(s) removed" if removed else ""))

    if not os.path.isfile(os.path.join(work, "top.v")):
        die("top.v was not produced — sv2v may name outputs differently")

    # project files: config with no modules (everything is in the root)
    with open(os.path.join(PROJECT, "config.json")) as f:
        config = json.load(f)
    config["modules"] = []
    with open(os.path.join(work, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    for xdc in glob.glob(os.path.join(PROJECT, "*.xdc")):
        shutil.copy(xdc, work)
    common = os.path.join(PROJECT, "common")
    if os.path.isdir(common):
        shutil.copytree(common, os.path.join(work, "common"), dirs_exist_ok=True)

    # firmware image baked in by $readmemh at elaboration
    fw = firmware if os.path.isabs(firmware) else os.path.join(ROOT, firmware)
    if not os.path.isfile(fw):
        die(f"firmware image not found: {fw}\n"
            f"        Build one first, e.g.\n"
            f"        make -C sw/examples/hello")
    shutil.copy(fw, os.path.join(work, "firmware.hex"))
    print(f"  firmware: {os.path.relpath(fw, ROOT)} -> firmware.hex")

    return work


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", nargs="?", default="build",
                    choices=["prepare", "build", "program", "clean"],
                    help="prepare: flatten only; build: + anvil build; "
                         "program: + anvil program; clean: remove the scratch dir")
    ap.add_argument("--work", default=DEFAULT_WORK,
                    help="scratch project directory (wiped every run)")
    ap.add_argument("--firmware", default=DEFAULT_FIRMWARE,
                    help="program image to bake in (default: %(default)s)")
    ap.add_argument("--sv2v", help="path to sv2v")
    ap.add_argument("--anvil", help="path to anvil")
    ap.add_argument("--keep", action="store_true",
                    help="do not wipe the scratch dir first (debugging)")
    args = ap.parse_args()

    if args.action == "clean":
        if os.path.isdir(args.work):
            shutil.rmtree(args.work)
            print(f"removed {args.work}")
        else:
            print("nothing to clean")
        return

    sv2v = args.sv2v or find_tool("sv2v", ["~/opt/sv2v/sv2v"])
    if not sv2v:
        die("sv2v not found. Install it (see the Anvil docs) or pass --sv2v.")

    work = prepare(args.work, args.firmware, sv2v, keep=args.keep)

    if args.action == "prepare":
        print(f"\nprepared. To build by hand:\n  cd {os.path.relpath(work)} "
              f"&& anvil build")
        return

    anvil = args.anvil or find_tool("anvil", ["~/opt/anvil/anvil.py"])
    if not anvil:
        die("anvil not found on PATH. Install it or pass --anvil.")

    cmd = [anvil] if os.access(anvil, os.X_OK) else [sys.executable, anvil]
    print("\nanvil build")
    run(cmd + ["build"], cwd=work)

    if args.action == "program":
        print("\nanvil program")
        run(cmd + ["program"], cwd=work)

    bit = glob.glob(os.path.join(work, "build", "*", "top.bit"))
    if bit:
        print(f"\nbitstream: {os.path.relpath(bit[0], ROOT)}")


if __name__ == "__main__":
    main()
