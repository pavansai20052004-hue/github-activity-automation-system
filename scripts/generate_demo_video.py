from __future__ import annotations

import json
import math
import shutil
import subprocess
import wave
from pathlib import Path
from textwrap import wrap

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path("docs/demo/github_activity_automation_narrated_demo.mp4")
BUILD_DIR = Path("build/demo_video")
SILENT_VIDEO = BUILD_DIR / "silent_demo.mp4"
COMBINED_AUDIO = BUILD_DIR / "narration.wav"
WIDTH = 1280
HEIGHT = 720
FPS = 24
PAUSE_BETWEEN_SLIDES_SECONDS = 0.45


SLIDES = [
    {
        "title": "GitHub Activity Automation System",
        "subtitle": "Narrated assessment demo",
        "bullets": [
            "Python backend automation using GitHub REST API v3",
            "Daily Commit Agent plus Project Creator Agent",
            "Built for safety, repeatability, and reviewer clarity",
        ],
        "narration": (
            "Hello, this is my demo for the GitHub Activity Automation System. "
            "The project is a Python backend automation tool with two agents: "
            "a Daily Commit Agent and a Project Creator Agent. My approach was to build it "
            "like a small production-ready automation system, not just a one-time script."
        ),
    },
    {
        "title": "What The System Does",
        "subtitle": "Two automation agents",
        "bullets": [
            "Daily Commit Agent updates an activity file in an eligible repository",
            "Project Creator Agent creates and seeds new starter repositories",
            "Both agents are safe to run manually or from a scheduler",
        ],
        "narration": (
            "The Daily Commit Agent fetches repositories owned by the authenticated user, "
            "filters out forks and archived repositories, selects an eligible repository, "
            "and creates one to three commits in a configured tracking file. "
            "The Project Creator Agent creates a new public repository and seeds it with "
            "a README, a gitignore file, and starter source code."
        ),
    },
    {
        "title": "Config-Driven Design",
        "subtitle": "No magic numbers in the source code",
        "bullets": [
            "All meaningful settings live in config.json",
            "Tokens are read from environment variables or .env",
            "Python and JavaScript starter templates are supported",
        ],
        "narration": (
            "All important behavior is controlled by config dot json. "
            "That includes commit counts, commit messages, target file paths, language options, "
            "project creation frequency, GitHub timeout settings, retry behavior, and the kill switch. "
            "Secrets are never hardcoded. The GitHub token is loaded from the GITHUB_TOKEN environment variable "
            "or from a local dot env file that is ignored by Git."
        ),
    },
    {
        "title": "Safety Features",
        "subtitle": "Built for repeatable scheduled runs",
        "bullets": [
            "Idempotency prevents duplicate same-day activity",
            "Kill switch stops both agents before API calls",
            "Runtime lock blocks overlapping scheduled executions",
        ],
        "narration": (
            "The system has several safety layers. "
            "First, local state prevents duplicate same-day Daily Commit runs and respects the Project Creator interval. "
            "Second, a kill switch can stop both agents before they call GitHub. "
            "Third, a runtime lock prevents overlapping cron or Task Scheduler executions from racing each other."
        ),
    },
    {
        "title": "Dry Run And Validation",
        "subtitle": "Reviewer-friendly commands",
        "bullets": [
            "python validate_config.py",
            "python daily_commit.py --dry-run",
            "python project_creator.py --dry-run --language python",
        ],
        "narration": (
            "For reviewer safety, both agents support dry-run mode. "
            "Dry-run mode plans the work and logs what would happen, but it does not create commits, "
            "does not create repositories, and does not mutate local state. "
            "There is also a validate config command that checks the configuration before scheduling the agents."
        ),
    },
    {
        "title": "GitHub API Resilience",
        "subtitle": "Clear errors and retry behavior",
        "bullets": [
            "Raw requests against GitHub REST API v3",
            "Retries transient failures with configurable backoff",
            "Structured JSON logs to stdout and log file",
        ],
        "narration": (
            "The GitHub integration uses REST API v3 directly through requests, which keeps the behavior explicit. "
            "The client handles network failures, server errors, and rate-limit style responses with configurable retries "
            "and exponential backoff. Expected failures are logged clearly as structured JSON instead of failing silently."
        ),
    },
    {
        "title": "Tests And CI",
        "subtitle": "Focused coverage for risky behavior",
        "bullets": [
            "Repository selection and exclusion tests",
            "Idempotency, interval, state, lock, config, and retry tests",
            "GitHub Actions runs config validation and pytest",
        ],
        "narration": (
            "The test suite focuses on the most important risks: repository selection, previous repository avoidance, "
            "idempotency, project creation interval checks, state persistence, runtime locking, config parsing, "
            "and GitHub retry behavior. The repository also includes GitHub Actions, so every push validates the config "
            "and runs the full pytest suite."
        ),
    },
    {
        "title": "Why This Approach",
        "subtitle": "Production-style engineering for a take-home assessment",
        "bullets": [
            "Small focused modules instead of monolithic scripts",
            "Approach docs, architecture notes, README, and submission notes included",
            "Public repository ready for review",
        ],
        "narration": (
            "My main design decision was to keep the project simple, but still production-minded. "
            "The agents are split into focused modules for config, state, GitHub API access, templates, locking, and orchestration. "
            "The result is easy to review, easy to run, and safe to schedule. Thank you for watching the demo."
        ),
    },
]


def main() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    audio_files = synthesize_narration()
    slide_durations = combine_audio(audio_files)
    render_silent_video(slide_durations)
    mux_audio_and_video()
    cleanup_intermediate_files()
    print(f"Wrote narrated demo video: {OUTPUT}")


def synthesize_narration() -> list[Path]:
    voice_items = []
    audio_files = []
    for index, slide in enumerate(SLIDES, start=1):
        audio_path = BUILD_DIR / f"slide_{index:02d}.wav"
        audio_files.append(audio_path)
        voice_items.append({"text": slide["narration"], "path": str(audio_path.resolve())})

    manifest_path = BUILD_DIR / "voice_manifest.json"
    manifest_path.write_text(json.dumps(voice_items, indent=2), encoding="utf-8")

    ps_script = BUILD_DIR / "generate_voice.ps1"
    ps_script.write_text(
        f"""
Add-Type -AssemblyName System.Speech
$items = Get-Content -Raw -LiteralPath "{manifest_path.resolve()}" | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{ $synth.SelectVoice("Microsoft Zira Desktop") }} catch {{ }}
$synth.Rate = 0
$synth.Volume = 100
foreach ($item in $items) {{
    $synth.SetOutputToWaveFile($item.path)
    $synth.Speak($item.text)
    $synth.SetOutputToNull()
}}
$synth.Dispose()
""".strip(),
        encoding="utf-8",
    )

    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps_script.resolve())],
        check=True,
    )
    return audio_files


def combine_audio(audio_files: list[Path]) -> list[float]:
    durations = []
    with wave.open(str(audio_files[0]), "rb") as first:
        params = first.getparams()

    silence_frames = int(params.framerate * PAUSE_BETWEEN_SLIDES_SECONDS)
    silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth

    with wave.open(str(COMBINED_AUDIO), "wb") as output:
        output.setparams(params)
        for audio_file in audio_files:
            with wave.open(str(audio_file), "rb") as source:
                frames = source.readframes(source.getnframes())
                duration = source.getnframes() / source.getframerate()
            output.writeframes(frames)
            output.writeframes(silence)
            durations.append(duration + PAUSE_BETWEEN_SLIDES_SECONDS)

    return durations


def render_silent_video(slide_durations: list[float]) -> None:
    title_font = load_font(48, bold=True)
    subtitle_font = load_font(28, bold=False)
    bullet_font = load_font(30, bold=False)
    footer_font = load_font(20, bold=False)

    with imageio.get_writer(SILENT_VIDEO, fps=FPS, codec="libx264", quality=8, macro_block_size=16) as writer:
        for index, (slide, duration) in enumerate(zip(SLIDES, slide_durations, strict=True), start=1):
            frame = render_slide(slide, index, len(SLIDES), title_font, subtitle_font, bullet_font, footer_font)
            frame_array = np.asarray(frame)
            frame_count = max(1, math.ceil(duration * FPS))
            for _ in range(frame_count):
                writer.append_data(frame_array)


def mux_audio_and_video() -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(SILENT_VIDEO),
            "-i",
            str(COMBINED_AUDIO),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(OUTPUT),
        ],
        check=True,
    )


def render_slide(slide, index, total, title_font, subtitle_font, bullet_font, footer_font) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#09111f")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, WIDTH, 118), fill="#11305a")
    draw.rectangle((0, HEIGHT - 82, WIDTH, HEIGHT), fill="#111827")
    draw.rounded_rectangle((66, 152, WIDTH - 66, HEIGHT - 126), radius=12, outline="#35d0ba", width=3)

    draw.text((78, 34), slide["title"], fill="#f8fafc", font=title_font)
    draw.text((84, 130), slide["subtitle"], fill="#a8dadc", font=subtitle_font)

    y = 218
    for bullet in slide["bullets"]:
        draw.rounded_rectangle((104, y + 9, 130, y + 35), radius=6, fill="#35d0ba")
        lines = wrap(bullet, width=68)
        for line in lines:
            draw.text((156, y), line, fill="#eef2ff", font=bullet_font)
            y += 42
        y += 30

    progress_width = int((WIDTH - 160) * index / total)
    draw.rounded_rectangle((80, HEIGHT - 52, WIDTH - 80, HEIGHT - 38), radius=7, fill="#334155")
    draw.rounded_rectangle((80, HEIGHT - 52, 80 + progress_width, HEIGHT - 38), radius=7, fill="#35d0ba")
    footer = f"Slide {index}/{total} | Narrated demo | github-activity-automation-system"
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


def cleanup_intermediate_files() -> None:
    for path in BUILD_DIR.glob("slide_*.wav"):
        path.unlink(missing_ok=True)
    for path in [BUILD_DIR / "voice_manifest.json", BUILD_DIR / "generate_voice.ps1", SILENT_VIDEO, COMBINED_AUDIO]:
        path.unlink(missing_ok=True)
    if BUILD_DIR.exists() and not any(BUILD_DIR.iterdir()):
        shutil.rmtree(BUILD_DIR)


if __name__ == "__main__":
    main()
