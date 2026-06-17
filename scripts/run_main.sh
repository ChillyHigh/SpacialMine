#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

/mnt/data/hpc/support/soft/anaconda3/bin/conda shell.bash hook >/tmp/spacialmine_conda_hook.sh
source /tmp/spacialmine_conda_hook.sh
set +u
conda activate minestudio
set -u

export JAVA_HOME="$CONDA_PREFIX"
export PATH="$JAVA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$HOME/opt/openssl10/lib:${LD_LIBRARY_PATH:-}"
export HF_ENDPOINT="https://hf-mirror.com"
export PKG_CONFIG_PATH="$CONDA_PREFIX/lib/pkgconfig:$CONDA_PREFIX/share/pkgconfig:${PKG_CONFIG_PATH:-}"

scripts/patch_minestudio.sh

exec ./.venv/bin/python main.py
