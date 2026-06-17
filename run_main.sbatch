#!/bin/bash
#SBATCH --job-name=spacialmine_main
#SBATCH --output=logs/main_%j.out
#SBATCH --error=logs/main_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --gpus-per-node=1
#SBATCH --mem=64G
#SBATCH --time=15:30:00
#SBATCH --partition=q_intel_share_L20

set -euo pipefail

module load cuda/12.9

cd /mnt/home/user42/ChillyHigh/SpacialMine/SpacialMine

mkdir -p logs recordings

echo "job node: $(hostname)"
echo "workdir: $(pwd)"

scripts/run_main.sh
