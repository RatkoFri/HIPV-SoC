TOPLEVEL_DIR := $(abspath ../..)

# Program image, applied at elaboration through INIT_FILE — the same
# synthesis-time initialization the FPGA flow uses. gen_prog.py builds
# it from the Python assembler in tb/common/rv32i.py.
INIT_FILE ?= $(PWD)/prog.hex
RAM_WORDS ?= 1024

TOPLEVEL = hipv_soc
# MODULE is overridable so `make -C tb/soc MODULE=test_sw` can run an
# arbitrary image built from sw/ instead of the built-in assembly program.
MODULE  ?= test_hipv_soc

VERILOG_SOURCES = $(TOPLEVEL_DIR)/config/periph.vlt \
                  $(TOPLEVEL_DIR)/config/hipv_pkg.sv \
                  $(TOPLEVEL_DIR)/config/hipv_soc_pkg.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/flopenr.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux2.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/mux3.sv \
                  $(TOPLEVEL_DIR)/rtl/generic/adder.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/register_wclear.sv \
                  $(TOPLEVEL_DIR)/rtl/stdlib/cntr.sv \
                  $(TOPLEVEL_DIR)/rtl/mem/sync_dual_port_RAM.sv \
                  $(TOPLEVEL_DIR)/rtl/mem/obi_ram_port.sv \
                  $(TOPLEVEL_DIR)/rtl/mem/obi_ram.sv \
                  $(TOPLEVEL_DIR)/rtl/core/regfile/regfile.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ifu/ifuctrl.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ifu/ifu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/extend.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/idudec.sv \
                  $(TOPLEVEL_DIR)/rtl/core/idu/idu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/alu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/branchcmp.sv \
                  $(TOPLEVEL_DIR)/rtl/core/ieu/ieu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/lsu/lsu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/wbu/wbu.sv \
                  $(TOPLEVEL_DIR)/rtl/core/hazard/hazard.sv \
                  $(TOPLEVEL_DIR)/rtl/core/hipv_core.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_decoder.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_arbiter.sv \
                  $(TOPLEVEL_DIR)/rtl/interconnect/obi_xbar.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_uart.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/uart_system.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/uart.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_timer.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/timer.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/obi_gpio.sv \
                  $(TOPLEVEL_DIR)/rtl/periph/gpio.sv \
                  $(TOPLEVEL_DIR)/rtl/top/hipv_soc.sv

# 1 KiB of RAM keeps elaboration fast for the built-in program; C
# programs from sw/ need the full 64 KiB (RAM_ADDR_WIDTH=14).
RAM_ADDR_WIDTH ?= 10
ARB_POLICY     ?= 0
COMPILE_ARGS += -GRAM_ADDR_WIDTH=$(RAM_ADDR_WIDTH) -GINIT_FILE=\"$(INIT_FILE)\" \
                -GARB_POLICY=$(ARB_POLICY)

# passed through to test_sw.py when running an image built from sw/
export UART_DIV
export RUN_CYCLES
export EXPECT
export EXPECT_FILE

include $(TOPLEVEL_DIR)/tb/common/Makefile.include

# rules after the include so cocotb's `all` stays the default goal
$(INIT_FILE): gen_prog.py
	python3 gen_prog.py $@ $(RAM_WORDS)

$(SIM_BUILD)/Vtop.mk: $(INIT_FILE)

clean::
	@rm -f $(INIT_FILE)
