"""
Image generation for comic panels.
Primary:  FLUX.2-klein via HuggingFace diffusers (requires torch)
Fallback: Pillow-rendered stylized placeholder
"""
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def _get_font(size: int, bold: bool = False):
    base = Path(__file__).parent / "fonts"
    paths = [
        str(base / ("ComicNeue-Bold.ttf" if bold else "ComicNeue-Regular.ttf")),
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

FLUX_MODEL_PATH = "/home/nvidia/models/llm/black-forest-labs--FLUX.2-klein-4B"
PANEL_W, PANEL_H = 512, 512

# --------------------------------------------------------------------------
# Pillow fallback — comic-style stylized placeholder
# --------------------------------------------------------------------------

def _wrap_text(text: str, max_chars: int = 40) -> list[str]:
    words = text.split()
    lines, line = [], []
    for w in words:
        if sum(len(x) + 1 for x in line) + len(w) > max_chars:
            lines.append(" ".join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(" ".join(line))
    return lines


STYLE_PALETTES = {
    "manga":       {"bg": (245, 240, 220), "fg": (20, 20, 20),  "accent": (180, 20, 20)},
    "american":    {"bg": (255, 252, 235), "fg": (10, 10, 80),  "accent": (200, 50, 0)},
    "watercolor":  {"bg": (230, 245, 255), "fg": (40, 60, 100), "accent": (80, 130, 200)},
    "noir":        {"bg": (30, 30, 30),    "fg": (230, 230, 230),"accent": (200, 180, 50)},
    "cyberpunk":   {"bg": (10, 10, 30),    "fg": (0, 255, 180), "accent": (255, 50, 200)},
}


def pillow_placeholder(prompt: str, panel_num: int, style: str = "manga") -> Image.Image:
    """Generate a styled placeholder comic panel with Pillow."""
    palette = STYLE_PALETTES.get(style.lower().split()[0], STYLE_PALETTES["manga"])
    img = Image.new("RGB", (PANEL_W, PANEL_H), palette["bg"])
    draw = ImageDraw.Draw(img)

    badge_font = _get_font(22, bold=True)
    body_font  = _get_font(17, bold=False)
    strip_font = _get_font(15, bold=True)

    # Outer border
    border = 8
    draw.rectangle([border, border, PANEL_W - border, PANEL_H - border],
                   outline=palette["fg"], width=4)

    # Panel number badge
    badge_r = 28
    draw.ellipse([border + 10, border + 10,
                  border + 10 + badge_r * 2, border + 10 + badge_r * 2],
                 fill=palette["accent"], outline=palette["fg"], width=2)
    draw.text((border + 10 + badge_r, border + 10 + badge_r),
              str(panel_num), fill=palette["bg"], anchor="mm", font=badge_font)

    # Stylized speed lines / mood background
    import math, random
    rng = random.Random(panel_num * 42)
    cx, cy = PANEL_W // 2, PANEL_H // 2
    for _ in range(30):
        angle = rng.uniform(0, 2 * math.pi)
        r1 = rng.uniform(80, 120)
        r2 = rng.uniform(200, 300)
        x1 = cx + r1 * math.cos(angle)
        y1 = cy + r1 * math.sin(angle)
        x2 = cx + r2 * math.cos(angle)
        y2 = cy + r2 * math.sin(angle)
        alpha = rng.randint(30, 80)
        draw.line([(x1, y1), (x2, y2)], fill=palette["fg"] + (alpha,), width=1)

    # Scene description text (wrapped)
    lines = _wrap_text(prompt, max_chars=34)[:5]
    line_h = body_font.size + 6
    y_start = PANEL_H // 2 - len(lines) * line_h // 2
    for i, ln in enumerate(lines):
        y = y_start + i * line_h
        draw.text((cx + 1, y + 1), ln, fill=(0, 0, 0), anchor="mm", font=body_font)
        draw.text((cx, y), ln, fill=palette["fg"], anchor="mm", font=body_font)

    # "GENERATING..." watermark strip at bottom
    strip_h = 44
    draw.rectangle([border + 2, PANEL_H - border - strip_h,
                    PANEL_W - border - 2, PANEL_H - border - 2],
                   fill=palette["accent"])
    draw.text((PANEL_W // 2, PANEL_H - border - strip_h // 2),
              "⚡ AI RENDERING...", fill=palette["bg"], anchor="mm", font=strip_font)

    return img


# --------------------------------------------------------------------------
# FLUX via diffusers (loaded lazily once torch is available)
# --------------------------------------------------------------------------

_flux_pipe = None


def _load_flux():
    global _flux_pipe
    if _flux_pipe is not None:
        return True
    try:
        import torch
        from diffusers import Flux2KleinPipeline
        print("[image_gen] Loading FLUX.2-klein from disk...", flush=True)
        _flux_pipe = Flux2KleinPipeline.from_pretrained(
            FLUX_MODEL_PATH,
            torch_dtype=torch.bfloat16,
        )
        _flux_pipe = _flux_pipe.to("cuda")
        print("[image_gen] FLUX ready.", flush=True)
        return True
    except Exception as e:
        print(f"[image_gen] FLUX load failed: {e}", flush=True)
        return False


def flux_generate(prompt: str, panel_num: int, style: str = "manga") -> Image.Image:
    """Generate a panel image with FLUX.2-klein."""
    import torch
    style_prefix = {
        "manga": "black and white manga ink illustration, detailed linework, comic panel, ",
        "american": "american comic book art, bold colors, cel shaded, strong outlines, ",
        "watercolor": "watercolor comic illustration, soft brushwork, artistic, ",
        "noir": "noir comic panel, high contrast black and white, dramatic shadows, ",
        "cyberpunk": "cyberpunk comic art, neon lights, futuristic cityscape, ",
    }.get(style.lower().split()[0], "comic book panel, ")

    full_prompt = style_prefix + prompt + ", high quality, detailed"

    result = _flux_pipe(
        prompt=full_prompt,
        height=PANEL_H,
        width=PANEL_W,
        num_inference_steps=25,
        guidance_scale=4.0,
        generator=torch.Generator("cuda").manual_seed(panel_num * 100),
    )
    return result.images[0]


# --------------------------------------------------------------------------
# Public interface
# --------------------------------------------------------------------------

def generate_panel_image(prompt: str, panel_num: int, style: str = "manga") -> Image.Image:
    """
    Try FLUX first; fall back to Pillow placeholder if not available.
    Returns a PIL Image ready to paste into the comic page.
    """
    if _load_flux():
        try:
            return flux_generate(prompt, panel_num, style)
        except Exception as e:
            print(f"[image_gen] FLUX generation error: {e}", flush=True)

    return pillow_placeholder(prompt, panel_num, style)


def torch_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False
