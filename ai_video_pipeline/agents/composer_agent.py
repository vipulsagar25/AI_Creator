"""
agents/composer_agent.py
=========================
Assembles final video from per-scene images + audio using FFmpeg.
Features: Ken Burns zoom effect, crossfade transitions, burned-in subtitles.
Pure subprocess FFmpeg — no MoviePy overhead.
"""

import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Optional

from config import PipelineConfig

logger = logging.getLogger("composer_agent")


class ComposerAgent:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self._check_ffmpeg()

    def compose(self, scenes: List[Dict], out_path: str, srt_path: Optional[str] = None) -> str:
        """
        Full composition pipeline:
        1. Per-scene: image + audio → scene clip
        2. Concat all clips
        3. Burn subtitles
        Returns final video path.
        """
        scene_clips = []
        for scene in scenes:
            clip_path = self._make_scene_clip(scene)
            scene_clips.append(clip_path)

        concat_path = str(Path(self.config.video_dir) / "concat.mp4")
        self._concat_clips(scene_clips, concat_path)

        if srt_path and Path(srt_path).exists():
            final = self._burn_subtitles(concat_path, srt_path, out_path)
        else:
            shutil.copy(concat_path, out_path)
            final = out_path

        logger.info(f"Final video: {final}")
        return final

    # ── Scene Clip ────────────────────────────────────────────────────────────

    def _make_scene_clip(self, scene: Dict) -> str:
        """Combine image + audio into a single scene clip with zoom effect."""
        scene_id  = scene["id"]
        image     = scene["image"]
        audio     = scene["audio"]
        duration  = scene["duration"]
        out_path  = str(Path(self.config.video_dir) / f"scene_{scene_id}.mp4")

        fps     = self.config.fps
        zoom    = self.config.zoom_ratio
        w, h    = self.config.image_width, self.config.image_height

        if self.config.zoom_effect:
            # Ken Burns: slow zoom in, centered
            # zoompan formula: zoom from 1.0 → (1 + zoom_ratio) over duration
            total_frames = int(duration * fps)
            zoom_filter  = (
                f"zoompan=z='min(zoom+{zoom/total_frames:.6f},1+{zoom})'"
                f":x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)'"
                f":d={total_frames}:s={w}x{h}:fps={fps}"
            )
            vf = zoom_filter
        else:
            vf = f"scale={w}:{h}"

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image,
            "-i", audio,
            "-vf", vf,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-t", str(duration),
            out_path
        ]
        self._run(cmd, f"scene_{scene_id} clip")
        return out_path

    # ── Concatenation ─────────────────────────────────────────────────────────

    def _concat_clips(self, clips: List[str], out_path: str):
        """Concatenate scene clips using FFmpeg concat demuxer."""
        list_file = Path(self.config.video_dir) / "concat_list.txt"
        with open(list_file, "w") as f:
            for clip in clips:
                f.write(f"file '{Path(clip).resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            out_path
        ]
        self._run(cmd, "concat")

    # ── Subtitles ─────────────────────────────────────────────────────────────

    def _burn_subtitles(self, video_path: str, srt_path: str, out_path: str) -> str:
        """Burn subtitles into video using FFmpeg subtitles filter."""
        font     = self.config.subtitle_font
        fontsize = self.config.subtitle_fontsize
        color    = self.config.subtitle_color

        # Escape path for FFmpeg filter
        safe_srt = str(Path(srt_path).resolve()).replace("\\", "/").replace(":", "\\:")

        sub_filter = (
            f"subtitles='{safe_srt}'"
            f":force_style='FontName={font},FontSize={fontsize},"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,"
            f"Alignment=2'"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", sub_filter,
            "-c:a", "copy",
            out_path
        ]
        self._run(cmd, "burn subtitles")
        return out_path

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _run(self, cmd: List[str], label: str):
        logger.info(f"FFmpeg [{label}]: running...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg [{label}] stderr:\n{result.stderr[-1000:]}")
            raise RuntimeError(f"FFmpeg failed at step: {label}")
        logger.info(f"FFmpeg [{label}]: done")

    def _check_ffmpeg(self):
        if not shutil.which("ffmpeg"):
            raise EnvironmentError(
                "FFmpeg not found. Install with: "
                "Ubuntu → 'sudo apt install ffmpeg' | "
                "Windows → https://ffmpeg.org/download.html"
            )
