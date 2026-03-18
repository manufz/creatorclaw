# CreatorClaw — AI Comic Book Generator

**NVIDIA "Hack to Create" Hackathon @ GTC 2026**

Turn any story idea into a full comic book page in minutes — running 100% locally on the NVIDIA GB10.

## Pipeline

```
Story idea (text)
  → Nemotron-Nano-30B  →  Comic script (JSON: panels, dialogue, captions)
  → FLUX.2-klein-4B    →  Panel images
  → Qwen3-VL-2B        →  Visual QA (optional)
  → Pillow compositor  →  Full comic page (PNG + PDF)
```

## Requirements

- NVIDIA GB10 (or compatible CUDA GPU with sufficient VRAM)
- CUDA 12.x+
- Python 3.10+
- Models pre-downloaded (see below)

### Model paths expected
| Model | Path |
|---|---|
| Nemotron-Nano-30B-A3B Q4_K_M | `~/models/gguf/ggml-org--Nemotron-Nano-3-30B-A3B-GGUF/` |
| FLUX.2-klein-4B | `~/models/llm/black-forest-labs--FLUX.2-klein-4B/` |
| Qwen3-VL-2B Q4_K_M | `~/models/gguf/Qwen--Qwen3-VL-2B-Instruct-GGUF/` |

## Setup

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install diffusers transformers accelerate gradio pillow reportlab
```

## Run

```bash
./start.sh
```

Then open **http://localhost:7860**

## Tech Stack

| Layer | Technology |
|---|---|
| Story LLM | Nemotron-Nano-30B (NVIDIA) via llama.cpp |
| Image Gen | FLUX.2-klein-4B via HuggingFace Diffusers |
| Visual QA | Qwen3-VL-2B via llama-mtmd-cli |
| UI | Gradio 6.9 |
| Compositor | Pillow + ReportLab |
| Hardware | NVIDIA GB10 · 120GB VRAM · CUDA 12.1 |
