# Nexys A7-100T constraints for the HIPV SoC.
#
# Pin assignments taken from the Digilent master XDC shipped with Anvil
# (xdc/Nexys-A7-100T-Master.xdc); only the pins this design uses are
# enabled here.

## Clock: the on-board 100 MHz oscillator at E3 drives the SoC directly,
## so the constraint is its real period, 10.00 ns. Software must be built
## with the same frequency (CPU_HZ=100000000, the default in sw/rules.mk).
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
