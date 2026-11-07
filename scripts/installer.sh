#!/usr/bin/env bash
# Crée l'environnement virtuel .venv et installe propar + le projet (Linux / macOS).
set -euo pipefail
cd "$(dirname "$0")/.."

git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo
echo "Environnement prêt. Pour l'activer :  source .venv/bin/activate"
