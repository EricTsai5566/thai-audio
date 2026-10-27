"""Generate Thai audio for requests/*.json with edge-tts (th-TH-NiwatNeural).

Request format: {"items": [{"id": "s1", "text": "สวัสดีครับ"}, ...]}
Output: audio/<request name>/<id>.mp3 (normal) and <id>-slow.mp3 (rate -40%).
Existing files are skipped, so re-running is cheap.
"""
import asyncio
import json
import pathlib
import re
import sys

import edge_tts

VOICE = "th-TH-NiwatNeural"
SPEEDS = {"": "-10%", "-slow": "-40%"}
ROOT = pathlib.Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^[a-z0-9-]{1,40}$")


async def synth(text, rate, out):
    for attempt in range(5):
        try:
            await edge_tts.Communicate(text, VOICE, rate=rate).save(str(out))
            if out.stat().st_size > 0:
                return True
        except Exception as e:  # edge-tts sometimes returns no audio; retry
            print(f"  retry {attempt + 1} for {out.name}: {e}")
        await asyncio.sleep(2 * (attempt + 1))
    out.unlink(missing_ok=True)
    return False


async def main():
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
            for suffix, rate in SPEEDS.items():
                out = outdir / f"{iid}{suffix}.mp3"
                if out.exists() and out.stat().st_size > 0:
                    continue
                print(f"gen {name}/{out.name}")
                if not await synth(text, rate, out):
                    failed += 1
    if failed:
        print(f"{failed} files failed")
        sys.exit(1)


asyncio.run(main())
