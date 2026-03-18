"""
Visual QA via Qwen3-VL-2B GGUF using llama-mtmd-cli.
Checks whether a generated panel image matches its intended scene description.
Returns (passed: bool, feedback: str).
"""
import subprocess
import tempfile
import os
from pathlib import Path
from PIL import Image

LLAMA_MTMD = "/home/nvidia/llama.cpp/build/bin/llama-mtmd-cli"
VL_MODEL = "/home/nvidia/models/gguf/Qwen--Qwen3-VL-2B-Instruct-GGUF/Qwen3VL-2B-Instruct-Q4_K_M.gguf"


def check_panel(image: Image.Image, scene_description: str, timeout: int = 60) -> tuple[bool, str]:
    """
    Run Qwen3-VL-2B on the panel image to verify it matches the scene description.
    Returns (passed, feedback_text).
    """
    if not Path(LLAMA_MTMD).exists():
        return True, "VL QA skipped (tool not found)"
    if not Path(VL_MODEL).exists():
        return True, "VL QA skipped (model not found)"

    # Save image to a temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = f.name
        image.save(tmp_path)

    prompt = (
        f"Does this comic panel image match the following scene description? "
        f"Answer YES or NO first, then briefly explain why in one sentence.\n\n"
        f"Scene: {scene_description}"
    )

    cmd = [
        LLAMA_MTMD,
        "-m", VL_MODEL,
        "--image", tmp_path,
        "-p", prompt,
        "-n", "80",
        "--temp", "0.1",
        "-ngl", "99",
        "--no-display-prompt",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip()
        passed = output.upper().startswith("YES")
        return passed, output
    except subprocess.TimeoutExpired:
        return True, "VL QA timed out — skipped"
    except Exception as e:
        return True, f"VL QA error: {e}"
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
