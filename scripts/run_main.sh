#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v conda >/dev/null 2>&1; then
  CONDA_BIN="$(command -v conda)"
elif [ -x /mnt/data/hpc/support/soft/anaconda3/bin/conda ]; then
  CONDA_BIN="/mnt/data/hpc/support/soft/anaconda3/bin/conda"
else
  echo "conda not found; expected conda on PATH or /mnt/data/hpc/support/soft/anaconda3/bin/conda" >&2
  exit 1
fi

"$CONDA_BIN" shell.bash hook >/tmp/spacialmine_conda_hook.sh
source /tmp/spacialmine_conda_hook.sh
set +u
conda activate minestudio
set -u

export LD_LIBRARY_PATH="$HOME/opt/openssl10/lib:${LD_LIBRARY_PATH:-}"
export HF_ENDPOINT="https://hf-mirror.com"
export PKG_CONFIG_PATH="$CONDA_PREFIX/lib/pkgconfig:$CONDA_PREFIX/share/pkgconfig:${PKG_CONFIG_PATH:-}"

if ! command -v xvfb-run >/dev/null 2>&1; then
  echo "xvfb-run not found; MineStudio launchClient.sh requires it on this server" >&2
  exit 1
fi

if [ ! -x ./.venv/bin/python ]; then
  echo "./.venv/bin/python not found or not executable" >&2
  exit 1
fi

exec ./.venv/bin/python main.py
