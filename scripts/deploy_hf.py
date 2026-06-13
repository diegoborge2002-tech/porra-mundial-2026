"""Despliega el repo al Space de Hugging Face vía API (maneja binarios con Xet).

`git push hf main` RECHAZA binarios (png/wav del banner y los recaps) si no van
por LFS. Este `upload_folder` los sube por Xet automáticamente, sin git-lfs local
y sin reescribir historia. Es el método de deploy del proyecto.

Uso:
    python scripts/deploy_hf.py ["mensaje de commit"]

Requiere estar logueado: `hf auth login` (token Write, queda cacheado).
"""
from __future__ import annotations

import sys
from huggingface_hub import HfApi

REPO = "diegoborge/porra-mundial-2026"

# Mismo espíritu que .gitignore (fnmatch: '*' también cruza '/')
IGNORE = [
    ".git/*",
    "scratch/*",
    "notebooks/*",
    "informes_tacticos/*",
    "*__pycache__*",
    "*.pyc",
    "*.log",
    ".claude/*",
    ".streamlit/secrets.toml",
]


def main() -> None:
    msg = sys.argv[1] if len(sys.argv) > 1 else "Deploy: actualización"
    api = HfApi()
    api.upload_folder(
        folder_path=".",
        repo_id=REPO,
        repo_type="space",
        ignore_patterns=IGNORE,
        commit_message=msg,
    )
    print(f"✅ Desplegado a https://huggingface.co/spaces/{REPO}")
    print("   App: https://diegoborge-porra-mundial-2026.hf.space (rebuild ~40 s)")


if __name__ == "__main__":
    main()
