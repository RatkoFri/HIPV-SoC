# Top-level convenience wrapper: compile a software example, run the
# F4PGA (Anvil) flow with it baked in, and program the board.
#
# Usage:
#   make APP=hello sw                  # compile sw/examples/hello
#   make APP=hello fpga                # sw, then flatten/sv2v/anvil build with that firmware
#   make APP=hello program             # flash the board with the existing build (no rebuild)
#   make APP=hello all                 # sw -> fpga -> program
#   make APP=hw1/check all             # same, for sw/hw1/check (the homework self-check)
#   make APP=hw1/check BONUS=1 all     # ... its bonus variant
#   make APP=hw1/bench all             # sw/hw1/bench, the cycle-count benchmark
#   make BOARD=nexys-50t all           # same, targeting the Nexys A7-50T instead of the 100T
#   make program-nexys100t             # sw -> fpga -> program for the Nexys A7-100T
#   make program-nexys50t              # sw -> fpga -> program for the Nexys A7-50T
#   make program-host                  # flash with a host openFPGALoader, bypassing Anvil
#
# BOARD selects the target device: nexys-100t (default) or nexys-50t. It
# is forwarded to anvil_flow.py --board, which looks up the matching
# part/constraints in Anvil's boards.json.
#
# The same targets run inside the Docker toolchain image (docker/):
#   make docker-build        # build the image once
#   make docker-shell        # interactive shell, repo at /work
#   make docker-all APP=blink   # any target, prefixed with docker-
#
# APP names a directory under sw/examples/, or hw1/check / hw1/bench for
# the sw/hw1/ homework programs (whose directory and output filename
# don't follow the sw/examples/<APP>/<APP>.hex convention).

APP   ?= blink
BOARD ?= nexys-100t
BONUS ?=
REF   ?=

ifeq ($(APP),hw1/check)
  SW_DIR   := sw/hw1/check
  FIRMWARE := $(SW_DIR)/build$(if $(filter 1,$(BONUS)),-bonus)$(if $(filter 1,$(REF)),-ref)/hw1_check.hex
else ifeq ($(APP),hw1/bench)
  SW_DIR   := sw/hw1/bench
  FIRMWARE := $(SW_DIR)/build$(if $(filter 1,$(REF)),-ref)/hw1_bench.hex
else
  SW_DIR   := sw/examples/$(APP)
  FIRMWARE := $(SW_DIR)/build/$(APP).hex
endif
ANVIL_FLOW := scripts/anvil_flow.py

# Anvil target directory and openFPGALoader board name per BOARD, for
# program-host (which bypasses Anvil's own config.json entirely).
ifeq ($(BOARD),nexys-100t)
  ANVIL_TARGET := nexys4ddr
  OFL_BOARD    := nexys_a7_100
else ifeq ($(BOARD),nexys-50t)
  ANVIL_TARGET := nexys_a7_50t
  OFL_BOARD    := nexys_a7_50
else
  $(error Unknown BOARD '$(BOARD)' -- use nexys-100t or nexys-50t)
endif
BITSTREAM := build/anvil-work/build/$(ANVIL_TARGET)/top.bit

DOCKER_IMAGE ?= hipv-anvil
export HIPV_DOCKER_IMAGE := $(DOCKER_IMAGE)

.PHONY: all sw fpga program program-host program-nexys100t program-nexys50t \
        clean docker-build docker-shell

all: sw fpga program

sw:
	$(MAKE) -C $(SW_DIR) BONUS=$(BONUS) REF=$(REF)

fpga: sw
	python3 $(ANVIL_FLOW) build --firmware $(FIRMWARE) --board $(BOARD)

program:
	python3 $(ANVIL_FLOW) program

# Convenience aliases: build and flash for a specific board regardless of
# the ambient BOARD value.
program-nexys100t:
	$(MAKE) all BOARD=nexys-100t

program-nexys50t:
	$(MAKE) all BOARD=nexys-50t

# For hosts where the toolchain runs in Docker but USB does not reach it
# (Docker Desktop on macOS/Windows). Needs openFPGALoader on the host,
# e.g. `brew install openfpgaloader`.
program-host:
	openFPGALoader -b $(OFL_BOARD) $(BITSTREAM)

clean:
	$(MAKE) -C $(SW_DIR) BONUS=$(BONUS) REF=$(REF) clean
	python3 $(ANVIL_FLOW) clean

docker-build:
	docker build --platform linux/amd64 \
	    --build-arg HOST_UID=$(shell id -u) --build-arg HOST_GID=$(shell id -g) \
	    -t $(DOCKER_IMAGE) docker

docker-shell:
	docker/run.sh

# docker-<target>: run `make <target>` inside the container
docker-%:
	docker/run.sh make $* APP=$(APP) BOARD=$(BOARD) BONUS=$(BONUS) REF=$(REF)
