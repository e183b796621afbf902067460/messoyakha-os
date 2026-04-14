#!/usr/bin/env bash

set -euo pipefail

# -------- configurable vars --------
TA_LIB_VERSION="${TA_LIB_VERSION:-0.6.4}"
PREFIX="${PREFIX:-/usr/local}"
JOBS="${JOBS:-$(nproc)}"
SRC_DIR="/tmp/ta-lib-${TA_LIB_VERSION}/"
ARCHIVE="/tmp/ta-lib-${TA_LIB_VERSION}-src.tar.gz"
# -----------------------------------

log() { printf "\e[36m[build-ta-lib] %s\e[0m\n" "$*"; }

install_build_deps() {
  local pkgs=(
    build-essential autoconf automake libtool
    wget curl unzip ca-certificates
  )
  log "Installing build dependencies…"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${pkgs[@]}"
}

download_source() {
  [[ -d "$SRC_DIR" ]] && return
  log "Fetching ta-lib source ($TA_LIB_VERSION)…"
  curl -L "https://github.com/ta-lib/ta-lib/releases/download/v${TA_LIB_VERSION}/ta-lib-${TA_LIB_VERSION}-src.tar.gz" -o "$ARCHIVE"
  tar -xzf "$ARCHIVE" --directory=/tmp
  rm -f "$ARCHIVE"
}

build_and_install() {
  log "Configuring…"
  cd "$SRC_DIR"
  ./configure --prefix="$PREFIX"
  log "Compiling…"
  make
  log "Installing to $PREFIX… (requires root)"
  make install
  rm -rf "$SRC_DIR"
}

main() {
  install_build_deps
  download_source
  build_and_install
  log "TA-Lib $(grep 'AC_INIT' -m1 configure.ac | cut -d'[' -f2 | cut -d']' -f1) installed to $PREFIX"
}

main "$@"
