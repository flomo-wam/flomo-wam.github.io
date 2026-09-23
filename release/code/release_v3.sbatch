#!/usr/bin/env bash
#SBATCH --job-name=flomo-v3
#SBATCH --partition=cpu-small
#SBATCH --account=gts-agarg35
#SBATCH --qos=embers
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:30:00
#SBATCH --output=../work/v3-%j.out
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUNBUFFERED=1
PY=/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/bin/python
printf 'JOB=%s HOST=%s START=%s\n' "${SLURM_JOB_ID:-}" "$(hostname)" "$(date --iso-8601=seconds)"
exec "$PY" "$SLURM_SUBMIT_DIR"/render.py "$@"
