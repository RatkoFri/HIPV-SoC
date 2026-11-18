#!/usr/bin/env python3
"""Sanity-check the tools HW1 needs, before touching any RTL.

Checks the same things docs/LectureNotes/HW1.md's "Tools" table lists:
Verilator >= 5.036, cocotb >= 2.0 (+ pytest), and a RISC-V GCC with
`.option arch` support in its assembler. Resolves cocotb the same way
tb/common/Makefile.include does -- preferring VERIF_VENV (default
~/opt/verif) if it has a working cocotb-config -- so this reports
exactly what `make` in tb/** will actually pick up.

Usage:
    python3 scripts/check_setup.py
    python3 scripts/check_setup.py --cross riscv32-unknown-elf-
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

MIN_VERILATOR = (5, 36)
MIN_COCOTB = (2, 0)

CROSS_CANDIDATES = [
    "riscv64-unknown-elf-",
    "riscv32-unknown-elf-",
    "riscv-none-elf-",
]


def ok(msg):
    print(f"  [OK]   {msg}")


def warn(msg):
    print(f"  [WARN] {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")


def parse_version(text):
    m = re.search(r"(\d+)\.(\d+)", text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def apply_verif_venv():
    """Prepend VERIF_VENV/bin to PATH if it has a working cocotb-config --
    the same rule tb/common/Makefile.include applies, so this script sees
    what a real `make` invocation would see."""
    venv = os.environ.get("VERIF_VENV", os.path.expanduser("~/opt/verif"))
    cocotb_config = os.path.join(venv, "bin", "cocotb-config")
    if venv and os.path.isfile(cocotb_config):
        os.environ["PATH"] = os.path.join(venv, "bin") + os.pathsep + os.environ["PATH"]
        return venv
    return None


def check_verilator():
    path = shutil.which("verilator")
    if not path:
        fail("verilator not found on PATH")
        return False
    out = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout
    ver = parse_version(out)
    if ver is None:
        warn(f"verilator found ({path}) but couldn't parse its version: {out.strip()!r}")
        return True
    if ver < MIN_VERILATOR:
        fail(f"verilator {ver[0]}.{ver[1]} at {path} is older than the required "
             f"{MIN_VERILATOR[0]}.{MIN_VERILATOR[1]}")
        return False
    ok(f"verilator {ver[0]}.{ver[1]} ({path})")
    return True


def check_cocotb(venv_used):
    cocotb_config = shutil.which("cocotb-config")
    if not cocotb_config:
        fail("cocotb-config not found on PATH -- cocotb isn't installed/active "
             "(pip install -r requirements.txt into a venv, e.g. ~/opt/verif)")
        return False
    out = subprocess.run(["cocotb-config", "--version"], capture_output=True, text=True).stdout
    ver = parse_version(out)
    where = f" (from {venv_used})" if venv_used else ""
    if ver is None:
        warn(f"cocotb-config found{where} but couldn't parse its version: {out.strip()!r}")
        return True
    if ver < MIN_COCOTB:
        fail(f"cocotb {out.strip()}{where} is older than the required "
             f"{MIN_COCOTB[0]}.{MIN_COCOTB[1]} -- the testbenches use the 2.x API "
             f"(e.g. Clock(unit=...)) and will fail to even start on 1.x")
        return False
    ok(f"cocotb {out.strip()}{where}")
    return True


def check_pytest():
    # Check via the resolved python3 (after the VERIF_VENV PATH prepend),
    # not this script's own interpreter -- they can easily differ, the
    # same way cocotb-config's shebang differs from `python3 check_setup.py`.
    python3 = shutil.which("python3") or sys.executable
    result = subprocess.run([python3, "-c", "import pytest; print(pytest.__version__)"],
                             capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"pytest not importable via {python3} "
             f"(pip install -r requirements.txt into that Python)")
        return False
    ok(f"pytest {result.stdout.strip()} (via {python3})")
    return True


def check_riscv_gcc(cross):
    candidates = [cross] if cross else CROSS_CANDIDATES
    found = None
    for prefix in candidates:
        gcc = shutil.which(prefix + "gcc")
        if gcc:
            found = (prefix, gcc)
            break
    if not found:
        fail("no RISC-V GCC found on PATH (tried: " +
             ", ".join(p + "gcc" for p in candidates) + "). "
             "Set --cross or CROSS to the right prefix.")
        return False
    prefix, gcc = found
    out = subprocess.run([gcc, "--version"], capture_output=True, text=True).stdout
    first_line = out.splitlines()[0] if out else "(no output)"
    ok(f"{prefix}gcc found: {first_line}")

    # The homework specifically needs `.option arch` support in the
    # assembler, to enable Zbb per-function without recompiling libgcc.
    # Not every RISC-V GCC build's binutils is new enough for this.
    src = ('__asm__(".option push\\n.option arch, +zbb\\n'
           'andn a0, a0, a0\\n.option pop\\n");\n')
    with tempfile.TemporaryDirectory() as d:
        src_path = os.path.join(d, "probe.c")
        obj_path = os.path.join(d, "probe.o")
        with open(src_path, "w") as f:
            f.write(src)
        result = subprocess.run(
            [gcc, "-march=rv32i", "-mabi=ilp32", "-c", src_path, "-o", obj_path],
            capture_output=True, text=True)
        if result.returncode != 0:
            fail(f"{prefix}gcc's assembler doesn't accept `.option arch, +zbb` "
                 f"(needed for Task 1): {result.stderr.strip()}")
            return False
    ok(f"{prefix}gcc's assembler accepts `.option arch, +zbb`")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cross", default=os.environ.get("CROSS"),
                     help="RISC-V GCC prefix to check (default: try the usual ones, "
                          "or $CROSS if set)")
    args = ap.parse_args()

    print("Checking your HW1 setup...\n")
    venv_used = apply_verif_venv()
    if venv_used:
        print(f"(using cocotb from VERIF_VENV={venv_used}, same as `make` in tb/**)\n")

    results = [
        check_verilator(),
        check_cocotb(venv_used),
        check_pytest(),
        check_riscv_gcc(args.cross),
    ]

    print()
    if all(results):
        print("All checks passed. Try `cd tb/core && make` next.")
        return 0
    print("Some checks failed -- fix those before starting the homework.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
