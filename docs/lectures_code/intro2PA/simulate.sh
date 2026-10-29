#!/bin/bash

# Define the testbench file
TB_DES="mux_tb"

iverilog -g2012 -o $TB_DES.out $TB_DES.sv
./$TB_DES.out

#gtkwave 