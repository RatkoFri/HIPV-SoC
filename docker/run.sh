#!/usr/bin/env bash
#
# Start the HIPV container with the repository mounted at /work.
# No arguments opens a shell; otherwise the arguments are run as a command:
#
#   docker/run.sh                       # interactive shell
#   docker/run.sh make fpga APP=blink   # one command, then exit
#
# USB on Linux: the container sees USB devices, including ones plugged in
# after it started. Host /dev is bind-mounted, so new device nodes appear
# live, and the device cgroup allows the character devices involved:
#   189  raw USB (/dev/bus/usb/*), used by openFPGALoader via libusb
#   188  USB-serial (/dev/ttyUSB*), the board's UART console
#   166  CDC-ACM (/dev/ttyACM*)
# This avoids --privileged while still covering any USB board.
#
# Docker Desktop on macOS and Windows runs containers inside a VM with no
# USB passthrough. Build there, then program from the host (make program-host).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${HIPV_DOCKER_IMAGE:-hipv-anvil}"

# the F4PGA conda packages and sv2v binary are x86-64 only
args=(--rm --platform linux/amd64 -v "$ROOT":/work -w /work)
if [ -t 0 ] && [ -t 1 ]; then
  args+=(-it)
fi

case "$(uname -s)" in
  Linux)
    args+=(-v /dev:/dev
           --device-cgroup-rule='c 189:* rmw'
           --device-cgroup-rule='c 188:* rmw'
           --device-cgroup-rule='c 166:* rmw')
    ;;
  *)
    echo "note: Docker on $(uname -s) cannot reach USB devices;" \
         "program the board from the host with 'make program-host'." >&2
    ;;
esac

if [ $# -eq 0 ]; then
  set -- bash
fi

exec docker run "${args[@]}" "$IMAGE" "$@"
