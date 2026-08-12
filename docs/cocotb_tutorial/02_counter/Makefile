# Standalone cocotb makefile for the counter example.
#
#   make            run the tests
#   make WAVES=1    also dump dump.vcd
#   make clean

SIM           ?= verilator
TOPLEVEL_LANG ?= verilog

VERILOG_SOURCES = $(PWD)/counter.sv
TOPLEVEL        = counter
MODULE          = test_counter

WAVES ?= 0
ifeq ($(WAVES),1)
  EXTRA_ARGS += --trace --trace-structs
endif
EXTRA_ARGS += -Wall

COCOTB_HDL_TIMEUNIT      = 1ns
COCOTB_HDL_TIMEPRECISION = 1ps

include $(shell cocotb-config --makefiles)/Makefile.sim
