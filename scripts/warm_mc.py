"""Precalcula el Monte Carlo de la configuración por defecto y lo cachea en disco.

La web (app/utils.run_simulation) busca primero este caché y, si está, carga al
instante en vez de simular 10.000 torneos (~5 s). Lo llama la rutina diaria
después de `dia.py informe`, con los resultados ya registrados.

Replica EXACTAMENTE las entradas que usa run_simulation_with_real (mismo Elo,
mismos real_results, misma porra, mismo stats_weight) para que la clave coincida.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.dia import _load_elo_full                     # noqa: E402
from src.model.tournament_sim import run_monte_carlo        # noqa: E402
from src.model import ensemble                              # noqa: E402
from src.model.mc_runtime import (                          # noqa: E402
    disk_key, save_cached, summary_to_dict, MC_DISK_DIR,
)
from app.utils import load_all_predictions, freeze_elo      # noqa: E402  (funciones puras)

N_SIMS, SEED = 10_000, 42
USER_PORRA = ROOT / "data" / "processed" / "porra_usuario.json"


def main() -> None:
    base, elo, cfg, real = _load_elo_full()
    real_str = json.dumps(real, sort_keys=True)
    porra = json.loads(USER_PORRA.read_text(encoding="utf-8")) if USER_PORRA.exists() else None
    porra_str = json.dumps(porra, sort_keys=True) if porra else ""
    sw = cfg.stats_weight
    frozen = freeze_elo(elo)
    key = disk_key(frozen, N_SIMS, SEED, real_str, porra_str, sw)

    # Dejar solo el caché de la config por defecto (limpia claves viejas)
    if MC_DISK_DIR.exists():
        for f in MC_DISK_DIR.glob("*.json"):
            f.unlink()

    ensemble.set_stats_weight(sw)
    predictions = load_all_predictions(porra)
    summary = run_monte_carlo(dict(frozen), n_sims=N_SIMS, seed=SEED,
                              real_results=real, predictions=predictions)
    save_cached(key, summary_to_dict(summary))

    f = MC_DISK_DIR / f"{key}.json"
    print(f"✓ MC precalculado → {f.relative_to(ROOT)} "
          f"({f.stat().st_size / 1024:.0f} KB · clave {key} · sw={sw})")


if __name__ == "__main__":
    main()
