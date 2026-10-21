# Top-level convenience wrapper: compile a software example, run the
# F4PGA (Anvil) flow with it baked in, and program the board.
#
# Usage:
#   make APP=hello sw        # compile sw/examples/hello
#   make APP=hello fpga      # sw, then flatten/sv2v/anvil build with that firmware
#   make APP=hello program   # flash the board with the existing build (no rebuild)
#   make APP=hello all       # sw -> fpga -> program
#   make program-host        # flash with a host openFPGALoader, bypassing Anvil
#
# The same targets run inside the Docker toolchain image (docker/):
#   make docker-build        # build the image once
#   make docker-shell        # interactive shell, repo at /work
#   make docker-all APP=blink   # any target, prefixed with docker-
#
# APP names a directory under sw/examples/.

APP ?= blink

SW_DIR     := sw/examples/$(APP)
FIRMWARE   := $(SW_DIR)/build/$(APP).hex
ANVIL_FLOW := scripts/anvil_flow.py

BITSTREAM := build/anvil-work/build/nexys4ddr/top.bit
OFL_BOARD := nexys_a7_100

DOCKER_IMAGE ?= hipv-anvil
export HIPV_DOCKER_IMAGE := $(DOCKER_IMAGE)

.PHONY: all sw fpga program program-host clean docker-build docker-shell

all: sw fpga program

sw:
	$(MAKE) -C $(SW_DIR)

fpga: sw
	python3 $(ANVIL_FLOW) build --firmware $(FIRMWARE)

program:
	python3 $(ANVIL_FLOW) program

# For hosts where the toolchain runs in Docker but USB does not reach it
# (Docker Desktop on macOS/Windows). Needs openFPGALoader on the host,
# e.g. `brew install openfpgaloader`.
program-host:
	openFPGALoader -b $(OFL_BOARD) $(BITSTREAM)

clean:
	$(MAKE) -C $(SW_DIR) clean
	python3 $(ANVIL_FLOW) clean

docker-build:
	docker build --platform linux/amd64 \
	    --build-arg HOST_UID=$(shell id -u) --build-arg HOST_GID=$(shell id -g) \
	    -t $(DOCKER_IMAGE) docker

docker-shell:
	docker/run.sh

# docker-<target>: run `make <target>` inside the container
docker-%:
	docker/run.sh make $* APP=$(APP)
