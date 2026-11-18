"""Generate Thai audio for requests/*.json with Gemini TTS (voice Puck).

Request format: {"items": [{"id": "s1", "text": "สวัสดีครับ"}, ...]}
Output: audio/<request name>/<id>.mp3 (normal) and <id>-slow.mp3 (ffmpeg atempo).
Existing files are skipped, so re-running is cheap. Needs GEMINI_API_KEY and ffmpeg.
"""
import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

MODEL = "gemini-3.8-flash-tts"
VOICE = "Puck"
SLOW_TEMPO = 0.75
STYLE = (
    "Say the following Thai text in natural, conversational Bangkok Thai, "
    "like a friendly Thai man talking to a friend. Clear and a little slower "
    "than normal for a learner. Read only the text, nothing else:\n\n"
)
MAX_CHARS = 1200  # longer texts are split at spaces and joined
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^[a-z0-9-]{1,40}$")
KEY = os.environ["GEMINI_API_KEY"]


def chunks(text):
    parts, cur = [], ""
    for word in text.split():
        if cur and len(cur) + len(word) + 1 > MAX_CHARS:
            parts.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return parts + [cur] if cur else parts


def tts(text):
    body = {
        "contents": [{"parts": [{"text": STYLE + text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    }
    for attempt in range(6):
        try:
            req = urllib.request.Request(
                URL, data=json.dumps(body).encode(),
                headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=300))
            pcm = base64.b64decode(r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            if pcm:
                return pcm
        except urllib.error.HTTPError as e:
            print(f"  retry {attempt + 1}: HTTP {e.code} {e.read()[:200]!r}")
            if e.code == 429:  # free-tier rate limit
                time.sleep(30 * (attempt + 1))
                continue
        except Exception as e:  # empty candidates, timeouts
            print(f"  retry {attempt + 1}: {e}")
        time.sleep(5 * (attempt + 1))
    return None


def to_mp3(pcm, out, tempo=None):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-"]
    if tempo:
        cmd += ["-filter:a", f"atempo={tempo}"]
    subprocess.run(cmd + ["-b:a", "64k", str(out)], input=pcm, check=True)


def main():
    failed = 0
    for req in sorted((ROOT / "requests").glob("*.json")):
        name = req.stem
        items = json.loads(req.read_text(encoding="utf-8")).get("items", [])
        outdir = ROOT / "audio" / name
        outdir.mkdir(parents=True, exist_ok=True)
        for item in items:
            iid, text = str(item.get("id", "")), str(item.get("text", "")).strip()
            if not ID_RE.match(iid) or not text:
                print(f"skip bad item in {req.name}: {item!r}")
                continue
            normal, slow = outdir / f"{iid}.mp3", outdir / f"{iid}-slow.mp3"
            if all(p.exists() and p.stat().st_size > 0 for p in (normal, slow)):
                continue
            print(f"gen {name}/{iid}")
            pcm = b""
            for part in chunks(text):
                got = tts(part)
                if got is None:
                    pcm = None
                    break
                pcm += got
            if not pcm:
                failed += 1
                continue
            to_mp3(pcm, normal)
            to_mp3(pcm, slow, SLOW_TEMPO)
    if failed:
        print(f"{failed} items failed")
        sys.exit(1)


main()
