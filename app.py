from flask import Flask, request, send_file, render_template_string
import yt_dlp
import os
import uuid
import subprocess

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MP3 Downloader</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', sans-serif;
      background: #0f0f0f;
      color: #f0f0f0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }

    .card {
      background: #1a1a1a;
      border: 1px solid #2a2a2a;
      border-radius: 16px;
      padding: 2.5rem;
      width: 100%;
      max-width: 480px;
    }

    .icon {
      width: 48px;
      height: 48px;
      background: #1db954;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1.5rem;
    }

    .icon svg {
      width: 24px;
      height: 24px;
      fill: #000;
    }

    h1 {
      font-size: 1.4rem;
      font-weight: 600;
      color: #fff;
      margin-bottom: 0.4rem;
    }

    p.sub {
      font-size: 0.875rem;
      color: #666;
      margin-bottom: 2rem;
    }

    label {
      display: block;
      font-size: 0.8rem;
      font-weight: 500;
      color: #888;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    input[type="text"] {
      width: 100%;
      background: #111;
      border: 1px solid #2a2a2a;
      border-radius: 10px;
      padding: 0.85rem 1rem;
      font-size: 0.95rem;
      color: #f0f0f0;
      font-family: 'Inter', sans-serif;
      outline: none;
      transition: border-color 0.15s;
      margin-bottom: 1.25rem;
    }

    input[type="text"]:focus { border-color: #1db954; }
    input[type="text"]::placeholder { color: #444; }

    button {
      width: 100%;
      background: #1db954;
      color: #000;
      border: none;
      border-radius: 10px;
      padding: 0.9rem;
      font-size: 0.95rem;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      cursor: pointer;
      transition: background 0.15s, transform 0.1s;
    }

    button:hover { background: #1ed760; }
    button:active { transform: scale(0.98); }
    button:disabled { background: #333; color: #666; cursor: not-allowed; transform: none; }

    .message {
      margin-top: 1.25rem;
      border-radius: 10px;
      padding: 0.85rem 1rem;
      font-size: 0.85rem;
    }

    .message.error {
      background: #2a1010;
      border: 1px solid #5a1a1a;
      color: #ff6b6b;
    }

    .supported {
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid #2a2a2a;
      font-size: 0.8rem;
      color: #444;
      text-align: center;
    }

    .supported span { color: #555; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6z"/>
      </svg>
    </div>

    <h1>MP3 Downloader</h1>
    <p class="sub">Paste a YouTube or Spotify link to download as MP3.</p>

    <form method="POST" action="/download" onsubmit="handleSubmit(this)">
      <label for="url">Song URL</label>
      <input
        type="text"
        id="url"
        name="url"
        placeholder="https://youtube.com/watch?v=... or Spotify link"
        value="{{ url or '' }}"
        required
        autocomplete="off"
      >
      <button type="submit" id="btn">Download MP3</button>
    </form>

    {% if error %}
    <div class="message error">⚠ {{ error }}</div>
    {% endif %}

    <p class="supported">Works with <span>YouTube · Spotify · SoundCloud · and 1000+ sites</span></p>
  </div>

  <script>
    function handleSubmit(form) {
      const btn = document.getElementById('btn');
      btn.disabled = true;
      btn.textContent = 'Downloading...';
    }
  </script>
</body>
</html>
"""

# ── config ────────────────────────────────────────────────
AUDIO_QUALITY = "320"   # max MP3 quality
# ─────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/download", methods=["POST"])
def download():
    url = request.form.get("url", "").strip()
    if not url:
        return render_template_string(HTML, error="Please enter a URL.", url=url)

    out_id = str(uuid.uuid4())

    try:
        if "spotify.com" in url:
            # ── Spotify: use spotdl ──────────────────────────
            result = subprocess.run(
                [
                "spotdl", url,
                "--output", f"/tmp/{out_id}.{{title}}.mp3",
                "--format", "mp3",
                "--bitrate", "320k",
                "--audio", "youtube",
                ],
                capture_output=True,
                text=True
            )

            # find the file spotdl created
            files = [f for f in os.listdir("/tmp") if f.startswith(out_id) and f.endswith(".mp3")]
            if not files:
                error_msg = f"STDOUT: {result.stdout.strip()} | STDERR: {result.stderr.strip()}"
                return render_template_string(HTML, error=error_msg, url=url)

            mp3_path = f"/tmp/{files[0]}"
            title = files[0].replace(f"{out_id}.", "").replace(".mp3", "")

        else:
            # ── YouTube / SoundCloud / everything else: use yt-dlp ──
            out_template = f"/tmp/{out_id}.%(ext)s"
            mp3_path = f"/tmp/{out_id}.mp3"

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": AUDIO_QUALITY,
                }],
                "quiet": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "audio")

        return send_file(
            mp3_path,
            as_attachment=True,
            download_name=f"{title}.mp3",
            mimetype="audio/mpeg"
        )

    except Exception as e:
        return render_template_string(HTML, error=str(e), url=url)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✓ MP3 Downloader running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port)
