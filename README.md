# CreatorClaw

**NVIDIA "Hack to Create" Hackathon · GTC 2026**

---

## What is CreatorClaw?

CreatorClaw is an open platform that puts the full power of AI-driven content creation in the hands of every creator — running entirely locally on the NVIDIA GB10, with no cloud dependency and no data leaving your machine.

It brings together two projects into one unified vision:

---

### 🎨 CreatorClaw — AI Comic & Image Generator

Turn any story idea into a fully illustrated comic book page in minutes. Type a concept, and the pipeline does the rest: a large language model scripts the story into panels with dialogue and captions, a diffusion model generates the artwork, and a compositor assembles everything into a print-ready comic page.

Built on **Nemotron-30B** (story scripting), **FLUX.2-klein** (image generation), and **Qwen3-VL** (visual quality check) — all running locally on the GB10's 120GB unified memory.

---

### 🛒 ClawMarket — Open Marketplace for Creators

A marketplace where creators can publish, discover, share, and monetize AI-powered creative tools — spanning image generation, video creation, character design, and beyond. Creators deploy their tools as companions or skills, others can fork and build on top of them.

Think of it as an app store for the creator economy, built around open, local-first AI.

---

## Why It Matters

The creator economy is massive, but the best AI tools are locked behind cloud APIs, subscription paywalls, and usage limits. CreatorClaw flips that model: the GB10 brings data-center-grade inference to the creator's own machine, and ClawMarket makes the resulting tools accessible and shareable to everyone.

**Create locally. Share openly. Own your work.**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Story LLM | Nemotron-Nano-30B-A3B (NVIDIA) via llama.cpp |
| Image Gen | FLUX.2-klein-4B (Black Forest Labs) via Diffusers |
| Visual QA | Qwen3-VL-2B via llama-mtmd-cli |
| Marketplace | Next.js · Supabase · Stripe · Tailwind CSS |
| UI | Gradio 6.9 · Comic Neue font |
| Compositor | Pillow · ReportLab |
| Hardware | NVIDIA GB10 · 120GB VRAM · CUDA 12.1 |

---

## Structure

```
creatorclaw/   ← AI comic & image generator (Python)
clawmarket/    ← Creator marketplace (Next.js)
```
