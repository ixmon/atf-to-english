#!/bin/bash
# Distilled from the exact command that produced the 28-epoch v12a "near-manual" result.
# Run this (or the equivalent docker run ...) on machines where stock PyTorch CUDA wheels don't work (ARM64/Blackwell etc.).

set -e

MODEL_DIR=${1:-models/atf-en-best-final}
MAX_EPOCHS=${EPOCHS:-50}
PATIENCE=${EARLY_STOPPING_PATIENCE:-5}
LR=${LEARNING_RATE:-3e-4}
BATCH=${BATCH_SIZE:-32}
MAX_LEN=${MAX_LENGTH:-256}

echo "======================================================================"
echo "Long training for best ATF→English quality (tag-free t5-small)"
echo "This is the invocation style used for the 28-epoch v12a result."
echo "======================================================================"

docker run --rm --gpus all \
  --ipc=host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -e TIER=best \
  -e EPOCHS=$MAX_EPOCHS \
  -e EARLY_STOPPING_PATIENCE=$PATIENCE \
  -e LEARNING_RATE=$LR \
  -e BATCH_SIZE=$BATCH \
  -e MAX_LENGTH=$MAX_LEN \
  -v "$(pwd)":/workspace -w /workspace \
  nvcr.io/nvidia/pytorch:25.01-py3 \
  bash -c "
    pip install -q datasets sentencepiece accelerate transformers &&
    python train.py --data data/ebl_pairs.json
  " 2>&1 | tee long_training.log

echo ""
echo "Done. Check long_training.log and the final model in $MODEL_DIR (or the dir you passed)."
echo "Then: python infer.py --model $MODEL_DIR --atf 'your atf here'"
echo "======================================================================"