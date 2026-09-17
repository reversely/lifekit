#!/usr/bin/env bash
# Cosmos Reason2 8B served by vLLM in a container on the box, on 127.0.0.1:8010, for the
# video summarization screen. Run once as root; the container restarts with the box.
#   1. Agree to the model terms at https://huggingface.co/nvidia/Cosmos-Reason2-8B
#   2. HF_TOKEN=<token> python3 -c "from huggingface_hub import snapshot_download; snapshot_download('nvidia/Cosmos-Reason2-8B', local_dir='/home/springbuilt/models/Cosmos-Reason2-8B')"
#   3. nvidia-ctk runtime configure --runtime=docker && systemctl restart docker
#   4. bash scripts/cosmos_up.sh
set -euo pipefail
MODELS=${MODELS:-/home/springbuilt/models}
IMAGE=${IMAGE:-nvcr.io/nvidia/vllm:26.08-py3}
docker rm -f cosmos > /dev/null 2>&1 || true
docker run -d --name cosmos --restart unless-stopped --gpus all --ipc=host \
  -p 127.0.0.1:8010:8000 -v "$MODELS:/models:ro" "$IMAGE" \
  vllm serve /models/Cosmos-Reason2-8B --served-model-name cosmos-reason2-8b \
  --max-model-len 16384 --reasoning-parser qwen3 --gpu-memory-utilization 0.35 --port 8000
echo "Cosmos Reason2 8B starts on 127.0.0.1:8010; the API reads LIFEKIT_VISION_URL=http://127.0.0.1:8010/v1 and LIFEKIT_VISION_MODEL=cosmos-reason2-8b from .env.box"
