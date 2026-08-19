"""Genera el metraje BASE de la película con ffmpeg, a coste cero.

Cada clip es un "hueco" con nombre fijo en film/assets/. Si el usuario genera el
clip equivalente con Higgsfield y lo deja ahí, este script NO lo pisa: solo
rellena lo que falte. Así la película está completa desde el minuto uno y va
mejorando según lleguen los clips buenos.

Uso:
    python scripts/build_footage.py            # rellena solo los que faltan
    python scripts/build_footage.py --force    # regenera el metraje base
                                               # (nunca toca clips ajenos)

Fuentes: app/assets/custom/{hero.mp4, engine.jpg, header_strip.jpg, map_motif.jpg,
banner_hero.jpg, bg_texture_min.jpg}
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "app" / "assets" / "custom"
OUT = ROOT / "film" / "assets"
STAMP = OUT / ".generated.json"   # qué clips generamos nosotros

W, H, FPS = 1600, 900, 25


def run(args: list[str]) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise SystemExit(f"❌ ffmpeg falló: {' '.join(args[:8])}…")


def ken_burns(img: pathlib.Path, dst: pathlib.Path, secs: int,
              grade: str, zoom_from: float = 1.0, zoom_to: float = 1.18,
              pan: str = "center") -> None:
    """Un plano con zoom/paneo lento a partir de una imagen fija."""
    frames = secs * FPS
    # zoompan trabaja sobre un lienzo ampliado para que el zoom no pixele
    zexpr = f"{zoom_from}+({zoom_to}-{zoom_from})*on/{frames}"
    if pan == "left":
        xy = "x='0':y='ih/2-(ih/zoom/2)'"
    elif pan == "right":
        xy = "x='iw-iw/zoom':y='ih/2-(ih/zoom/2)'"
    else:
        xy = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"

    vf = (
        f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
        f"crop={W*2}:{H*2},"
        f"zoompan=z='{zexpr}':{xy}:d={frames}:s={W}x{H}:fps={FPS},"
        f"{grade},"
        f"fade=t=in:st=0:d=0.8,fade=t=out:st={secs-0.8}:d=0.8"
    )
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-vf", vf,
         "-t", str(secs), "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-preset", "slow", "-crf", "26", "-movflags", "+faststart",
         "-an", str(dst)])


def from_video(src: pathlib.Path, dst: pathlib.Path, secs: int, grade: str,
               scrub: bool = False) -> None:
    """Reencodea el hero con un gradado distinto; `scrub` mete un keyframe por
    frame para que el seek por scroll sea instantáneo."""
    # el hero dura 10 s: lo ralentizamos para llegar a `secs` sin cortar
    src_dur = 10.0
    factor = secs / src_dur
    vf = f"setpts={factor:.3f}*PTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{grade}"
    args = ["ffmpeg", "-y", "-i", str(src), "-vf", vf, "-t", str(secs),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow",
            "-crf", "26", "-movflags", "+faststart", "-an"]
    if scrub:
        # keyframe en cada frame: pesa más, pero el scrubbing va fino
        args += ["-g", "1", "-keyint_min", "1", "-sc_threshold", "0", "-crf", "28"]
    args.append(str(dst))
    run(args)


def wipe_light(dst: pathlib.Path) -> None:
    """Barrido de luz sobre negro puro, generado proceduralmente."""
    secs = 2
    # una banda diagonal luminosa que cruza el encuadre
    expr = (
        f"color=c=black:s={W}x{H}:d={secs}:r={FPS},"
        f"geq="
        f"r='255*exp(-pow((X+0.35*Y-(-0.5+1.9*T/{secs})*{W*1.5})/{W*0.055},2))':"
        f"g='220*exp(-pow((X+0.35*Y-(-0.5+1.9*T/{secs})*{W*1.5})/{W*0.055},2))':"
        f"b='120*exp(-pow((X+0.35*Y-(-0.5+1.9*T/{secs})*{W*1.5})/{W*0.055},2))',"
        f"gblur=sigma=14"
    )
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", expr, "-t", str(secs),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow",
         "-crf", "28", "-movflags", "+faststart", "-an", str(dst)])


# gradados (filtros de color) por capítulo
GRADE_GOLD = "eq=contrast=1.10:saturation=1.30:gamma=1.22:brightness=0.05,colorbalance=rm=0.16:gm=0.06:bm=-0.12"
GRADE_COLD = "eq=contrast=1.02:saturation=0.60:gamma=1.28:brightness=0.04,colorbalance=rm=-0.14:gm=-0.02:bm=0.22"
GRADE_CYAN = "eq=contrast=1.10:saturation=1.15:gamma=1.15,colorbalance=rm=-0.10:bm=0.16"
GRADE_DARK = "eq=contrast=1.05:saturation=0.75:brightness=-0.06"


def main() -> None:
    force = "--force" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    mine = set(json.loads(STAMP.read_text()) if STAMP.exists() else [])

    hero = SRC / "hero.mp4"
    plan = [
        # (nombre, función generadora)
        ("cap0_final.mp4",   lambda p: from_video(hero, p, 12, GRADE_GOLD, scrub=True)),
        ("cap1_mayo.mp4",    lambda p: from_video(hero, p, 8, GRADE_COLD)),
        ("cap2_partidos.mp4", lambda p: ken_burns(SRC / "header_strip.jpg", p, 8, GRADE_CYAN, 1.0, 1.22, "left")),
        ("cap3_montana.mp4", lambda p: ken_burns(SRC / "map_motif.jpg", p, 8, GRADE_CYAN, 1.15, 1.0)),
        ("cap4_juicio.mp4",  lambda p: ken_burns(SRC / "engine.jpg", p, 12, GRADE_CYAN, 1.0, 1.2)),
        ("cap5_archivo.mp4", lambda p: ken_burns(SRC / "bg_texture_min.jpg", p, 8, GRADE_DARK, 1.1, 1.0)),
        ("wipe_light.mp4",   wipe_light),
    ]

    made, kept, skipped = [], [], []
    for name, fn in plan:
        dst = OUT / name
        if dst.exists():
            if name not in mine:
                skipped.append(name)      # es un clip del usuario: intocable
                continue
            if not force:
                kept.append(name)
                continue
        print(f"🎬 {name} …", flush=True)
        try:
            fn(dst)
            made.append(name)
        except SystemExit as e:
            print(f"   ⚠️  {e}")

    STAMP.write_text(json.dumps(sorted(set(mine) | set(made))))

    print()
    if made:    print(f"✅ generados: {', '.join(made)}")
    if kept:    print(f"↩️  ya estaban (base): {', '.join(kept)}")
    if skipped: print(f"🎨 clips tuyos, respetados: {', '.join(skipped)}")
    total = sum(p.stat().st_size for p in OUT.glob("*.mp4"))
    print(f"📦 film/assets: {total/1e6:.1f} MB en {len(list(OUT.glob('*.mp4')))} clips")


if __name__ == "__main__":
    main()
