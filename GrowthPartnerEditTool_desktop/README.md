# Growth Partner Edit Tool — Desktop

AI video editing app for streamers and YouTubers. Runs entirely locally except for Gemini API calls.

## Requirements

- Python 3.11+
- FFmpeg installed and in PATH
- NVIDIA GPU recommended (for fast Whisper transcription)

## Development setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your API keys
python app.py
```

## Build .exe (Windows)

```bash
pip install pyinstaller
pyinstaller build.spec
# Output in dist/GrowthPartnerEditTool/
```

## API Keys

- **Gemini API key** (required): [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **Anthropic API key** (optional): [console.anthropic.com](https://console.anthropic.com)

Keys are stored locally in:
- Windows: `%APPDATA%\GrowthPartnerEditTool\settings.json`
- macOS: `~/Library/Application Support/GrowthPartnerEditTool/settings.json`
- Linux: `~/.config/GrowthPartnerEditTool/settings.json`

## Architecture

```
Video file (local)
    ↓
FFmpeg — extract audio WAV
    ↓
Whisper large-v3 (GPU) — transcription for captions
    ↓
Gemini 2.5 Flash — video analysis, finds viral moments
    ↓
Claude — selects final clips from candidates
    ↓
FFmpeg — renders output clips
    ↓
Output .mp4 files
```
