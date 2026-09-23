#!/usr/bin/env bash
#SBATCH --job-name=footage-figs
#SBATCH --partition=cpu-small
#SBATCH --account=gts-agarg35
#SBATCH --qos=embers
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=00:45:00
#SBATCH --output=../work/footage_figs-%j.out

set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export HDF5_USE_FILE_LOCKING=FALSE PYTHONUNBUFFERED=1

FFMPEG=/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/lib/python3.10/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2
PY=/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/bin/python

printf 'JOB=%s HOST=%s START=%s\n' "${SLURM_JOB_ID:-}" "$(hostname)" "$(date --iso-8601=seconds)"
exec "$PY" "$SLURM_SUBMIT_DIR"/footage_figs.py --stage footage
