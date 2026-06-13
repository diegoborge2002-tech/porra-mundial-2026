"""Genera el boletin de audio del dia con el TTS de macOS (say) — gratis, sin creditos.

Uso:
  python scripts/make_boletin_audio.py "texto del boletin" [--date YYYY-MM-DD] [--voz Monica]
  echo "texto" | python scripts/make_boletin_audio.py

Guarda app/assets/recaps/boletin_<fecha>.mp3, que la web muestra automaticamente
(render_matchday_brief coge el boletin mas reciente por fecha de modificacion).
"""
from __future__ import annotations

import datetime
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECAP = ROOT / "app" / "assets" / "recaps"


def main() -> None:
    args = sys.argv[1:]
    voz = "Mónica"
    fecha = datetime.date.today().isoformat()
    text_parts: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--date" and i + 1 < len(args):
            fecha = args[i + 1]; i += 2
        elif args[i] == "--voz" and i + 1 < len(args):
            voz = args[i + 1]; i += 2
        else:
            text_parts.append(args[i]); i += 1

    text = " ".join(text_parts).strip() or (sys.stdin.read().strip() if not sys.stdin.isatty() else "")
    if not text:
        sys.exit("❌ Sin texto que locutar")

    RECAP.mkdir(parents=True, exist_ok=True)
    out_mp3 = RECAP / f"boletin_{fecha}.mp3"
    aiff = tempfile.NamedTemporaryFile(suffix=".aiff", delete=False).name
    try:
        subprocess.run(["say", "-v", voz, "-o", aiff, text], check=True)
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ff, "-y", "-i", aiff, "-ar", "44100", "-b:a", "128k", str(out_mp3)],
                       check=True, capture_output=True)
    finally:
        if os.path.exists(aiff):
            os.remove(aiff)
    print(f"✓ {out_mp3.name} ({round(out_mp3.stat().st_size / 1024)} KB, voz {voz})")


if __name__ == "__main__":
    main()
