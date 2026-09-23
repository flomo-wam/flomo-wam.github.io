#!/usr/bin/env bash
#SBATCH --job-name=motion-hc
#SBATCH --partition=cpu-small
#SBATCH --account=gts-agarg35
#SBATCH --qos=embers
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=../work/motion_hc-%j.out

set -euo pipefail
export HDF5_USE_FILE_LOCKING=FALSE
export OMP_NUM_THREADS=1
export PYTHONUNBUFFERED=1

FFMPEG=/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/lib/python3.10/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2
PY=/storage/home/hcoda1/0/sgovil9/.conda/envs/v2r/bin/python
MEDIA="$SLURM_SUBMIT_DIR"/../media

printf 'JOB=%s HOST=%s START=%s ffmpeg=%s py=%s\n' \
  "${SLURM_JOB_ID:-}" "$(hostname)" "$(date --iso-8601=seconds)" "$FFMPEG" "$PY"
exec "$PY" "$SLURM_SUBMIT_DIR"/motion_hc.py \
  --out "$MEDIA/motion" --ffmpeg "$FFMPEG" --workers 8
