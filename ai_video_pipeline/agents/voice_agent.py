"""
agents/voice_agent.py
======================
Converts scene text → .wav audio using Microsoft Edge-TTS (free, no API key).
Audio duration drives all downstream timing — this is the source of truth.
"""

import asyncio
import logging
import hashlib
from pathlib import Path
from typing import List, Dict

import edge_tts
from pydub import AudioSegment

from config import PipelineConfig

logger = logging.getLogger("voice_agent")


class VoiceAgent:
    def __init__(self, config: PipelineConfig):
        self.config = config

    async def process_all(self, scenes: List[Dict]) -> List[Dict]:
        """Process all scenes concurrently."""
        tasks = [self._process_scene(scene) for scene in scenes]
        return await asyncio.gather(*tasks)

    async def _process_scene(self, scene: Dict) -> Dict:
        scene_id = scene["id"]
        text     = scene["text"]
        out_path = Path(self.config.audio_dir) / f"scene_{scene_id}.mp3"

        # Cache: skip if already generated
        if out_path.exists() and self._cache_valid(text, out_path):
            logger.info(f"Scene {scene_id}: audio cache hit")
        else:
            await self._generate_tts(text, out_path, scene_id)

        duration = self._get_duration(out_path)
        scene["audio"]    = str(out_path)
        scene["duration"] = duration
        logger.info(f"Scene {scene_id}: audio={out_path.name}, duration={duration:.2f}s")
        return scene

    async def _generate_tts(self, text: str, out_path: Path, scene_id: int):
        """Generate TTS with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                communicate = edge_tts.Communicate(
                    text,
                    voice=self.config.tts_voice,
                    rate=self.config.tts_rate,
                    pitch=self.config.tts_pitch,
                )
                await communicate.save(str(out_path))
                logger.info(f"Scene {scene_id}: TTS generated")
                return
            except Exception as e:
                logger.warning(f"Scene {scene_id} TTS attempt {attempt+1} failed: {e}")
                await asyncio.sleep(self.config.retry_delay)
        raise RuntimeError(f"Scene {scene_id}: TTS failed after {self.config.max_retries} retries")

    def _get_duration(self, audio_path: Path) -> float:
        """Return audio duration in seconds using pydub."""
        audio = AudioSegment.from_file(str(audio_path))
        return len(audio) / 1000.0  # ms → seconds

    def _cache_valid(self, text: str, path: Path) -> bool:
        """Simple hash-based cache validation."""
        cache_file = Path(self.config.cache_dir) / f"{path.stem}.hash"
        text_hash  = hashlib.md5(text.encode()).hexdigest()
        if cache_file.exists():
            return cache_file.read_text().strip() == text_hash
        # Write hash for next time
        cache_file.write_text(text_hash)
        return False
