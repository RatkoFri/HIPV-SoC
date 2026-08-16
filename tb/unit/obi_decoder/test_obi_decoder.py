# cocotb testbench for obi_decoder (SoC address decode).

import cocotb
from cocotb.triggers import Timer

from socmap import SLAVE, REGIONS


async def decode(dut, addr):
    dut.Addr.value = addr
    await Timer(1, unit="ns")
    return int(dut.SlaveSel.value), int(dut.DecErr.value)


@cocotb.test()
async def test_region_bases(dut):
    """The base address of each region selects exactly that slave."""
    for name, (base, size) in REGIONS.items():
        sel, err = await decode(dut, base)
        assert err == 0, f"{name} base decoded as error"
        assert sel == 1 << SLAVE[name], \
            f"{name}: sel={sel:05b}, expected bit {SLAVE[name]}"


@cocotb.test()
async def test_region_extents(dut):
    """First and last address of every region hit, one past does not."""
    for name, (base, size) in REGIONS.items():
        for addr in (base, base + 4, base + size - 4):
            sel, err = await decode(dut, addr)
            assert err == 0 and sel == 1 << SLAVE[name], \
                f"{name}: {hex(addr)} not in region"
        # one past the end must not select this slave
        sel, _ = await decode(dut, base + size)
        assert not (sel & (1 << SLAVE[name])), \
            f"{name}: {hex(base + size)} still selects the region"


@cocotb.test()
async def test_onehot(dut):
    """The select is always one-hot or all-zero: regions never overlap."""
    for name, (base, size) in REGIONS.items():
        for addr in (base, base + size // 2, base + size - 4):
            sel, _ = await decode(dut, addr)
            assert bin(sel).count("1") == 1, \
                f"{hex(addr)}: sel={sel:05b} is not one-hot"


@cocotb.test()
async def test_unmapped(dut):
    """Addresses outside every region raise DecErr with no select."""
    holes = [0x0001_0000,   # just past IMEM
             0x0FFF_FFFC,   # below DMEM
             0x1001_0000,   # just past DMEM
             0x2000_3000,   # just past GPIO
             0xFFFF_FFFC]   # top of memory
    for addr in holes:
        sel, err = await decode(dut, addr)
        assert err == 1 and sel == 0, \
            f"{hex(addr)}: sel={sel:05b} err={err}, expected an error"
