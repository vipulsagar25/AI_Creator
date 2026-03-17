"""
agents/subtitle_agent.py
=========================
Generates a proper .srt subtitle file from scene text + audio durations.
No external dependency — pure Python SRT formatting.
"""

import logging
from pathlib import Path
from typing import List, Dict

from config import PipelineConfig

logger = logging.getLogger("subtitle_agent")


def _format_srt_time(seconds: float) -> str:
    """Convert float seconds → SRT timestamp: HH:MM:SS,mmm"""
    ms  = int((seconds % 1) * 1000)
    s   = int(seconds) % 60
    m   = int(seconds // 60) % 60
    h   = int(seconds // 3600)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


class SubtitleAgent:
    def __init__(self, config: PipelineConfig):
        self.config = config

    def generate(self, scenes: List[Dict], out_path: str) -> str:
        """
        Generate SRT file from scenes.
        Each scene = one subtitle block.
        Returns path to .srt file.
        """
        blocks   = []
        cursor   = 0.0  # running timestamp (seconds)

        for scene in scenes:
            duration = scene.get("duration", 3.0)
            text     = scene["text"]

            start = cursor
            end   = cursor + duration
            cursor = end

            blocks.append(self._srt_block(scene["id"], start, end, text))

        srt_content = "\n\n".join(blocks)
        Path(out_path).write_text(srt_content, encoding="utf-8")
        logger.info(f"SRT generated: {out_path} ({len(blocks)} blocks)")
        return out_path

    def _srt_block(self, idx: int, start: float, end: float, text: str) -> str:
        return (
            f"{idx}\n"
            f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n"
            f"{text}"
        )
