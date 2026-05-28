from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path("docs/demo/github_activity_automation_demo.mp4")
WIDTH = 1280
HEIGHT = 720
FPS = 24
SECONDS_PER_SLIDE = 6


SLIDES = [
    {
        "title": "GitHub Activity Automation System",
        "subtitle": "Backend Engineering Assessment Demo",
        "bullets": [
            "Daily Commit Agent",
            "Project Creator Agent",
            "Config-driven, safe, idempotent automation",
        ],
    },
    {
        "title": "Core Requirements Covered",
        "subtitle": "Two agents built around GitHub REST API v3",
        "bullets": [
            "Fetch eligible owned repositories and create 1-3 activity commits",
            "Create new public starter repositories with Python or JavaScript files",
            "Persist state locally to avoid duplicate same-day or duplicate project runs",
        ],
    },
    {
        "title": "Safety First",
        "subtitle": "Designed for scheduled automation",
        "bullets": [
            "Kill switch through config or STOP_AGENTS file",
            "--dry-run mode previews work without writes or state changes",
            "Runtime lock prevents overlapping cron or Task Scheduler runs",
        ],
    },
    {
        "title": "Config And Secrets",
        "subtitle": "No secrets or magic numbers in source code",
        "bullets": [
            "All behavior lives in config.json",
            "GITHUB_TOKEN is loaded from environment or .env",
            ".env, logs, state, and lock files are ignored by Git",
        ],
    },
    {
        "title": "Resilience",
        "subtitle": "Graceful handling for real-world API behavior",
        "bullets": [
            "Structured JSON logs to stdout and logs/automation.log",
            "Retries transient GitHub errors with configurable backoff",
            "External idea generation falls back to built-in project ideas",
        ],
    },
    {
        "title": "Validation",
        "subtitle": "Fast checks for reviewers",
        "bullets": [
            "python validate_config.py",
            "python -m pytest -q",
            "GitHub Actions validates config and runs the test suite on every push",
        ],
    },
    {
        "title": "Why This Approach",
        "subtitle": "A small production-style automation tool, not a one-off script",
        "bullets": [
            "Focused modules: config, state, GitHub client, agents, templates",
            "Readable docs: README, architecture notes, approach, demo script",
            "Public repo ready for assessment review",
        ],
    },
]


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    title_font = load_font(48, bold=True)
    subtitle_font = load_font(28, bold=False)
    bullet_font = load_font(30, bold=False)
    footer_font = load_font(20, bold=False)

    with imageio.get_writer(OUTPUT, fps=FPS, codec="libx264", quality=8, macro_block_size=16) as writer:
        for index, slide in enumerate(SLIDES, start=1):
            frame = render_slide(slide, index, len(SLIDES), title_font, subtitle_font, bullet_font, footer_font)
            frame_array = np.asarray(frame)
            for _ in range(FPS * SECONDS_PER_SLIDE):
                writer.append_data(frame_array)

    print(f"Wrote {OUTPUT}")


def render_slide(slide, index, total, title_font, subtitle_font, bullet_font, footer_font) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#0b1220")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, WIDTH, 110), fill="#12355b")
    draw.rectangle((0, HEIGHT - 76, WIDTH, HEIGHT), fill="#101828")
    draw.rectangle((70, 148, WIDTH - 70, HEIGHT - 120), outline="#2dd4bf", width=3)

    draw.text((80, 34), slide["title"], fill="#f8fafc", font=title_font)
    draw.text((84, 126), slide["subtitle"], fill="#9ccfd8", font=subtitle_font)

    y = 215
    for bullet in slide["bullets"]:
        draw.rounded_rectangle((105, y + 8, 129, y + 32), radius=5, fill="#2dd4bf")
        lines = wrap(bullet, width=68)
        for line in lines:
            draw.text((150, y), line, fill="#e5e7eb", font=bullet_font)
            y += 40
        y += 28

    progress_width = int((WIDTH - 160) * index / total)
    draw.rounded_rectangle((80, HEIGHT - 48, WIDTH - 80, HEIGHT - 34), radius=7, fill="#334155")
    draw.rounded_rectangle((80, HEIGHT - 48, 80 + progress_width, HEIGHT - 34), radius=7, fill="#2dd4bf")
    footer = f"Slide {index}/{total} | github-activity-automation-system"
    draw.text((80, HEIGHT - 30), footer, fill="#cbd5e1", font=footer_font)
    return image


def load_font(size: int, bold: bool) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


if __name__ == "__main__":
    main()

