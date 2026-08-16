# SoC address map for testbenches. Mirrors config/hipv_soc_pkg.sv.
#
# Keep in step with the package: the decoder test checks the extents of
# every region listed here.

MASTER_D = 0
MASTER_I = 1

SLAVE = {
    "IMEM": 0,
    "DMEM": 1,
    "UART": 2,
    "TIMER": 3,
    "GPIO": 4,
}

NUM_MASTERS = 2
NUM_SLAVES = len(SLAVE)

# name -> (base, size)
REGIONS = {
    "IMEM": (0x0000_0000, 0x0001_0000),
    "DMEM": (0x1000_0000, 0x0001_0000),
    "UART": (0x2000_0000, 0x0000_1000),
    "TIMER": (0x2000_1000, 0x0000_1000),
    "GPIO": (0x2000_2000, 0x0000_1000),
}

ARB_FIXED = 0
ARB_ROUND_ROBIN = 1


def base(name):
    return REGIONS[name][0]
