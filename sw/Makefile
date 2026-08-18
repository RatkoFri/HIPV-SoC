# Build (and optionally run) every HIPV example.
#
#   make            build all examples
#   make run        build and run each on the SoC testbench
#   make clean
#
# Pass toolchain settings through, e.g.
#   make CROSS=riscv32-unknown-elf- TOOLFLAGS=-B/opt/riscv/bin/

EXAMPLES := $(notdir $(wildcard examples/*))

.PHONY: all run clean $(EXAMPLES)

all: $(EXAMPLES)

$(EXAMPLES):
	@$(MAKE) --no-print-directory -C examples/$@

run:
	@for e in $(EXAMPLES); do \
	    echo "=== $$e ==="; \
	    $(MAKE) --no-print-directory -C examples/$$e run || exit 1; \
	done

clean:
	@for e in $(EXAMPLES); do $(MAKE) --no-print-directory -C examples/$$e clean; done
