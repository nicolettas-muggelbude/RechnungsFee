SHELL := /bin/bash
.DEFAULT_GOAL := help

PYTHON ?= python3.12
NPM ?= npm
CARGO ?= cargo
PYTHON_PLUGIN := examples/plugins/python-kundenpruefung
PLUGIN_PYTHON := $(abspath $(PYTHON_PLUGIN)/.venv/bin/python)
BACKEND := src/backend
FRONTEND := src/frontend
VENV := $(BACKEND)/.venv
BACKEND_PYTHON := $(abspath $(VENV)/bin/python)
TAURI ?= npx --yes @tauri-apps/cli@^2
BACKEND_PORT ?= 8002
# Vite leitet API-Anfragen standardmäßig an Port 8002 weiter.
PLATFORM := $(shell uname -s)
ifeq ($(PLATFORM),Linux)
BUNDLES ?= appimage
else ifeq ($(PLATFORM),Darwin)
BUNDLES ?= dmg
else
BUNDLES ?= nsis
endif
NO_STRIP ?= true
export NO_STRIP
PYTEST_ARGS ?= -v --tb=short
TAURI_ARGS ?=

.PHONY: help setup setup-backend setup-frontend setup-desktop dev dev-web dev-desktop \
 dev-backend dev-frontend preview build build-dev build-prod build-frontend \
 build-sidecar build-desktop-dev build-desktop-prod test test-backend test-plugins \
 test-rust test-debug lint lint-frontend lint-rust check check-frontend check-rust \
 format-rust plugins-build clean clean-frontend clean-backend clean-rust \
 build\:dev build\:prod build-appimage build\:appimage \
 plugins-python-setup plugins-python-build plugins-python-test

help: ## Alle verfügbaren Befehle anzeigen
	@printf 'RechnungsFee – Entwicklung und Build (Bash / GNU Make)\n\n'
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  make %-23s %s\n", $$1, $$2}' $(firstword $(MAKEFILE_LIST))
	@printf '\nAliase: make build:dev = build-dev; make build:prod = build-prod; make build:appimage = build-appimage\n'
	@printf 'Optionen: PYTHON, BACKEND_PORT, BUNDLES, PYTEST_ARGS, TAURI_ARGS, TAURI, NO_STRIP\n'

setup: setup-backend setup-frontend setup-desktop ## Alle Entwicklungsabhängigkeiten installieren (ohne Systempakete)

$(VENV)/bin/python:
	$(PYTHON) -m venv "$(VENV)"

setup-backend: $(VENV)/bin/python ## Python-venv anlegen und Backend- sowie Testabhängigkeiten installieren
	"$(BACKEND_PYTHON)" -m pip install -r $(BACKEND)/requirements-dev.txt pyinstaller

setup-frontend: ## Frontend-Abhängigkeiten aus dem Lockfile installieren
	$(NPM) --prefix $(FRONTEND) ci

setup-desktop: ## Lokale Tauri-CLI aus dem Root-Lockfile installieren
	$(NPM) ci

dev: dev-web ## Backend und Browser-Frontend gemeinsam starten

dev-web: ## Backend mit Reload und Vite starten; Strg+C beendet beide
	@set -m; \
	backend_pid=; ui_pid=; \
	trap 'trap - EXIT INT TERM; for pid in $$backend_pid $$ui_pid; do kill -- -$$pid 2>/dev/null || true; done; wait 2>/dev/null || true' EXIT; \
	trap 'exit 130' INT; trap 'exit 143' TERM; \
	(cd $(BACKEND) && exec "$(BACKEND_PYTHON)" -m uvicorn main:app --reload --port $(BACKEND_PORT)) & backend_pid=$$!; \
	$(NPM) --prefix $(FRONTEND) run dev & ui_pid=$$!; \
	wait -n $$backend_pid $$ui_pid

dev-desktop: build-sidecar ## Backend mit Reload und Tauri gemeinsam starten (Vite startet automatisch)
	@set -m; \
	backend_pid=; ui_pid=; \
	trap 'trap - EXIT INT TERM; for pid in $$backend_pid $$ui_pid; do kill -- -$$pid 2>/dev/null || true; done; wait 2>/dev/null || true' EXIT; \
	trap 'exit 130' INT; trap 'exit 143' TERM; \
	(cd $(BACKEND) && exec "$(BACKEND_PYTHON)" -m uvicorn main:app --reload --port $(BACKEND_PORT)) & backend_pid=$$!; \
	$(TAURI) dev $(TAURI_ARGS) & ui_pid=$$!; \
	wait -n $$backend_pid $$ui_pid

dev-backend: ## Nur FastAPI mit automatischem Reload starten
	cd $(BACKEND) && "$(BACKEND_PYTHON)" -m uvicorn main:app --reload --port $(BACKEND_PORT)

dev-frontend: ## Nur Vite starten (Port 5173)
	$(NPM) --prefix $(FRONTEND) run dev

preview: ## Gebautes Frontend lokal anzeigen (Backend separat starten)
	$(NPM) --prefix $(FRONTEND) run preview

build: build-prod ## Vollständiges Produktionspaket bauen
build\:dev: build-dev
build\:prod: build-prod
build\:appimage: build-appimage
build-dev: build-desktop-dev ## Desktop-Debug-Build mit frischem Sidecar, ohne Installer
build-prod: build-desktop-prod ## Desktop-Release mit frischem Sidecar und Plattformpaket

build-appimage: ## Linux-AppImage mit frischem Sidecar und Frontend bauen
	@test "$(PLATFORM)" = Linux || { echo 'AppImage-Builds erfordern Linux.' >&2; exit 1; }
	$(MAKE) build-desktop-prod BUNDLES=appimage

build-frontend: ## TypeScript prüfen und Frontend für Produktion bauen
	$(NPM) --prefix $(FRONTEND) run build

build-sidecar: ## Python-Backend mit PyInstaller als Tauri-Sidecar bauen
	@test -x "$(BACKEND_PYTHON)" || { echo 'Bitte zuerst make setup-backend ausführen.' >&2; exit 1; }
	bash scripts/build-sidecar.sh

# Tauri baut das Frontend selbst über beforeBuildCommand; kein doppelter Vite-Build.
build-desktop-dev: build-sidecar ## Tauri im Debug-Modus kompilieren
	$(TAURI) build --debug --no-bundle $(TAURI_ARGS)

build-desktop-prod: build-sidecar ## Tauri-Release und Installer bauen (BUNDLES überschreibbar)
	$(TAURI) build --bundles "$(BUNDLES)" $(TAURI_ARGS)

test: test-backend test-rust ## Backend- und Rust-Tests ausführen

test-backend: ## Gesamte pytest-Suite ausführen (PYTEST_ARGS überschreibbar)
	cd $(BACKEND) && "$(BACKEND_PYTHON)" -m pytest tests/ $(PYTEST_ARGS)

test-plugins: ## Tests für Plugin-Verwaltung, Laufzeit und Ereignisse ausführen
	cd $(BACKEND) && "$(BACKEND_PYTHON)" -m pytest tests/test_plugin_*.py $(PYTEST_ARGS)

test-debug: ## Mitgeliefertes Debug-Plugin testen
	cd $(BACKEND) && "$(BACKEND_PYTHON)" -m pytest tests/test_debug_plugin.py $(PYTEST_ARGS)

test-rust: ## Rust-Tests ausführen (Sidecar und Tauri-Systembibliotheken erforderlich)
	$(CARGO) test --manifest-path src-tauri/Cargo.toml

lint: lint-frontend lint-rust ## Frontend und Rust auf Stilprobleme prüfen
lint-frontend: ## ESLint ausführen
	$(NPM) --prefix $(FRONTEND) run lint
lint-rust: ## Rust-Formatierung prüfen
	$(CARGO) fmt --manifest-path src-tauri/Cargo.toml --check

check: check-frontend check-rust ## TypeScript und Rust statisch prüfen
check-frontend: ## TypeScript ohne Vite-Build prüfen
	cd $(FRONTEND) && $(NPM) exec -- tsc -b
check-rust: ## Rust mit Clippy prüfen (Sidecar und Systembibliotheken erforderlich)
	$(CARGO) clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings
format-rust: ## Rust-Quelltext formatieren
	$(CARGO) fmt --manifest-path src-tauri/Cargo.toml

plugins-python-setup: ## Separate Python-Buildumgebung für das Beispiel-Plugin installieren
	$(PYTHON) -m venv $(PYTHON_PLUGIN)/.venv
	"$(PLUGIN_PYTHON)" -m pip install -r $(PYTHON_PLUGIN)/requirements-build.txt

plugins-python-build: ## Python-Beispiel als Wasm und .rfplugin bauen (vorher plugins-python-setup)
	"$(PLUGIN_PYTHON)" $(PYTHON_PLUGIN)/build.py

plugins-python-test: plugins-python-build ## Python-Beispiel lokal und in der echten Wasm-Sandbox testen
	"$(PLUGIN_PYTHON)" -m unittest discover -s $(PYTHON_PLUGIN) -p test_pruefung.py -v
	"$(BACKEND_PYTHON)" $(PYTHON_PLUGIN)/smoke_test.py

plugins-build: ## Wasm-Test-Fixtures neu bauen (clang, wit-bindgen und wasm-tools erforderlich)
	bash $(BACKEND)/tests/fixtures/plugins/quelle/build.sh

clean: clean-frontend clean-backend clean-rust ## Build-Ausgaben und Caches löschen; venv, node_modules und Nutzerdaten behalten
clean-frontend: ## Frontend-Build und TypeScript-Buildcache löschen
	rm -rf $(FRONTEND)/dist $(FRONTEND)/node_modules/.tmp $(FRONTEND)/node_modules/.vite
clean-backend: ## Python-Test- und Bytecode-Caches löschen (venv ausgenommen)
	find $(BACKEND) -path '$(VENV)' -prune -o -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
clean-rust: ## Rust-Build-Ausgaben löschen
	$(CARGO) clean --manifest-path src-tauri/Cargo.toml
