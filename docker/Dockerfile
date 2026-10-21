# syntax=docker/dockerfile:1.6
#
# Anvil + F4PGA (Artix-7) + RISC-V toolchain + openFPGALoader, for
# building HIPV software and bitstreams and programming the board.
#
# Based on Jure Vreča's anvil-docker:
#   https://github.com/jurevreca12/anvil-docker
#
# Changes from upstream:
#   * keeps the RISC-V compiler and openFPGALoader (upstream uses
#     --minimal, which skips both); cocotb/Verilator are still left out
#     because the installer pins cocotb 1.9, while HIPV needs >= 2.0
#   * the in-container user takes the host's UID/GID (build args), so
#     files written to the mounted repo belong to you
#   * the installer is fetched from a pinned upstream commit, checksummed
#
# Build and run through the top-level Makefile:
#   make docker-build
#   make docker-shell

FROM ubuntu:22.04

LABEL description="HIPV SoC: Anvil/F4PGA Artix-7 flow, RISC-V toolchain, openFPGALoader"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    sudo \
    ca-certificates \
    curl \
    wget \
    git \
    unzip \
    xz-utils \
    tar \
    gzip \
    sed \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    gcc \
    g++ \
    make \
    cmake \
    pkg-config \
    flex \
    bison \
    libssl-dev \
    libelf-dev \
    bc \
    pahole \
    libusb-1.0-0-dev \
    libudev-dev \
    libftdi1-dev \
    libhidapi-dev \
    zlib1g-dev \
    iverilog \
    && rm -rf /var/lib/apt/lists/*

# Non-root user with the host's UID/GID. The installer refuses to run as
# root, and `anvil program` calls openFPGALoader through sudo, so the
# user gets passwordless sudo. If the host GID already names a group in
# the image (e.g. 20 = staff on macOS, dialout on Ubuntu), reuse it.
# The installer writes an openFPGALoader udev rule, and that directory
# does not exist without udev (the rule goes unused: the host's apply).
ARG HOST_UID=1000
ARG HOST_GID=1000
RUN if ! getent group "${HOST_GID}" >/dev/null; then \
        groupadd -g "${HOST_GID}" developer; \
    fi \
    && useradd --create-home --shell /bin/bash \
       -u "${HOST_UID}" -g "${HOST_GID}" developer \
    && echo 'developer ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/developer \
    && chmod 0440 /etc/sudoers.d/developer \
    && mkdir -p /etc/udev/rules.d

ENV HOME=/home/developer \
    USER=developer

USER developer
WORKDIR /home/developer

ADD --chown=developer:developer \
    --checksum=sha256:268408073fbfaa0daafdaf4ad2803e3fcf8a7fcf63bd10db1b29d23bb90066a8 \
    https://raw.githubusercontent.com/jurevreca12/anvil-docker/d1108ec3163e96ede8ffdcf6a7b2d9a6a4604ec2/install.sh \
    /home/developer/install.sh

# --no-sim:  skip Verilator + cocotb 1.9 (see above)
# --no-test: skip the integration test, which builds FPGA projects
# The classic conda solver is needed for the legacy F4PGA environment.
RUN chmod +x install.sh \
    && sed -i \
       's/conda env create -f "\$envyml"/conda env create --solver=classic -f "\$envyml"/' \
       install.sh \
    && ./install.sh --no-sim --no-test \
    && rm install.sh

ENV PATH="/home/developer/.local/bin:/home/developer/opt/sv2v:/home/developer/miniconda3/bin:${PATH}"

SHELL ["/bin/bash", "-c"]

# the repository is mounted here by docker/run.sh
WORKDIR /work

CMD ["/bin/bash"]
