# CreatorClaw

**NVIDIA "Hack to Create" Hackathon · GTC 2026**

---

## The Vision

**ClawMarket** is an open marketplace for creators — a platform where AI-powered creative tools for image generation, video creation, character design, and more can be published, discovered, and used by anyone.

**CreatorClaw** is the first app on that platform.

---

## CreatorClaw — AI Comic Generator

Give it a story idea. Get back a fully illustrated comic book page.

CreatorClaw uses a chain of local AI models to script your idea into panels, generate artwork for each one, and assemble everything into a finished comic — complete with speech bubbles, captions, and a title. No cloud, no API keys, no limits. Everything runs on the NVIDIA GB10.

**How it works:**
1. You type a story idea
2. Nemotron-30B writes the comic script — panels, dialogue, captions
3. FLUX.2-klein generates the artwork for each panel
4. Qwen3-VL checks each image matches its scene
5. The compositor assembles the final page as PNG and PDF

---

## Tech Stack

| | |
|---|---|
| Story scripting | Nemotron-Nano-30B (NVIDIA) via llama.cpp |
| Image generation | FLUX.2-klein-4B via HuggingFace Diffusers |
| Visual QA | Qwen3-VL-2B via llama-mtmd-cli |
| UI | Gradio |
| Hardware | NVIDIA GB10 · 120GB VRAM · fully local |

---

## Repo Structure

```
creatorclaw/   ← the comic generator app
clawmarket/    ← the creator marketplace platform
```
