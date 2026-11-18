# Nexys A7-50T constraints for the HIPV SoC.
#
# The Nexys A7-50T and A7-100T are the same baseboard with a smaller
# Artix-7 die, so every pin assignment here is identical to
# Nexys-A7-100T-Master.xdc (verified against Anvil's own stock
# xdc/Nexys-A7-50T-Master.xdc template); only the device/part in
# config.json differ. Keep this file in sync with the 100T one if the
# board wrapper's port list changes.

## Clock: this pin is the Nexys A7's 100 MHz on-board oscillator,
## constrained here at its true physical rate. top.sv divides it down
## to the SoC's real 25 MHz operating clock (SocClk) with a fabric FSM
## (see top.sv); CPU_HZ in sw/rules.mk must match that 25 MHz, not this
## port's rate. This toolchain's XDC-to-SDC conversion does not follow
## a clock through that divider register, so SocClk's own domain isn't
## independently re-verified by this constraint -- see KnownBugs.md,
## BUG-CLOCK, for the cross-validation this relies on instead.
set_property PACKAGE_PIN E3  [get_ports {clk}]
set_property IOSTANDARD LVCMOS33 [get_ports {clk}]
create_clock -period 10.00 -name sys_clk [get_ports {clk}]

## Reset: CPU_RESETN push button (active low)
set_property PACKAGE_PIN C12 [get_ports {cpu_resetn}]
set_property IOSTANDARD LVCMOS33 [get_ports {cpu_resetn}]

## UART over the USB-serial bridge.
## Digilent names these from the bridge's point of view:
##   UART_RXD_OUT (D4) is driven BY the FPGA  -> our uart_tx
##   UART_TXD_IN  (C4) is driven TO the FPGA  -> our uart_rx
set_property PACKAGE_PIN D4  [get_ports {uart_tx}]
set_property IOSTANDARD LVCMOS33 [get_ports {uart_tx}]
set_property PACKAGE_PIN C4  [get_ports {uart_rx}]
set_property IOSTANDARD LVCMOS33 [get_ports {uart_rx}]

## Slide switches -> GPIO inputs
set_property PACKAGE_PIN J15 [get_ports {sw[0]}]
set_property PACKAGE_PIN L16 [get_ports {sw[1]}]
set_property PACKAGE_PIN M13 [get_ports {sw[2]}]
set_property PACKAGE_PIN R15 [get_ports {sw[3]}]
set_property PACKAGE_PIN R17 [get_ports {sw[4]}]
set_property PACKAGE_PIN T18 [get_ports {sw[5]}]
set_property PACKAGE_PIN U18 [get_ports {sw[6]}]
set_property PACKAGE_PIN R13 [get_ports {sw[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[6]}]
set_property IOSTANDARD LVCMOS33 [get_ports {sw[7]}]

## LEDs <- GPIO outputs
set_property PACKAGE_PIN H17 [get_ports {led[0]}]
set_property PACKAGE_PIN K15 [get_ports {led[1]}]
set_property PACKAGE_PIN J13 [get_ports {led[2]}]
set_property PACKAGE_PIN N14 [get_ports {led[3]}]
set_property PACKAGE_PIN R18 [get_ports {led[4]}]
set_property PACKAGE_PIN V17 [get_ports {led[5]}]
set_property PACKAGE_PIN U17 [get_ports {led[6]}]
set_property PACKAGE_PIN U16 [get_ports {led[7]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[0]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[1]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[2]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[4]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[5]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[6]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led[7]}]

## Timer compare match on LED8
set_property PACKAGE_PIN V16 [get_ports {led_timer}]
set_property IOSTANDARD LVCMOS33 [get_ports {led_timer}]
