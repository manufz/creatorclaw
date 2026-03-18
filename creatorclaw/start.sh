#!/bin/bash
# ============================================================
#  Comic Creator — Start Script
#  Starts Nemotron-30B story server, then launches the Gradio app
# ============================================================
set -e

LLAMA_SERVER="/home/nvidia/llama.cpp/build/bin/llama-server"
NEMOTRON_MODEL="/home/nvidia/models/gguf/ggml-org--Nemotron-Nano-3-30B-A3B-GGUF/Nemotron-Nano-3-30B-A3B-Q4_K_M.gguf"
LLM_PORT=8080
APP_PORT=7860

echo "================================================================"
echo "  Comic Creator — NVIDIA GB10 Hackathon"
echo "================================================================"

# ---- Kill any previous instances ----
pkill -f "llama-server.*$LLM_PORT" 2>/dev/null || true
pkill -f "app.py" 2>/dev/null || true
sleep 1

# ---- Start Nemotron story server ----
echo ""
echo "[1/3] Starting Nemotron-30B story server on port $LLM_PORT ..."
$LLAMA_SERVER \
  -m "$NEMOTRON_MODEL" \
  --port $LLM_PORT \
  --host 0.0.0.0 \
  -ngl 99 \
  -c 8192 \
  --parallel 2 \
  --cont-batching \
  --flash-attn on \
  --jinja \
  --log-disable \
  > /tmp/nemotron_server.log 2>&1 &

LLM_PID=$!
echo "   PID: $LLM_PID — waiting for server to be healthy..."

# Wait up to 120s for server
for i in $(seq 1 60); do
  if curl -s http://localhost:$LLM_PORT/health 2>/dev/null | grep -q "ok"; then
    echo "   ✅ Nemotron server ready!"
    break
  fi
  sleep 2
  if [ $i -eq 60 ]; then
    echo "   ❌ Server failed to start. Check /tmp/nemotron_server.log"
    exit 1
  fi
done

# ---- Check/install diffusers for FLUX (if torch available) ----
echo ""
echo "[2/3] Checking image generation dependencies..."
if python3 -c "import torch; import diffusers" 2>/dev/null; then
  echo "   ✅ torch + diffusers available — FLUX image gen enabled"
else
  echo "   ⚡ Installing diffusers (torch installing in background)..."
  pip3 install diffusers transformers accelerate safetensors \
    --break-system-packages -q 2>/dev/null || true
fi

# ---- Launch Gradio app ----
echo ""
echo "[3/3] Launching Comic Creator UI on port $APP_PORT ..."
echo ""
echo "  Open in browser: http://localhost:$APP_PORT"
echo "  (Or from another machine: http://$(hostname -I | awk '{print $1}'):$APP_PORT)"
echo ""
echo "================================================================"

cd "$(dirname "$0")"
python3 app.py

# Cleanup on exit
trap "kill $LLM_PID 2>/dev/null; echo 'Servers stopped.'" EXIT
