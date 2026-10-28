#!/usr/bin/env bash
# Baut die Test-Plugins in tests/fixtures/plugins/ neu (Phase-0-Spike, docs/plan-plugin-system.md).
# Bewusst in C statt Rust: braucht nur clang (wasm32-Backend) + wit-bindgen + wasm-tools
#   cargo install wasm-tools wit-bindgen-cli
# Echte Plugins werden in Rust mit `cargo component` gebaut - siehe Doku.
set -euo pipefail
cd "$(dirname "$0")"
WIT_PROD=../../../../plugins/wit/rechnungsfee.wit
CFLAGS="--target=wasm32-unknown-unknown -O2 -nostdlib -ffreestanding -Ilibc -mexec-model=reactor -Wl,--no-entry -Wl,--export-dynamic"
tmp=$(mktemp -d); trap 'rm -rf "$tmp" gen genb' EXIT

# Gültiges Plugin gegen die echte WIT-Datei
wit-bindgen c "$WIT_PROD" --world plugin-world --out-dir gen >/dev/null
clang $CFLAGS -o "$tmp/core.wasm" testplugin.c gen/plugin_world.c gen/plugin_world_component_type.o libc/mini_libc.c
wasm-tools component new "$tmp/core.wasm" -o ../testplugin.wasm

# Plugin mit nicht erlaubtem Import (Netzwerk) - WIT = echte WIT + Test-Welt boese-world
wit-bindgen c wit-boese/rechnungsfee.wit --world boese-world --out-dir genb >/dev/null
clang $CFLAGS -o "$tmp/core_b.wasm" boese.c genb/boese_world.c genb/boese_world_component_type.o libc/mini_libc.c
wasm-tools component new "$tmp/core_b.wasm" -o ../boese.wasm

# Reines Wasm-Modul (keine Component)
echo '(module (func (export "hallo")))' | wasm-tools parse -o ../modul.wasm

ls -la ../*.wasm
