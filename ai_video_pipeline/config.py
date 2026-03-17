"""
config.py - Central Configuration
All tuneable parameters live here. Never scatter magic values across agents.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    # ── Directories ──────────────────────────────────────────────
    base_dir:    Path = Path("output")
    audio_dir:   Path = Path("output/audio")
    image_dir:   Path = Path("output/images")
    video_dir:   Path = Path("output/video")
    cache_dir:   Path = Path("output/cache")

    # ── Edge-TTS ─────────────────────────────────────────────────
    tts_voice:   str  = "en-US-AriaNeural"       # change for different accent/gender
    tts_rate:    str  = "+0%"                     # speed: +10% = faster
    tts_pitch:   str  = "+0Hz"

    # ── Pollinations Image API ────────────────────────────────────
    image_width:  int  = 1024
    image_height: int  = 576                      # 16:9 for video
    image_model:  str  = "turbo"                  # flux | turbo
    image_seed:   int  = 42                       # fixed seed = reproducibility
    image_style:  str  = "cinematic, high quality, detailed, 4k"

    # ── Video Composition ─────────────────────────────────────────
    fps:          int   = 24
    transition_duration: float = 0.5              # seconds
    zoom_effect:  bool  = True                    # Ken Burns effect
    zoom_ratio:   float = 0.05                    # subtle zoom per scene

    # ── Subtitles ─────────────────────────────────────────────────
    subtitle_font:     str = "Arial"
    subtitle_fontsize: int = 24
    subtitle_color:    str = "white"
    subtitle_bg:       str = "black@0.5"          # semi-transparent bg

    # ── Retry / Reliability ───────────────────────────────────────
    max_retries:  int   = 1
    retry_delay:  float = 1.0                     # seconds between retries

    def ensure_dirs(self):
        """Create all output directories if they don't exist."""
        for d in [self.base_dir, self.audio_dir, self.image_dir,
                  self.video_dir, self.cache_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)
