# 🎬 AI_Creator

**Agentic Content Production Pipeline** — Script JSON → Full Video with Audio, Visuals & Subtitles

**Stack:** Edge-TTS · Pollinations API · FFmpeg · Python Asyncio  
**Cost:** $0 · **GPU:** Not required · **API Keys:** None needed for core pipeline

---

## 📁 Project Structure

```
ai_video_pipeline/
├── main.py                    # Entry point
├── config.py                  # All settings (one place)
├── requirements.txt
├── agents/
│   ├── scene_controller.py    # Orchestrator / data normalizer
│   ├── voice_agent.py         # Edge-TTS → .mp3 per scene
│   ├── visual_agent.py        # Pollinations API → .jpg per scene
│   ├── subtitle_agent.py      # Timing-aware .srt generation
│   ├── composer_agent.py      # FFmpeg: image+audio → video
│   └── upload_agent.py        # YouTube Data API v3 upload
├── examples/
│   └── sample_script.json     # Example input
└── output/                    # Generated (gitignored)
    ├── audio/
    ├── images/
    ├── video/
    └── cache/
```

---

## 🚀 Quick Start

### 1. Install system dependencies
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: download from https://ffmpeg.org/download.html
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the pipeline
```bash
python main.py examples/sample_script.json
```

Output: `output/final.mp4` + `output/final.srt`

---

## 📝 Input Format

```json
{
  "title": "Your Video Title",
  "scenes": [
    {
      "id": 1,
      "text": "Spoken narration for this scene.",
      "prompt": "Optional custom image prompt. If omitted, auto-built from text."
    }
  ]
}
```

---

## ⚙️ Configuration (`config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `tts_voice` | `en-US-AriaNeural` | Edge-TTS voice |
| `image_seed` | `42` | Fixed seed → reproducible images |
| `image_model` | `flux` | Pollinations model (flux / turbo) |
| `zoom_effect` | `True` | Ken Burns zoom on images |
| `image_width/height` | `1024x576` | 16:9 for video |

See full list in `config.py`.

---

## 🏗️ Architecture

```
Input JSON
    ↓
SceneController  ← normalize + validate scenes
    ↓
VoiceAgent       ← Edge-TTS async → .mp3 + duration
    ↓
VisualAgent      ← Pollinations API async → .jpg
    ↓
SubtitleAgent    ← timing-aware .srt generation
    ↓
ComposerAgent    ← FFmpeg: zoom + concat + subtitles → .mp4
    ↓
(Optional) UploadAgent → YouTube
```

**Key design decisions:**
- Audio duration = source of truth for all timing
- Fixed seed per scene = reproducible visual outputs
- Hash-based caching = skip regeneration on reruns
- Async throughout = fast even on CPU

---

## 📤 YouTube Upload (Phase 3)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project → Enable **YouTube Data API v3**
3. Create **OAuth2 credentials** → Download `client_secret.json`
4. Place in `credentials/client_secret.json`
5. Run:

```python
from agents.upload_agent import UploadAgent
from config import PipelineConfig

agent = UploadAgent(PipelineConfig())
url = agent.upload(
    "output/final.mp4",
    title="My AI Video",
    tags=["AI", "automation"],
    privacy="private"   # test with private first
)
print(url)
```

First run opens browser for OAuth. Token cached for all future runs.

---

## 🔁 Caching

Re-running with the same script skips regeneration:
- Audio: hash of scene text
- Images: hash of image prompt

Delete `output/cache/` to force full regeneration.

---

## 📦 Resume / Partial Runs

If pipeline fails mid-way, rerun — cached scenes are skipped automatically.

---

## 🗺️ Roadmap

- [x] Phase 1: Core pipeline (voice + image + video)
- [x] Phase 2: Subtitles + Ken Burns + caching
- [x] Phase 3: YouTube upload
- [ ] Phase 4: Instagram Reels (Meta Graph API)
- [ ] Phase 4: AnimateDiff for motion video
- [ ] Phase 4: Character consistency via ControlNet
