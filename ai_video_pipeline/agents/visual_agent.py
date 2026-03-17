"""
agents/visual_agent.py
=======================
Generates one image per scene using Pollinations.ai free API.
Fixed seed per scene = reproducible outputs across runs.
No API key required.
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import List, Dict
from urllib.parse import quote

import httpx

from config import PipelineConfig

logger = logging.getLogger("visual_agent")

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"


class VisualAgent:
    def __init__(self, config: PipelineConfig):
        self.config = config

    async def process_all(self, scenes: List[Dict]) -> List[Dict]:
        """Process all scenes with controlled concurrency (avoid rate limits)."""
        semaphore = asyncio.Semaphore(1)  # max 1 concurrent image requests to avoid 429

        async def bounded(scene):
            async with semaphore:
                return await self._process_scene(scene)

        tasks = [bounded(scene) for scene in scenes]
        return await asyncio.gather(*tasks)

    async def _process_scene(self, scene: Dict) -> Dict:
        scene_id = scene["id"]
        prompt   = scene["prompt"]
        out_path = Path(self.config.image_dir) / f"scene_{scene_id}.jpg"

        if out_path.exists() and self._cache_valid(prompt, out_path):
            logger.info(f"Scene {scene_id}: image cache hit")
        else:
            await self._generate_image(prompt, out_path, scene_id)

        scene["image"] = str(out_path)
        logger.info(f"Scene {scene_id}: image={out_path.name}")
        return scene

    async def _generate_image(self, prompt: str, out_path: Path, scene_id: int):
        """Fetch image from Pollinations with retry."""
        # Per-scene seed derived from global seed + scene_id = reproducible
        seed = self.config.image_seed + scene_id

        url = POLLINATIONS_URL.format(prompt=quote(prompt))
        params = {
            "width":  self.config.image_width,
            "height": self.config.image_height,
            "model":  self.config.image_model,
            "seed":   seed,
            "nologo": "true",
        }

        for attempt in range(self.config.max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    out_path.write_bytes(response.content)
                    logger.info(f"Scene {scene_id}: image generated (seed={seed})")
                    return
            except Exception as e:
                logger.warning(f"Scene {scene_id} image attempt {attempt+1} failed: {e}")
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        # If we reach here, Pollinations API completely failed (429 or timeout).
        # Fallback to a fast dummy image so the pipeline can succeed.
        logger.warning(f"Scene {scene_id}: Pollinations API failed after {self.config.max_retries} retries. Using dummy placeholder.")
        dummy_url = f"https://dummyimage.com/{self.config.image_width}x{self.config.image_height}/736d89/fff&text=Scene+{scene_id}+Fallback"
        async with httpx.AsyncClient() as client:
            resp = await client.get(dummy_url)
            out_path.write_bytes(resp.content)
            logger.info(f"Scene {scene_id}: dummy image generated")

    def _cache_valid(self, prompt: str, path: Path) -> bool:
        cache_file = Path(self.config.cache_dir) / f"{path.stem}.hash"
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        if cache_file.exists():
            return cache_file.read_text().strip() == prompt_hash
        cache_file.write_text(prompt_hash)
        return False
