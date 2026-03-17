"""
AI Video Pipeline - Main Entry Point
=====================================
Agentic Content Production Pipeline
Stack: Edge-TTS + Pollinations API + FFmpeg
"""

import asyncio
import json
import logging
from pathlib import Path

from agents.scene_controller import SceneController
from agents.voice_agent import VoiceAgent
from agents.visual_agent import VisualAgent
from agents.subtitle_agent import SubtitleAgent
from agents.composer_agent import ComposerAgent
from config import PipelineConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("pipeline")


async def run_pipeline(script_path: str, output_path: str = "output/final.mp4"):
    """
    Full pipeline: script JSON → final video
    """
    config = PipelineConfig()
    config.ensure_dirs()

    # Load script
    with open(script_path, "r") as f:
        script = json.load(f)

    logger.info(f"Loaded script: {len(script['scenes'])} scenes")

    # Initialize agents
    controller   = SceneController(config)
    voice_agent  = VoiceAgent(config)
    visual_agent = VisualAgent(config)
    sub_agent    = SubtitleAgent(config)
    composer     = ComposerAgent(config)

    # Step 1: Validate & enrich scenes
    scenes = controller.prepare(script["scenes"])

    # Step 2: Generate voice (async, scene by scene)
    logger.info("Phase 1: Generating voiceovers...")
    scenes = await voice_agent.process_all(scenes)

    # Step 3: Generate visuals (parallel)
    logger.info("Phase 2: Generating visuals...")
    scenes = await visual_agent.process_all(scenes)

    # Step 4: Generate subtitles
    logger.info("Phase 3: Generating subtitles...")
    srt_path = sub_agent.generate(scenes, output_path.replace(".mp4", ".srt"))

    # Step 5: Compose video
    logger.info("Phase 4: Composing final video...")
    final_video = composer.compose(scenes, output_path, srt_path)

    logger.info(f"✅ Pipeline complete → {final_video}")
    return final_video


if __name__ == "__main__":
    import sys
    script = sys.argv[1] if len(sys.argv) > 1 else "examples/sample_script.json"
    asyncio.run(run_pipeline(script))
