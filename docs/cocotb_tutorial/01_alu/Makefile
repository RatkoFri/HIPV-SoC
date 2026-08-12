# Standalone cocotb makefile for the tiny_alu example.
#
#   make            run the tests
#   make WAVES=1    also dump dump.vcd
#   make clean

SIM           ?= verilator
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES = $(PWD)/tiny_alu.sv
TOPLEVEL        = tiny_alu
MODULE          = test_tiny_alu

WAVES ?= 0
ifeq ($(WAVES),1)
  EXTRA_ARGS += --trace --trace-structs
endif
EXTRA_ARGS += -Wall

include $(shell cocotb-config --makefiles)/Makefile.sim
