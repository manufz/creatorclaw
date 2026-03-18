"""
Comic Creator — Hackathon Demo
NVIDIA GB10 · Nemotron-30B story scripting · FLUX.2-klein image generation

Run: python3 app.py
"""
import os
import sys
import time
import json
import tempfile
from pathlib import Path

import gradio as gr
from PIL import Image

# Add project dir to path
sys.path.insert(0, str(Path(__file__).parent))

from story_gen import generate_script, server_ready
from image_gen import generate_panel_image, torch_available
from vl_qa import check_panel
from compositor import compose_page, save_page, export_pdf

# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _status(msg: str, progress=None) -> str:
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    return line


def _check_gpu_status() -> str:
    lines = []
    if server_ready():
        lines.append("✅ Nemotron story server: ONLINE (port 8080)")
    else:
        lines.append("⚠️  Nemotron story server: OFFLINE — run start.sh first")
    if torch_available():
        lines.append("✅ FLUX image generation: READY (GPU)")
    else:
        lines.append("⚡ FLUX image generation: Installing... (using stylized placeholders now)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def run_pipeline(idea: str, num_panels: int, style: str,
                 use_vl_qa: bool, progress=gr.Progress(track_tqdm=True)):
    """
    Full pipeline:
    1. Nemotron → comic script JSON
    2. FLUX (or Pillow fallback) → panel images
    3. (Optional) Qwen3-VL → visual QA
    4. Compositor → full page PNG + PDF
    """
    logs = []

    def log(msg):
        entry = _status(msg)
        logs.append(entry)
        return "\n".join(logs)

    if not idea.strip():
        yield None, None, None, "❌ Please enter a story idea.", None
        return

    if not server_ready():
        yield None, None, None, (
            "❌ Nemotron server is not running.\n"
            "Start it with: ./start.sh\n"
            "Then try again."
        ), None
        return

    # Step 1: Story generation
    yield None, None, None, log("🧠 Generating comic script with Nemotron-30B..."), None
    progress(0.05, desc="Story scripting...")

    try:
        script = generate_script(idea, num_panels=num_panels, style=style)
    except Exception as e:
        yield None, None, None, log(f"❌ Story generation failed: {e}"), None
        return

    panels_data = script.get("panels", [])
    title = script.get("title", "My Comic")
    log(f"✅ Script ready: '{title}' ({len(panels_data)} panels)")
    yield None, None, json.dumps(script, indent=2), "\n".join(logs), None

    # Step 2: Generate panel images
    panel_results = []
    for i, panel in enumerate(panels_data):
        pn = panel.get("panel_number", i + 1)
        img_prompt = panel.get("image_prompt", panel.get("scene", ""))
        log(f"🎨 Rendering panel {pn}/{len(panels_data)}...")
        progress((0.1 + 0.6 * i / len(panels_data)), desc=f"Panel {pn} image...")
        yield None, None, json.dumps(script, indent=2), "\n".join(logs), None

        img = generate_panel_image(img_prompt, pn, style)

        # Step 3: VL QA (optional)
        qa_result = ""
        if use_vl_qa:
            log(f"🔍 VL QA check on panel {pn}...")
            passed, feedback = check_panel(img, panel.get("scene", ""))
            qa_result = f" | QA: {'✅' if passed else '⚠️'} {feedback[:80]}"
            if not passed:
                log(f"  ⚠️  Panel {pn} QA failed — regenerating...")
                img = generate_panel_image(img_prompt + ", more detailed", pn + 100, style)
        log(f"  ✅ Panel {pn} done{qa_result}")

        panel_results.append({
            "image": img,
            "dialogue": panel.get("dialogue", ""),
            "caption": panel.get("caption", ""),
            "panel_number": pn,
        })
        yield img, None, json.dumps(script, indent=2), "\n".join(logs), None

    # Step 4: Compose full page
    log("📄 Compositing final comic page...")
    progress(0.9, desc="Compositing page...")
    page = compose_page(panel_results, title=title, style=style)

    # Save outputs
    out_dir = Path(tempfile.mkdtemp(prefix="comic_"))
    png_path = str(out_dir / "comic_page.png")
    pdf_path = str(out_dir / "comic_page.pdf")
    save_page(page, png_path)
    export_pdf(page, pdf_path)

    log(f"✅ Comic complete! Saved to {png_path}")
    progress(1.0, desc="Done!")

    if not Path(pdf_path).exists():
        pdf_path = None

    yield panel_results[-1]["image"], page, json.dumps(script, indent=2), "\n".join(logs), png_path


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

STYLES = ["manga", "american", "watercolor", "noir", "cyberpunk"]

EXAMPLES = [
    ["A lone astronaut discovers ancient alien ruins on Mars.", 4, "manga"],
    ["A street chef in Neo-Tokyo accidentally creates a dish that grants superpowers.", 3, "cyberpunk"],
    ["Two rival detectives must team up to solve the impossible heist of the century.", 6, "noir"],
    ["A young wizard accidentally swaps lives with their cat.", 4, "watercolor"],
]

CSS = """
.gradio-container { font-family: 'Comic Sans MS', cursive, sans-serif; }
#title-bar { background: #1a1a2e; padding: 20px; border-radius: 8px; margin-bottom: 10px; }
#title-bar h1 { color: #76ff03; margin: 0; font-size: 2em; }
#title-bar p { color: #aaa; margin: 4px 0 0 0; }
.status-box { font-family: monospace; font-size: 12px; background: #0d0d0d; color: #76ff03; }
"""

with gr.Blocks(title="Comic Creator — NVIDIA GB10 Hackathon") as demo:
    gr.HTML("""
    <div id="title-bar">
      <h1>⚡ Comic Creator</h1>
      <p>Powered by Nemotron-30B (story) · FLUX.2-klein (art) · Qwen3-VL (QA) · Running fully local on NVIDIA GB10</p>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📝 Your Idea")
            idea_input = gr.Textbox(
                label="Story Idea",
                placeholder="A cyberpunk hacker discovers the city's AI overlord has been dreaming...",
                lines=4,
            )
            with gr.Row():
                num_panels = gr.Slider(2, 6, value=4, step=1, label="Panels")
                style_select = gr.Dropdown(STYLES, value="manga", label="Art Style")

            use_vl_qa = gr.Checkbox(value=False, label="Enable Visual QA (Qwen3-VL)")

            generate_btn = gr.Button("⚡ Create Comic", variant="primary", size="lg")

            gr.Markdown("### 🎭 Examples")
            gr.Examples(examples=EXAMPLES,
                         inputs=[idea_input, num_panels, style_select],
                         label="Quick starts")

            gr.Markdown("---")
            status_label = gr.Markdown(_check_gpu_status())
            refresh_btn = gr.Button("🔄 Refresh Status", size="sm")

        with gr.Column(scale=2):
            gr.Markdown("### 🖼️ Output")
            with gr.Tabs():
                with gr.Tab("Comic Page"):
                    page_output = gr.Image(label="Full Comic Page", height=600)
                    png_download = gr.File(label="Download PNG", visible=False)
                with gr.Tab("Latest Panel"):
                    panel_output = gr.Image(label="Current Panel", height=400)
                with gr.Tab("Script JSON"):
                    script_output = gr.Code(language="json", label="Comic Script")

            log_output = gr.Textbox(
                label="Pipeline Log",
                lines=8,
                elem_classes=["status-box"],
                interactive=False,
            )

    # Wiring
    generate_btn.click(
        fn=run_pipeline,
        inputs=[idea_input, num_panels, style_select, use_vl_qa],
        outputs=[panel_output, page_output, script_output, log_output, png_download],
    )

    refresh_btn.click(fn=_check_gpu_status, outputs=status_label)

if __name__ == "__main__":
    print("=" * 60)
    print("  Comic Creator — NVIDIA GB10 Hackathon Demo")
    print("=" * 60)
    print(_check_gpu_status())
    print("=" * 60)
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=CSS,
    )
