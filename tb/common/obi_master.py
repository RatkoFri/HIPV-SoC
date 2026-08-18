# Simple OBI master driver for slave-unit testbenches.
#
# Drives one transaction on a DUT slave port with the project signal
# names (ObiReq/ObiGnt/ObiAddr/ObiWe/ObiBe/ObiWdata/ObiRvalid/ObiRdata).
# Complements obi.py, which models the *slave* side.

from cocotb.triggers import RisingEdge, FallingEdge, Timer


async def obi_write(dut, addr, data, be=0xF, timeout=20):
    dut.ObiAddr.value = addr
    dut.ObiWe.value = 1
    dut.ObiBe.value = be
    dut.ObiWdata.value = data
    dut.ObiReq.value = 1
    for _ in range(timeout):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if dut.ObiGnt.value:
            break
    else:
        raise AssertionError(f"no grant for write {hex(addr)}")
    await RisingEdge(dut.clk)
    dut.ObiReq.value = 0
    dut.ObiWe.value = 0
    for _ in range(timeout):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if dut.ObiRvalid.value:
            return
    raise AssertionError(f"no response for write {hex(addr)}")


async def obi_read(dut, addr, timeout=20):
    dut.ObiAddr.value = addr
    dut.ObiWe.value = 0
    dut.ObiBe.value = 0xF
    dut.ObiReq.value = 1
    for _ in range(timeout):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if dut.ObiGnt.value:
            break
    else:
        raise AssertionError(f"no grant for read {hex(addr)}")
    await RisingEdge(dut.clk)
    dut.ObiReq.value = 0
    for _ in range(timeout):
        await FallingEdge(dut.clk)
        await Timer(1, unit="ns")
        if dut.ObiRvalid.value:
            return int(dut.ObiRdata.value)
    raise AssertionError(f"no response for read {hex(addr)}")
