"""Prepara la foto de campeones para la portada y (opcionalmente) despliega.

La foto va embebida en base64 dentro del HTML del hero, así que el peso cuenta
directamente en lo que tarda en pintar la portada. Este script la deja lista:
recorte al formato del hueco, tamaño sensato y compresión hasta ~200 KB.

Uso:
    # 1. Deja el archivo (cualquier nombre) en app/assets/custom/
    # 2. Ejecuta:
    python scripts/add_photo.py                      # busca campeones.*
    python scripts/add_photo.py ~/Downloads/foto.jpg # o le pasas la ruta
    python scripts/add_photo.py --deploy             # y además despliega
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CUSTOM = ROOT / "app" / "assets" / "custom"
DST = CUSTOM / "campeones.jpg"

TARGET_KB = 220          # tope razonable para ir en base64 en la portada
W = 1400                 # ancho final; el hueco se ve a ~480 px, sobra margen
ASPECT = 4 / 3           # el marco del hero está pensado apaisado 4:3


def find_source(arg: str | None) -> pathlib.Path:
    if arg:
        p = pathlib.Path(arg).expanduser()
        if not p.exists():
            sys.exit(f"❌ No existe: {p}")
        return p
    for ext in ("jpg", "jpeg", "png", "webp", "JPG", "JPEG", "PNG", "HEIC"):
        hits = sorted(CUSTOM.glob(f"campeones.{ext}"))
        if hits:
            return hits[0]
    sys.exit(
        "❌ No encuentro la foto.\n"
        f"   Déjala en {CUSTOM.relative_to(ROOT)}/campeones.jpg\n"
        "   o pásame la ruta: python scripts/add_photo.py ~/Downloads/foto.jpg"
    )


def probe(p: pathlib.Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True,
    ).stdout.strip()
    w, h = (int(x) for x in out.split(",")[:2])
    return w, h


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    deploy = "--deploy" in sys.argv
    src = find_source(args[0] if args else None)

    w, h = probe(src)
    print(f"📷 origen: {src.name} · {w}×{h} · {src.stat().st_size/1024:.0f} KB")

    # Recorte al 4:3 del marco. Si la foto es más apaisada (16:9, como las de
    # agencia), recortamos por los lados y dejamos el centro-arriba, que es
    # donde suelen estar el trofeo y los brazos en alto.
    if w / h > ASPECT:
        ch = h
        cw = int(round(h * ASPECT))
        cx = (w - cw) // 2
        cy = 0
    else:
        cw = w
        ch = int(round(w / ASPECT))
        cx = 0
        cy = int((h - ch) * 0.30)          # un pelín por encima del centro
    print(f"✂️  recorte 4:3 → {cw}×{ch} desde ({cx},{cy})")

    tmp = CUSTOM / "_campeones_tmp.jpg"
    # bajamos calidad progresivamente hasta entrar en el presupuesto de peso
    for q in (3, 5, 7, 9, 12, 16):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(src),
             "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale={W}:-1",
             "-q:v", str(q), str(tmp)],
            check=True,
        )
        kb = tmp.stat().st_size / 1024
        if kb <= TARGET_KB:
            break
    print(f"🗜️  comprimida: {kb:.0f} KB (q={q})")

    if src.resolve() == DST.resolve():
        src_backup = CUSTOM / "campeones_original.jpg"
        if not src_backup.exists():
            shutil.copy(src, src_backup)
            print(f"💾 original guardado como {src_backup.name}")
    shutil.move(tmp, DST)
    print(f"✅ listo: {DST.relative_to(ROOT)}")

    if deploy:
        print("\n🚀 desplegando…")
        subprocess.run([sys.executable, "scripts/deploy_hf.py",
                        "Foto de campeones en la portada"], cwd=ROOT, check=True)
    else:
        print("\nPara publicarla:  python scripts/deploy_hf.py \"Foto de campeones\"")


if __name__ == "__main__":
    main()
