# Top-level convenience wrapper: compile a software example, run the
# F4PGA (Anvil) flow with it baked in, and program the board.
#
# Usage:
#   make APP=hello sw        # compile sw/examples/hello
#   make APP=hello fpga      # sw, then flatten/sv2v/anvil build with that firmware
#   make APP=hello program   # flash the board with the existing build (no rebuild)
#   make APP=hello all       # sw -> fpga -> program
#
# APP names a directory under sw/examples/ (default: hello).

APP ?= blink

SW_DIR     := sw/examples/$(APP)
FIRMWARE   := $(SW_DIR)/build/$(APP).hex
ANVIL_FLOW := scripts/anvil_flow.py

.PHONY: all sw fpga program clean

all: sw fpga program

sw:
	$(MAKE) -C $(SW_DIR)

fpga: sw
	python3 $(ANVIL_FLOW) build --firmware $(FIRMWARE)

program:
	python3 $(ANVIL_FLOW) program

clean:
	$(MAKE) -C $(SW_DIR) clean
	python3 $(ANVIL_FLOW) clean
