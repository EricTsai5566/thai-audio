# thai-audio

尚霖每日泰文 email 用的泰文男聲音檔（Google Gemini TTS `gemini-3.8-flash-tts`，voice `Puck`；正常版 x0.9、慢速版 x0.7，用 ffmpeg atempo 放慢）。2026-11-19 起取代 Niwat。

- routine 把句子寫進 `requests/<name>.json`：`{"items": [{"id": "s1", "text": "..."}]}`
- GitHub Actions 產生 `audio/<name>/<id>.mp3` 和 `<id>-slow.mp3`
- 網址：`https://erictsai5566.github.io/thai-audio/audio/<name>/<id>.mp3`
