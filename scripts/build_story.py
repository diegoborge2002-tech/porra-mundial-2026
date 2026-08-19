"""Hornea `film/story.json`: todos los datos de la retrospectiva, congelados.

El Mundial terminó, así que los datos ya no cambian. En vez de calcularlos en vivo
(que es lo que obliga a tener Streamlit detrás), los precalculamos UNA vez y la
película queda como un sitio 100% estático, desplegable en Vercel.

Uso:
    python scripts/build_story.py

Lee: real_results.json, snapshots/, actualidad.json, elo_ratings.csv
Escribe: film/story.json
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from src.data.snapshots import list_snapshots  # noqa: E402
from src.data.team_profile import ISO_CODES  # noqa: E402
from src.model import ensemble as _ens  # noqa: E402
from src.model.biases import BiasesConfig  # noqa: E402
from src.model.calibration import aggregate_metrics, reliability_bins  # noqa: E402
from src.model.elo import train_elo  # noqa: E402
from src.model.live_diagnostics import compute_match_diagnostics  # noqa: E402
from src.data.team_names import EN_TO_ES  # noqa: E402
from src.tournament.groups import ALL_TEAMS  # noqa: E402

OUT = ROOT / "film" / "story.json"
REAL = ROOT / "data" / "processed" / "real_results.json"
ACTUALIDAD = ROOT / "data" / "processed" / "actualidad.json"
RESULTS_CSV = ROOT / "data" / "raw" / "results.csv"
RECAPS = ROOT / "app" / "assets" / "recaps"

ROUND_LABEL = {
    "r32": "Dieciseisavos", "r16": "Octavos", "qf": "Cuartos",
    "sf": "Semifinales", "third": "3er puesto", "final": "Final",
}


def _base_elo() -> dict[str, float]:
    """Elo pre-Mundial, idéntico al que usa la web (sin resultados reales)."""
    cfg = BiasesConfig.load()
    _ens.set_stats_weight(cfg.stats_weight)
    results = pd.read_csv(RESULTS_CSV)
    results["date"] = pd.to_datetime(results["date"])
    train = results[results["date"] < pd.Timestamp("2026-05-21")].dropna(
        subset=["home_score", "away_score"])
    ratings = train_elo(train, decay_old_matches=True, half_life=cfg.half_life)
    es_to_en = {v: k for k, v in EN_TO_ES.items()}
    base = {t: ratings.get(es_to_en.get(t, t), 1500.0) for t in ALL_TEAMS}
    return cfg.apply_to(base), cfg


def _iso(team: str) -> str:
    return ISO_CODES.get(team, "un")


def _all_matches(real: dict) -> list[dict]:
    """Los 104 partidos en una lista plana y ordenada."""
    out = []
    for key, sc in (real.get("group_matches") or {}).items():
        if sc and len(sc) == 2:
            h, a = key.split(" vs ", 1)
            out.append({"home": h, "away": a, "gh": int(sc[0]), "ga": int(sc[1]),
                        "stage": "Grupos", "pens": False, "winner": None})
    ko = real.get("knockout_matches") or {}
    for rnd in ("r32", "r16", "qf", "sf", "third", "final"):
        for mid, e in sorted((ko.get(rnd) or {}).items(),
                             key=lambda x: int(x[0]) if x[0].isdigit() else 9999):
            if e.get("home_score") is None:
                continue
            gh, ga = int(e["home_score"]), int(e["away_score"])
            out.append({"home": e["home"], "away": e["away"], "gh": gh, "ga": ga,
                        "stage": ROUND_LABEL[rnd], "pens": gh == ga,
                        "winner": e.get("winner"), "id": int(mid)})
    return out


def _engine_comparison(base_elo: dict, real: dict, w_user: float) -> list[dict]:
    """Elo puro vs ensemble del usuario vs XGBoost sobre los 104 partidos."""
    rows = []
    for label, key, w in [("Elo puro", "elo", 0.0),
                          (f"Ensemble ({w_user*100:.0f}% stats)", "ensemble", w_user),
                          ("XGBoost stats", "xgb", 1.0)]:
        _ens.set_stats_weight(w)
        diags = compute_match_diagnostics(base_elo, real)
        s = aggregate_metrics([((d.p_home, d.p_draw, d.p_away), d.outcome) for d in diags])
        rows.append({"label": label, "key": key, "weight": w, "n": s.n,
                     "top1": s.hit_rate_top1, "brier": s.mean_brier,
                     "logloss": s.mean_log_loss, "rps": s.mean_rps})
    _ens.set_stats_weight(w_user)
    return rows


def main() -> None:
    real = json.loads(REAL.read_text(encoding="utf-8"))
    actualidad = json.loads(ACTUALIDAD.read_text(encoding="utf-8"))
    base_elo, cfg = _base_elo()

    matches = _all_matches(real)
    diags = compute_match_diagnostics(base_elo, real)
    stats = aggregate_metrics([((d.p_home, d.p_draw, d.p_away), d.outcome) for d in diags])

    # --- el campeón ---
    final = (real.get("knockout_matches") or {}).get("final", {}).get("104")
    third = (real.get("knockout_matches") or {}).get("third", {}).get("103")
    champion = final["winner"] if final else None
    runner_up = final["away"] if final and final["winner"] == final["home"] else (
        final["home"] if final else None)

    # --- snapshots: la evolución día a día ---
    snaps = list_snapshots()
    snap_series = []
    for s in snaps:
        champ = s.get("champion") or {}
        if not champ:
            continue
        lead, lead_p = max(champ.items(), key=lambda x: x[1])
        snap_series.append({
            "date": s["date"],
            "leader": lead, "leader_p": round(lead_p, 4),
            "probs": {t: round(p, 4) for t, p in
                      sorted(champ.items(), key=lambda x: -x[1])[:10]},
        })

    # equipos a dibujar en la carrera de probabilidades: los que lideraron alguna vez
    # + finalistas, para que la narrativa del adelantamiento se vea
    tracked = {sn["leader"] for sn in snap_series}
    tracked.update([t for t in (champion, runner_up) if t])
    race = {}
    for team in tracked:
        race[team] = [
            {"date": s["date"], "p": round(float((s.get("champion") or {}).get(team, 0.0)), 4)}
            for s in snaps if s.get("champion")
        ]

    # --- sorpresas ---
    surprises = sorted(diags, key=lambda d: -d.surprise)[:8]

    # --- goles ---
    total_goals = sum(m["gh"] + m["ga"] for m in matches)

    # --- calibración ---
    bins = reliability_bins([((d.p_home, d.p_draw, d.p_away), d.outcome) for d in diags])

    # --- boletines de audio ---
    boletines = sorted(p.name for p in RECAPS.glob("boletin_*.mp3")) if RECAPS.exists() else []

    story = {
        "generated_from": "data/processed/real_results.json + snapshots/ + actualidad.json",
        "tournament": {
            "name": "Mundial 2026", "hosts": ["us", "ca", "mx"],
            "start": "2026-06-11", "end": "2026-07-19",
            "teams": 48, "matches": len(matches), "goals": total_goals,
        },
        "champion": {
            "team": champion, "iso": _iso(champion) if champion else None,
            "runner_up": runner_up, "runner_up_iso": _iso(runner_up) if runner_up else None,
            "score": f"{final['home_score']}-{final['away_score']}" if final else None,
            "final_home": final["home"] if final else None,
            "final_away": final["away"] if final else None,
            "date": "2026-07-19",
            "third_place": third["winner"] if third else None,
            "third_iso": _iso(third["winner"]) if third else None,
            "third_score": f"{third['home']} {third['home_score']}-{third['away_score']} {third['away']}" if third else None,
        },
        # Cap 1: lo que dijo el modelo ANTES de que empezara nada
        "preseason": {
            "date": snap_series[0]["date"] if snap_series else None,
            "top": [{"team": t, "p": p, "iso": _iso(t)}
                    for t, p in list((snaps[0].get("champion") or {}).items())[:0]] or
                   [{"team": t, "p": round(p, 4), "iso": _iso(t)} for t, p in
                    sorted((snaps[0].get("champion") or {}).items(),
                           key=lambda x: -x[1])[:8]] if snaps else [],
        },
        # Cap 3: la montaña rusa
        "race": race,
        "snapshots": snap_series,
        # Cap 4: el juicio al modelo
        "verdict": {
            "n": stats.n,
            "top1": round(stats.hit_rate_top1, 4),
            "brier": round(stats.mean_brier, 4),
            "logloss": round(stats.mean_log_loss, 4),
            "rps": round(stats.mean_rps, 4),
            "engines": _engine_comparison(base_elo, real, cfg.stats_weight),
            "calibration": [
                {"mid": round(b["mid"], 3), "n": b["n"],
                 "predicted": round(b["predicted_mean"], 4),
                 "observed": round(b["observed_freq"], 4)}
                for b in bins if b["n"] > 0 and b["predicted_mean"] is not None
            ],
        },
        "surprises": [{
            "home": d.home, "away": d.away, "home_iso": _iso(d.home), "away_iso": _iso(d.away),
            "gh": d.home_score, "ga": d.away_score, "phase": d.phase,
            "surprise": round(d.surprise, 4),
            "p_home": round(d.p_home, 4), "p_draw": round(d.p_draw, 4), "p_away": round(d.p_away, 4),
        } for d in surprises],
        # todos los partidos, con lo que dijo el modelo de cada uno
        "matches": [{
            "home": d.home, "away": d.away, "home_iso": _iso(d.home), "away_iso": _iso(d.away),
            "gh": d.home_score, "ga": d.away_score, "phase": d.phase, "date": d.date,
            "p_home": round(d.p_home, 4), "p_draw": round(d.p_draw, 4), "p_away": round(d.p_away, 4),
            "outcome": d.outcome, "surprise": round(d.surprise, 4),
            "hit": max([("H", d.p_home), ("D", d.p_draw), ("A", d.p_away)],
                       key=lambda x: x[1])[0] == d.outcome,
        } for d in diags],
        # Cap 2 / archivo
        "scorers": actualidad.get("scorers", [])[:15],
        "assists": actualidad.get("assists", [])[:10],
        "boletines": boletines,
        "archive": {
            "snapshots": len(snaps),
            "first": snaps[0]["date"] if snaps else None,
            "last": snaps[-1]["date"] if snaps else None,
            "audio": len(boletines),
        },
    }

    # el camino del campeón: sus partidos en orden
    if champion:
        story["champion"]["road"] = [
            {"home": m["home"], "away": m["away"], "gh": m["gh"], "ga": m["ga"],
             "stage": m["stage"], "phase": m["phase"],
             "p_win": round(m["p_home"] if m["home"] == champion else m["p_away"], 4)}
            for m in [{**mm, "stage": mm["phase"]} for mm in story["matches"]]
            if champion in (m["home"], m["away"])
        ]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(story, ensure_ascii=False, indent=1), encoding="utf-8")

    kb = OUT.stat().st_size / 1024
    print(f"✅ {OUT.relative_to(ROOT)} · {kb:.0f} KB")
    print(f"   campeón: {champion} ({story['champion']['score']} a {runner_up})")
    print(f"   partidos: {len(matches)} · goles: {total_goals}")
    print(f"   modelo: {stats.n} evaluados · top-1 {stats.hit_rate_top1*100:.1f}% · Brier {stats.mean_brier:.3f}")
    for e in story["verdict"]["engines"]:
        print(f"     {e['label']:24s} top1 {e['top1']*100:5.1f}%  Brier {e['brier']:.3f}")
    print(f"   snapshots: {len(snaps)} · audio: {len(boletines)}")


if __name__ == "__main__":
    main()
