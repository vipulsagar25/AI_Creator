"""
agents/scene_controller.py
===========================
Orchestrator: validates, normalizes, and sequences scene data.
Every downstream agent receives a guaranteed-shape Scene dict.
"""

import logging
from typing import List, Dict, Any
from config import PipelineConfig

logger = logging.getLogger("scene_controller")

# Canonical scene shape — all agents expect exactly this
SCENE_SCHEMA = {
    "id":         int,
    "text":       str,
    "prompt":     str,   # image generation prompt (can differ from spoken text)
    "audio":      None,  # filled by VoiceAgent
    "duration":   None,  # filled by VoiceAgent (seconds)
    "image":      None,  # filled by VisualAgent
}


class SceneController:
    def __init__(self, config: PipelineConfig):
        self.config = config

    def prepare(self, raw_scenes: List[Dict[str, Any]]) -> List[Dict]:
        """
        Validate and normalize raw scenes from input JSON.
        Returns list of enriched scene dicts ready for agent processing.
        """
        scenes = []
        for idx, raw in enumerate(raw_scenes):
            scene = self._normalize(idx + 1, raw)
            scenes.append(scene)
            logger.info(f"Scene {scene['id']} prepared: {scene['text'][:50]}...")
        return scenes

    def _normalize(self, idx: int, raw: Dict) -> Dict:
        if "text" not in raw:
            raise ValueError(f"Scene {idx} is missing required field: 'text'")

        return {
            "id":       raw.get("id", idx),
            "text":     raw["text"].strip(),
            # If no dedicated image prompt, auto-build one from text + global style
            "prompt":   raw.get("prompt", self._build_prompt(raw["text"])),
            "audio":    None,
            "duration": None,
            "image":    None,
        }

    def _build_prompt(self, text: str) -> str:
        """Auto-generate an image prompt from spoken text."""
        style = self.config.image_style
        # Keep it short — Pollinations handles long prompts poorly
        trimmed = text[:120] if len(text) > 120 else text
        return f"{trimmed}, {style}"
