# Reusable OBI slave model for HIPV testbenches.
#
# One outstanding transaction, configurable grant and response latency.
# All driving happens on the falling clock edge so the DUT samples
# cleanly on the rising edge. `mem` is a dict of word-aligned byte
# address -> 32-bit word; writes honour the byte enables.

from cocotb.triggers import FallingEdge


async def obi_slave(clk, mem, req, gnt, addr, rvalid, rdata,
                    we=None, be=None, wdata=None,
                    gnt_delay=0, rvalid_delay=1, default=0):
    gnt.value = 0
    rvalid.value = 0
    resp = None            # [cycles_until_rvalid, data]
    wait = gnt_delay
    while True:
        await FallingEdge(clk)
        # response channel
        if resp is not None and resp[0] == 0:
            rvalid.value = 1
            rdata.value = resp[1]
            resp = None
        else:
            rvalid.value = 0
            if resp is not None:
                resp[0] -= 1
        # address channel: grant when no response is pending
        if resp is None and req.value and not gnt.value:
            if wait == 0:
                gnt.value = 1
                a = int(addr.value) & 0xFFFFFFFC
                if we is not None and we.value:
                    old = mem.get(a, 0)
                    ben = int(be.value)
                    mask = 0
                    for i in range(4):
                        if (ben >> i) & 1:
                            mask |= 0xFF << (8 * i)
                    mem[a] = (old & ~mask) | (int(wdata.value) & mask)
                    resp = [rvalid_delay - 1, 0]
                else:
                    resp = [rvalid_delay - 1, mem.get(a, default)]
                wait = gnt_delay
            else:
                wait -= 1
        else:
            gnt.value = 0
