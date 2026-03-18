"""
Comic page compositor.
Assembles panel images with speech bubbles, captions, and title into a full comic page.
Outputs PNG. Optionally exports PDF via reportlab.
"""
import textwrap
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Panel dimensions
PANEL_W = 512
PANEL_H = 512

# Page margins and gutters
MARGIN = 30
GUTTER = 12
CAPTION_BAR_H = 48
SPEECH_PADDING = 10

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 248, 180)
PANEL_BORDER = 4


def _get_font(size: int, bold: bool = True):
    base = Path(__file__).parent / "fonts"
    bold_paths = [
        str(base / "ComicNeue-Bold.ttf"),
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    regular_paths = [
        str(base / "ComicNeue-Regular.ttf"),
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in (bold_paths if bold else regular_paths):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text_to_width(draw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] > max_width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_speech_bubble(draw: ImageDraw, text: str, x: int, y: int,
                         max_w: int, font, tail_dir: str = "bottom",
                         x_min: int = 6, x_max: int = 1500):
    """Draw an oval speech bubble with a tail."""
    if not text.strip():
        return

    lines = _wrap_text_to_width(draw, text, font, max_w - 2 * SPEECH_PADDING)
    if not lines:
        return

    line_h = font.size + 4
    text_w = max(draw.textbbox((0, 0), ln, font=font)[2] for ln in lines)
    text_h = len(lines) * line_h

    bx0 = x - text_w // 2 - SPEECH_PADDING
    by0 = y - text_h // 2 - SPEECH_PADDING
    bx1 = x + text_w // 2 + SPEECH_PADDING
    by1 = y + text_h // 2 + SPEECH_PADDING

    # Clamp to panel bounds
    bx0 = max(x_min, bx0)
    bx1 = min(x_max, bx1)
    # Ensure minimum bubble size
    if bx1 <= bx0 + 10:
        bx1 = bx0 + max(text_w + 2 * SPEECH_PADDING, 60)
    if by1 <= by0 + 10:
        by1 = by0 + max(text_h + 2 * SPEECH_PADDING, 24)

    # Bubble fill + outline
    draw.ellipse([bx0, by0, bx1, by1], fill=WHITE, outline=BLACK, width=2)

    # Tail triangle pointing down-left
    tail_x = (bx0 + bx1) // 2
    if tail_dir == "bottom":
        tail_pts = [(tail_x - 8, by1), (tail_x + 8, by1), (tail_x, by1 + 20)]
    else:
        tail_pts = [(tail_x - 8, by0), (tail_x + 8, by0), (tail_x, by0 - 20)]
    draw.polygon(tail_pts, fill=WHITE, outline=BLACK)

    # Re-draw ellipse on top of tail seam
    draw.ellipse([bx0, by0, bx1, by1], fill=WHITE, outline=BLACK, width=2)

    # Text
    ty = by0 + SPEECH_PADDING
    for ln in lines:
        lw = draw.textbbox((0, 0), ln, font=font)[2]
        draw.text((bx0 + SPEECH_PADDING + (text_w - lw) // 2, ty), ln,
                  fill=BLACK, font=font)
        ty += line_h


def _draw_caption(draw: ImageDraw, text: str, x0: int, y0: int, width: int, font):
    """Draw a yellow caption box at the top or bottom of a panel."""
    if not text.strip():
        return 0
    lines = _wrap_text_to_width(draw, text, font, width - 2 * SPEECH_PADDING)
    line_h = font.size + 4
    box_h = len(lines) * line_h + 2 * SPEECH_PADDING
    draw.rectangle([x0, y0, x0 + width, y0 + box_h], fill=YELLOW, outline=BLACK, width=2)
    ty = y0 + SPEECH_PADDING
    for ln in lines:
        draw.text((x0 + SPEECH_PADDING, ty), ln, fill=BLACK, font=font)
        ty += line_h
    return box_h


def _layout_grid(num_panels: int) -> list[tuple[int, int, int, int]]:
    """
    Return panel bounding boxes in page coordinates for a grid layout.
    Each box: (col, row, colspan, rowspan) in grid units.
    """
    if num_panels <= 3:
        return [(i, 0, 1, 1) for i in range(num_panels)]
    if num_panels == 4:
        return [(0, 0, 1, 1), (1, 0, 1, 1), (0, 1, 1, 1), (1, 1, 1, 1)]
    if num_panels == 5:
        return [(0, 0, 1, 1), (1, 0, 1, 1), (2, 0, 1, 1),
                (0, 1, 1, 1), (1, 1, 2, 1)]
    if num_panels == 6:
        return [(i % 3, i // 3, 1, 1) for i in range(6)]
    # Fallback: 2 columns
    cols = 2
    rows = math.ceil(num_panels / cols)
    boxes = []
    for i in range(num_panels):
        boxes.append((i % cols, i // cols, 1, 1))
    return boxes


def compose_page(panels: list[dict], title: str = "", style: str = "manga") -> Image.Image:
    """
    Build the full comic page from a list of panel dicts.
    Each panel dict: {image: PIL.Image, dialogue: str, caption: str, panel_number: int}
    Returns a PIL Image of the full page.
    """
    num = len(panels)
    cols = min(3, num) if num > 3 else num
    rows = math.ceil(num / cols)

    title_h = 70 if title else 0
    page_w = MARGIN * 2 + cols * PANEL_W + (cols - 1) * GUTTER
    page_h = MARGIN * 2 + title_h + rows * PANEL_H + (rows - 1) * GUTTER + rows * CAPTION_BAR_H

    page = Image.new("RGB", (page_w, page_h), WHITE)
    draw = ImageDraw.Draw(page)

    title_font = _get_font(40, bold=True)
    caption_font = _get_font(17, bold=False)
    speech_font = _get_font(16, bold=False)

    # Title bar
    if title:
        draw.rectangle([0, 0, page_w, title_h], fill=BLACK)
        draw.text((page_w // 2, title_h // 2), title.upper(),
                  fill=WHITE, font=title_font, anchor="mm")

    y_base = MARGIN + title_h

    for i, panel in enumerate(panels):
        col = i % cols
        row = i // cols

        px = MARGIN + col * (PANEL_W + GUTTER)
        py = y_base + row * (PANEL_H + GUTTER + CAPTION_BAR_H)

        # Panel border
        draw.rectangle([px - PANEL_BORDER, py - PANEL_BORDER,
                         px + PANEL_W + PANEL_BORDER, py + PANEL_H + PANEL_BORDER],
                        fill=BLACK)

        # Paste panel image
        img = panel.get("image")
        if img:
            img_resized = img.resize((PANEL_W, PANEL_H), Image.LANCZOS)
            page.paste(img_resized, (px, py))

        # Caption strip below panel
        cap_y = py + PANEL_H + 4
        caption_text = panel.get("caption", "").strip()
        if caption_text:
            _draw_caption(draw, caption_text, px, cap_y, PANEL_W, caption_font)

        # Speech bubble overlay on panel
        dialogue_text = panel.get("dialogue", "").strip()
        if dialogue_text:
            # Strip "Character: " prefix for cleaner bubble
            if ":" in dialogue_text:
                parts = dialogue_text.split(":", 1)
                dialogue_text = parts[1].strip()
            bubble_x = px + PANEL_W // 2
            bubble_y = py + 60
            _draw_speech_bubble(
                draw,
                dialogue_text,
                bubble_x, bubble_y,
                PANEL_W - 20, speech_font,
                tail_dir="bottom",
                x_min=px + 6,
                x_max=px + PANEL_W - 6,
            )

    return page


def save_page(page: Image.Image, output_path: str):
    """Save the comic page as PNG."""
    page.save(output_path, "PNG", optimize=True)
    return output_path


def export_pdf(page: Image.Image, output_path: str):
    """Export the comic page as a PDF using reportlab."""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.pdfgen import canvas
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_png = tmp.name
            page.save(tmp_png, "PNG")

        w, h = page.size
        # A4 in points
        a4_w, a4_h = A4
        scale = min(a4_w / w, a4_h / h)
        img_w, img_h = w * scale, h * scale
        x_off = (a4_w - img_w) / 2
        y_off = (a4_h - img_h) / 2

        c = canvas.Canvas(output_path, pagesize=A4)
        c.drawImage(tmp_png, x_off, y_off, img_w, img_h)
        c.save()
        os.unlink(tmp_png)
        return output_path
    except Exception as e:
        print(f"[compositor] PDF export failed: {e}")
        return None
