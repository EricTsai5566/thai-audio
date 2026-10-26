# thai-audio

尚霖每日泰文 email 用的泰文男聲音檔（Microsoft Edge TTS `th-TH-NiwatNeural`，用 [edge-tts](https://github.com/rany2/edge-tts) 產生）。

- routine 把句子寫進 `requests/<name>.json`：`{"items": [{"id": "s1", "text": "..."}]}`
- GitHub Actions 產生 `audio/<name>/<id>.mp3` 和 `<id>-slow.mp3`
- 網址：`https://erictsai5566.github.io/thai-audio/audio/<name>/<id>.mp3`
