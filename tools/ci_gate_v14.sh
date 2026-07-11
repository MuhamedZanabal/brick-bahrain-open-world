#!/usr/bin/env bash
set -euo pipefail
python3 tools/ci_runtime_manifest.py
python3 -m py_compile tools/check_godot_log.py tools/verify_ci_artifacts.py tools/ci_generate_parity_matrix.py tools/ci_runtime_manifest.py
