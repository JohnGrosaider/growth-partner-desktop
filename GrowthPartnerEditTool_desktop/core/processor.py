"""
Core video processing logic for Growth Partner Edit Tool (Desktop)
Extracted from main.py — runs entirely locally except for Gemini API calls.
"""
import os
import json
import math
import subprocess
import asyncio
import uuid
import time
import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable, Optional


# ── API clients (lazy init) ────────────────────────────────────────────────

_gemini_client = None
_anthropic_client = None
_whisper_model = None


def init_clients(gemini_key: str, anthropic_key: str):
    global _gemini_client, _anthropic_client
    if gemini_key:
        from google import genai
        _gemini_client = genai.Client(api_key=gemini_key)
    if anthropic_key:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=anthropic_key)


def get_whisper_model(model_size: str = "large-v3"):
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        device = "cuda" if _cuda_available() else "cpu"
        compute = "float16" if device == "cuda" else "int8"
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute)
    return _whisper_model


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# ── Progress callback type ─────────────────────────────────────────────────

ProgressFn = Callable[[str, int], None]  # (message, percent)


# ── Main processing entry point ────────────────────────────────────────────

async def process_video(
    video_path: str,
    prompt: str,
    output_dir: str,
    content_type: str,          # "short_clip" | "video" | "stream"
    output_format: str = "mp4",
    quality: str = "1080p",
    progress: ProgressFn = None,
    job_id: str = None,
) -> dict:
    """
    Main processing pipeline:
    1. Probe video duration
    2. Extract audio (WAV)
    3. Whisper peak detection (GPU if available)
    4. Gemini 2.5 Flash chunk analysis
    5. FFmpeg render selected clips
    Returns dict with output file paths.
    """
    job_id = job_id or str(uuid.uuid4())[:8]
    os.makedirs(output_dir, exist_ok=True)
    tmp_dir = os.path.join(output_dir, f"tmp_{job_id}")
    os.makedirs(tmp_dir, exist_ok=True)

    def log(msg: str, pct: int = -1):
        print(f"[{job_id}] {msg}")
        if progress:
            progress(msg, pct)

    try:
        # ── Step 1: Probe video ────────────────────────────────────────────
        log("Reading video info...", 2)
        video_duration = _probe_duration(video_path)
        if not video_duration:
            raise Exception("Could not read video duration. Is FFmpeg installed?")
        log(f"Video duration: {_fmt_duration(video_duration)}", 5)

        # ── Step 2: Extract audio ──────────────────────────────────────────
        log("Extracting audio...", 8)
        audio_path = os.path.join(tmp_dir, "audio.wav")
        _extract_audio(video_path, audio_path)

        # ── Step 3: Whisper transcription (for captions or context) ────────
        p_lower = prompt.lower()
        needs_captions = any(w in p_lower for w in ["caption", "captions", "subtitle", "subtitles", "titulky"])
        wants_best = any(w in p_lower for w in [
            "best moment", "best moments", "highlight", "highlights", "funny", "funniest",
            "hype", "exciting", "nejlepší", "vtipný", "vtipné"
        ])

        segments = []
        if needs_captions or (wants_best and not _gemini_client):
            log("Transcribing with Whisper...", 12)
            segments = await _transcribe_whisper(audio_path, job_id, log)

        # ── Step 4: Gemini video analysis ──────────────────────────────────
        peak_candidates = ""
        if wants_best and _gemini_client:
            num_match = re.search(r'(\d+)\s*(clip|moment|video|highlight|funny|part)', p_lower)
            num_clips = int(num_match.group(1)) if num_match else 3
            num_clips = max(1, min(num_clips, 10))

            log("Analyzing video with Gemini...", 20)
            peak_candidates = await _gemini_chunked_analysis(
                video_path, prompt, num_clips, video_duration, job_id, tmp_dir, log
            )

        if not peak_candidates and segments:
            log("Building candidates from transcript...", 45)
            peak_candidates = _build_candidates_from_whisper(segments, video_duration, job_id)

        # ── Step 5: Claude selection ────────────────────────────────────────
        log("Selecting best clips...", 50)
        from core.ai_logic import build_ai_prompt
        ai_prompt = build_ai_prompt(
            content_type=content_type,
            user_prompt=prompt,
            stream_context="",
            video_duration=video_duration,
            segments=segments,
            peak_candidates=peak_candidates,
        )
        instructions = _claude_select(ai_prompt)

        # ── Step 6: Render clips ────────────────────────────────────────────
        clips = instructions.get("clips", [])
        add_captions = instructions.get("add_captions", False)
        vertical_format = instructions.get("vertical_format", False)
        effects = instructions.get("effects", [])
        add_music = instructions.get("add_music", False)

        output_files = []
        for i, clip in enumerate(clips):
            start = float(clip.get("start", 0))
            end = float(clip.get("end", video_duration))
            label = clip.get("label", f"clip_{i+1}").replace(" ", "_")

            if end - start < 2:
                log(f"Skipping clip {i+1} — too short ({end-start:.1f}s)", -1)
                continue

            pct = 55 + int((i / max(len(clips), 1)) * 40)
            log(f"Rendering clip {i+1}/{len(clips)}: {label} ({int(end-start)}s)...", pct)

            out_path = os.path.join(output_dir, f"{label}.mp4")
            srt_path = os.path.join(tmp_dir, f"{label}.srt") if add_captions and segments else None

            if srt_path:
                _generate_srt(segments, srt_path, start, end)

            _render_clip(
                video_path=video_path,
                start=start, end=end,
                out_path=out_path,
                quality=quality,
                vertical=vertical_format,
                effects=effects,
                srt_path=srt_path,
            )
            if os.path.exists(out_path):
                output_files.append({"path": out_path, "label": label, "duration": end - start})

        log("Done!", 100)
        return {
            "success": True,
            "files": output_files,
            "description": instructions.get("description", ""),
        }

    except Exception as e:
        log(f"Error: {e}", -1)
        return {"success": False, "error": str(e), "files": []}
    finally:
        # Clean up temp files
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


# ── Video utilities ────────────────────────────────────────────────────────

def _probe_duration(video_path: str) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ], capture_output=True, text=True, timeout=30)
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def _extract_audio(video_path: str, audio_path: str):
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        audio_path, "-y", "-loglevel", "error"
    ], capture_output=True, timeout=7200, check=True)


def _fmt_duration(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"


# ── Whisper transcription ──────────────────────────────────────────────────

async def _transcribe_whisper(audio_path: str, job_id: str, log: ProgressFn) -> list:
    loop = asyncio.get_event_loop()

    def _run():
        model = get_whisper_model()
        log("Whisper model loaded, transcribing...", 15)
        segments, _ = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            language=None,
        )
        result = []
        for seg in segments:
            result.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text.strip(),
            })
        return result

    segments = await loop.run_in_executor(None, _run)
    log(f"Whisper done: {len(segments)} segments", 18)
    return segments


# ── Gemini chunked analysis ────────────────────────────────────────────────

CHUNK_SECONDS = 2700  # 45 min per chunk

async def _gemini_chunked_analysis(
    video_path: str,
    user_prompt: str,
    num_clips: int,
    video_duration: float,
    job_id: str,
    tmp_dir: str,
    log: ProgressFn,
) -> str:
    loop = asyncio.get_event_loop()

    # Transcode to 360p
    log("Transcoding to 360p for Gemini...", 22)
    low_res = os.path.join(tmp_dir, "video_360p.mp4")
    timeout = max(600, int(video_duration * 0.5))
    try:
        await loop.run_in_executor(None, lambda: subprocess.run([
            "ffmpeg", "-i", video_path,
            "-vf", "scale=-2:360",
            "-c:v", "libx264", "-crf", "28", "-preset", "fast",
            "-c:a", "aac", "-b:a", "64k",
            "-y", low_res
        ], capture_output=True, timeout=timeout, check=True))
    except Exception as e:
        log(f"Transcode failed: {e}", -1)
        return ""

    size_mb = os.path.getsize(low_res) / (1024 * 1024)
    log(f"360p ready: {size_mb:.0f}MB", 28)

    # Split into chunks if needed
    if video_duration <= CHUNK_SECONDS:
        chunk_jobs = [(low_res, 0.0, video_duration, "full video")]
    else:
        n = math.ceil(video_duration / CHUNK_SECONDS)
        log(f"Splitting into {n} chunks...", 30)
        chunk_jobs = []
        for i in range(n):
            c_start = i * CHUNK_SECONDS
            c_dur = min(CHUNK_SECONDS, video_duration - c_start)
            c_path = os.path.join(tmp_dir, f"chunk_{i:02d}.mp4")
            result = await loop.run_in_executor(None, lambda s=int(c_start), d=int(c_dur), p=c_path: subprocess.run([
                "ffmpeg", "-ss", str(s), "-i", low_res,
                "-t", str(d), "-c", "copy", "-y", p
            ], capture_output=True, timeout=120))
            if os.path.exists(c_path) and os.path.getsize(c_path) > 0:
                chunk_jobs.append((c_path, c_start, c_dur, f"chunk {i+1}/{n}"))

    # Analyze chunks
    total = len(chunk_jobs)
    all_moments = []

    async def analyze_chunk(idx, c_path, c_start, c_dur, label):
        if idx > 0:
            await asyncio.sleep(idx * 4)  # stagger to avoid rate limits
        pct = 32 + int((idx / total) * 30)
        log(f"Gemini analyzing {label}...", pct)
        result = await loop.run_in_executor(
            None, _analyze_one_chunk, c_path, user_prompt, num_clips, c_start, c_dur, job_id, label
        )
        return result

    results = await asyncio.gather(*[
        analyze_chunk(i, cp, cs, cd, lb)
        for i, (cp, cs, cd, lb) in enumerate(chunk_jobs)
    ], return_exceptions=True)

    for r in results:
        if isinstance(r, Exception):
            log(f"Chunk error: {r}", -1)
        elif r:
            all_moments.extend(r)

    if not all_moments:
        log("Gemini found no moments", -1)
        return ""

    all_moments.sort(key=lambda m: m["start"])
    log(f"Gemini found {len(all_moments)} candidates", 63)

    # Format candidates string for Claude
    lines = [
        f"CLIP CANDIDATES — {len(all_moments)} moments from Gemini video analysis.",
        "Copy start/end EXACTLY.\n"
    ]
    for i, m in enumerate(all_moments):
        pt = float(m["peak_time"])
        mm, ss = int(pt // 60), int(pt % 60)
        lines.append(
            f"CANDIDATE {i+1}: peak@{mm}:{ss:02d} start={m['start']:.0f} end={m['end']:.0f}\n"
            f"  REASON: {m.get('reason', '')}\n"
            f"  LABEL: {m.get('label', 'moment')}"
        )
    return "\n".join(lines)


def _analyze_one_chunk(
    chunk_path: str, user_prompt: str, num_clips: int,
    chunk_offset: float, chunk_duration: float, job_id: str, label: str
) -> list:
    """Synchronous: upload chunk to Gemini Files API and analyze."""
    from google.genai import types as _gtypes

    print(f"[{job_id}] [{label}] Uploading to Gemini...")
    with open(chunk_path, "rb") as f:
        video_file = _gemini_client.files.upload(file=f, config={"mime_type": "video/mp4"})

    try:
        for _ in range(60):
            if video_file.state.name != "PROCESSING":
                break
            time.sleep(5)
            video_file = _gemini_client.files.get(name=video_file.name)

        if video_file.state.name != "ACTIVE":
            raise Exception(f"Gemini file not active: {video_file.state.name}")

        prompt = f"""You are selecting viral clips from a gaming stream for TikTok/Shorts.

USER REQUEST: "{user_prompt}"

Find moments where BOTH are true:
1. Something happens (fail, surprise, funny situation, unexpected event)
2. Streamer has STRONG reaction (laughs hard, screams, loses composure)

SKIP: calm chat, normal gameplay, mild reactions.

Clip structure: HEAD (5-15s context before) → PEAK (reaction) → TAIL (reaction finishes)
Never cut mid-laugh or mid-sentence.

Return ONLY a JSON array:
[{{"peak_time": 45.0, "start": 30.0, "end": 78.0, "label": "fail_reaction", "reason": "streamer falls and can't stop laughing"}}]

Rules:
- Timestamps relative to THIS segment (0 to {chunk_duration:.0f}s)
- Clip length: 25-60 seconds
- Return [] if nothing qualifies
- Max {num_clips} clips, quality over quantity"""

        response = _gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[video_file, prompt],
            config=_gtypes.GenerateContentConfig(
                max_output_tokens=1024,
                system_instruction="You are a JSON API. Respond ONLY with a valid JSON array. No markdown, no text. Only [] or [{...}]."
            )
        )

        text = response.text.strip()
        bs = text.find("[")
        be = text.rfind("]")
        if bs == -1 or be <= bs:
            return []
        text = text[bs:be+1]
        text = re.sub(r'\n(?!["\{\}\[\]])', ' ', text)

        try:
            moments = json.loads(text)
        except json.JSONDecodeError:
            clean = re.sub(r'"reason"\s*:\s*"[^"]*(?:"[^,\}]*)*"', '"reason": ""', text)
            try:
                moments = json.loads(clean)
            except Exception:
                return []

        result = []
        for m in moments:
            try:
                ls = max(0.0, float(m.get("start", float(m["peak_time"]) - 20)))
                le = min(float(m.get("end", float(m["peak_time"]) + 40)), chunk_duration)
                if le - ls < 20:
                    le = ls + 40
                if le - ls > 60:
                    le = ls + 60
                le = min(le, chunk_duration)
                if le - ls < 15:
                    continue
                result.append({
                    "peak_time": float(m["peak_time"]) + chunk_offset,
                    "start": round(ls + chunk_offset, 1),
                    "end": round(le + chunk_offset, 1),
                    "label": m.get("label", "moment"),
                    "reason": m.get("reason", ""),
                })
            except (KeyError, ValueError):
                continue

        print(f"[{job_id}] [{label}] Found {len(result)} clips")
        return result

    finally:
        try:
            _gemini_client.files.delete(name=video_file.name)
        except Exception:
            pass


# ── Whisper fallback candidates ────────────────────────────────────────────

def _build_candidates_from_whisper(segments: list, video_duration: float, job_id: str) -> str:
    KEYWORDS = {
        "kurva", "do prdele", "ty vole", "kámo", "bože", "sakra",
        "nemožný", "šílenej", "vážně", "haha", "ahahah",
        "no way", "what", "holy", "insane", "crazy", "omg",
        "let's go", "wtf", "ne ne ne", "jéé", "počkej",
    }
    WINDOW = 30
    windows = {}
    for seg in segments:
        text = seg["text"].lower()
        words = text.split()
        dur = max(seg["end"] - seg["start"], 0.01)
        score = min(len(words) / dur / 3.0, 1.0) * 10
        score += min(sum(3 for kw in KEYWORDS if kw in text), 15)
        score += min(text.count("!") * 2 + text.count("?"), 5)
        w = int(seg["start"] / WINDOW)
        if w not in windows:
            windows[w] = {"score": 0.0, "time": seg["start"]}
        windows[w]["score"] += score

    ranked = sorted(windows.values(), key=lambda x: x["score"], reverse=True)
    selected = []
    for w in ranked:
        t = w["time"] + WINDOW / 2
        if not any(abs(t - s["time"]) < 60 for s in selected):
            selected.append({"time": t, "score": w["score"]})
        if len(selected) >= 15:
            break

    selected.sort(key=lambda x: x["time"])
    lines = [f"CLIP CANDIDATES — {len(selected)} moments from speech analysis.\n"]
    for i, p in enumerate(selected):
        t = p["time"]
        start = max(0, t - 20)
        end = min(video_duration, t + 40)
        mm, ss = int(t // 60), int(t % 60)
        lines.append(f"CANDIDATE {i+1}: peak@{mm}:{ss:02d} start={start:.0f} end={end:.0f}")
    return "\n".join(lines)


# ── Claude selection ───────────────────────────────────────────────────────

def _claude_select(ai_prompt: str) -> dict:
    if not _anthropic_client:
        # Fallback: first 5 minutes
        return {"clips": [{"start": 0, "end": 300, "label": "clip_1"}],
                "add_captions": False, "vertical_format": False,
                "add_music": False, "effects": [], "output_type": "clips",
                "description": "Fallback: no Claude key"}

    response = _anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": ai_prompt}]
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        return {"clips": [], "add_captions": False, "vertical_format": False,
                "add_music": False, "effects": [], "output_type": "clips",
                "description": "Parse error"}


# ── FFmpeg render ──────────────────────────────────────────────────────────

def _render_clip(
    video_path: str, start: float, end: float,
    out_path: str, quality: str = "1080p",
    vertical: bool = False, effects: list = None,
    srt_path: str = None,
):
    crf = {"720p": 23, "1080p": 20, "4k": 18}.get(quality, 20)
    duration = end - start

    vf_parts = []
    if vertical:
        vf_parts.append("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
    else:
        vf_parts.append("scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2")

    if effects:
        if "cinematic" in effects:
            vf_parts.append("curves=preset=warm")
        if "sharpen" in effects:
            vf_parts.append("unsharp=5:5:1.0:5:5:0.0")
        if "vignette" in effects:
            vf_parts.append("vignette=PI/4")
        if "zoom" in effects:
            vf_parts.append(f"zoompan=z='min(zoom+0.0005,1.1)':d={int(duration*25)}:s=1920x1080")
        if "fade" in effects:
            fade_dur = min(1.5, duration * 0.1)
            vf_parts.append(f"fade=t=in:st=0:d={fade_dur}")
            vf_parts.append(f"fade=t=out:st={duration - fade_dur}:d={fade_dur}")

    if srt_path and os.path.exists(srt_path):
        srt_escaped = srt_path.replace(":", "\\:").replace("'", "\\'")
        vf_parts.append(f"subtitles='{srt_escaped}'")

    vf = ",".join(vf_parts) if vf_parts else "null"

    cmd = [
        "ffmpeg",
        "-ss", str(start), "-i", video_path,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-crf", str(crf), "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-y", out_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=3600)


# ── SRT generation ─────────────────────────────────────────────────────────

def _generate_srt(segments: list, srt_path: str, clip_start: float, clip_end: float):
    relevant = [s for s in segments if s["end"] > clip_start and s["start"] < clip_end]
    lines = []
    for i, seg in enumerate(relevant):
        s = max(0, seg["start"] - clip_start)
        e = min(clip_end - clip_start, seg["end"] - clip_start)
        lines.append(str(i + 1))
        lines.append(f"{_fmt_srt(s)} --> {_fmt_srt(e)}")
        lines.append(seg["text"])
        lines.append("")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _fmt_srt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
