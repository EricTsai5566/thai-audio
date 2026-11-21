"""Generate Thai audio for requests/*.json with Gemini TTS (voice Puck).

Request format: {"items": [{"id": "s1", "text": "สวัสดีครับ"}, ...]}
Output: audio/<request name>/<id>.mp3 (x0.9) and <id>-slow.mp3 (x0.75), slowed by ffmpeg atempo.
Existing files are skipped unless the text changed (<id>.sha holds its hash), so re-running is cheap. Needs GEMINI_API_KEY and ffmpeg.
"""
import base64
import hashlib
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
# Gemini reads any style prompt aloud, so send bare text and slow it with ffmpeg
TEMPO = {"": 0.9, "-slow": 0.75}
GAP = 25  # free tier allows only a few requests per minute
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
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}},
        },
    }
    for attempt in range(8):
        time.sleep(GAP)
        try:
            req = urllib.request.Request(
                URL, data=json.dumps(body).encode(),
                headers={"x-goog-api-key": KEY, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=300))
            pcm = base64.b64decode(r["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            if pcm:
                return pcm
        except urllib.error.HTTPError as e:
            err = e.read().decode(errors="replace")
            print(f"  retry {attempt + 1}: HTTP {e.code} {err[:300]}")
            if "PerDay" in err:  # daily quota gone, retrying won't help
                return None
        except Exception as e:  # empty candidates, timeouts
            print(f"  retry {attempt + 1}: {e}")
        time.sleep(10 * attempt)
    return None


def to_mp3(pcm, out, tempo):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", "-",
           "-filter:a", f"atempo={tempo}", "-b:a", "64k", str(out)]
    subprocess.run(cmd, input=pcm, check=True)


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
            outs = {sfx: outdir / f"{iid}{sfx}.mp3" for sfx in TEMPO}
            sha_file = outdir / f"{iid}.sha"
            sha = hashlib.sha256(text.encode()).hexdigest()
            # audio from before .sha files existed has no hash; keep it
            stale = sha_file.exists() and sha_file.read_text().strip() != sha
            if not stale and all(p.exists() and p.stat().st_size > 0 for p in outs.values()):
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
            for sfx, out in outs.items():
                to_mp3(pcm, out, TEMPO[sfx])
            sha_file.write_text(sha)
    if failed:
        print(f"{failed} items failed")
        sys.exit(1)


main()
