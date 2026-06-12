"""CLI de actualización diaria del Mundial.

El torneo es corto: cada día se juegan partidos y conviene registrar los
resultados y re-evaluar el modelo. Este script hace todo el ciclo sin
necesidad de abrir la web (la web lee los mismos JSON y se actualiza sola).

Uso:
    python scripts/dia.py add "Mexico 2-0 Sudafrica" "Corea del Sur 2-1 Rep. Checa"
    python scripts/dia.py ko r32 73 "Espana 1-1 Noruega" --ganador Espana   # penaltis
    python scripts/dia.py informe          # rendimiento + probabilidades + próximos
    python scripts/dia.py informe --sims 20000

Los nombres aceptan acentos y alias comunes (Chequia, Holanda, EEUU…).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.tournament.groups import ALL_TEAMS, GROUPS
from src.data.team_names import EN_TO_ES
from src.model.biases import BiasesConfig
from src.model import ensemble
from src.model.elo import train_elo, HOME_ADVANTAGE
from src.model.elo_dynamic import recalculate_elo_with_real
from src.model.poisson import expected_goals_ensemble
from src.model.match_probs import match_outcome_probs, representative_score

REAL_RESULTS = ROOT / "data" / "processed" / "real_results.json"
RESULTS_CSV = ROOT / "data" / "raw" / "results.csv"

ALIASES = {
    "chequia": "Rep. Checa", "republica checa": "Rep. Checa", "czechia": "Rep. Checa",
    "corea": "Corea del Sur", "korea": "Corea del Sur",
    "eeuu": "Estados Unidos", "usa": "Estados Unidos", "ee uu": "Estados Unidos",
    "holanda": "Paises Bajos", "paises bajos": "Paises Bajos",
    "costa de marfil": "Costa Marfil", "rd congo": "R.D. Congo", "congo": "R.D. Congo",
    "bosnia": "Bosnia Herz.", "bosnia-herzegovina": "Bosnia Herz.",
    "arabia": "Arabia Saudi", "sudafrica": "Sudafrica", "turquia": "Turquia",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


_CANON = {_norm(t): t for t in ALL_TEAMS}


def resolve_team(name: str) -> str:
    n = _norm(name)
    if n in _CANON:
        return _CANON[n]
    if n in ALIASES:
        return ALIASES[n]
    cands = [t for k, t in _CANON.items() if n in k or k in n]
    if len(cands) == 1:
        return cands[0]
    raise SystemExit(
        f"❌ Equipo no reconocido: '{name}'"
        + (f" (¿quizás {', '.join(cands)}?)" if cands else "")
        + f"\n   Equipos válidos: {', '.join(sorted(ALL_TEAMS))}"
    )


def load_real() -> dict:
    if REAL_RESULTS.exists():
        return json.loads(REAL_RESULTS.read_text(encoding="utf-8"))
    return {"group_matches": {},
            "knockout_matches": {"r32": {}, "r16": {}, "qf": {}, "sf": {}, "final": {}}}


def save_real(d: dict) -> None:
    REAL_RESULTS.parent.mkdir(parents=True, exist_ok=True)
    REAL_RESULTS.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def _schedule() -> pd.DataFrame:
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"])
    wc = df[df["date"] >= "2026-06-01"].copy()
    wc["home_es"] = wc["home_team"].map(lambda x: EN_TO_ES.get(x, x))
    wc["away_es"] = wc["away_team"].map(lambda x: EN_TO_ES.get(x, x))
    return wc


SCORE_RE = re.compile(r"^(.+?)\s+(\d+)\s*[-–:]\s*(\d+)\s+(.+)$")


def parse_score(text: str) -> tuple[str, int, int, str]:
    m = SCORE_RE.match(text.strip())
    if not m:
        raise SystemExit(f"❌ Formato no reconocido: '{text}'. Usa: \"Equipo1 2-0 Equipo2\"")
    return resolve_team(m.group(1)), int(m.group(2)), int(m.group(3)), resolve_team(m.group(4))


def cmd_add(scores: list[str]) -> None:
    real = load_real()
    sched = _schedule()
    for s in scores:
        a, ga, gb, b = parse_score(s)
        # Validar que el fixture existe y registrar con la orientación del calendario
        row = sched[(sched["home_es"] == a) & (sched["away_es"] == b)]
        row_inv = sched[(sched["home_es"] == b) & (sched["away_es"] == a)]
        if len(row):
            key, val = f"{a} vs {b}", [ga, gb]
        elif len(row_inv):
            key, val = f"{b} vs {a}", [gb, ga]
        else:
            raise SystemExit(f"❌ No existe el partido de grupos {a} vs {b} en el calendario. "
                             f"¿Es de eliminatorias? Usa: python scripts/dia.py ko <ronda> <id> \"...\"")
        prev = real["group_matches"].get(key)
        real["group_matches"][key] = val
        tag = f"(antes {prev[0]}-{prev[1]})" if prev else ""
        print(f"✅ {key}: {val[0]}-{val[1]} {tag}")
    save_real(real)
    print(f"\n💾 Guardado en {REAL_RESULTS.relative_to(ROOT)} "
          f"({len(real['group_matches'])} partidos de grupos registrados)")


def cmd_ko(ronda: str, match_id: int, score: str, ganador: str | None) -> None:
    if ronda not in ("r32", "r16", "qf", "sf", "final"):
        raise SystemExit("❌ Ronda debe ser: r32, r16, qf, sf o final")
    a, ga, gb, b = parse_score(score)
    if ga == gb and not ganador:
        raise SystemExit("❌ Empate en eliminatoria: indica --ganador <equipo> (penaltis)")
    winner = resolve_team(ganador) if ganador else (a if ga > gb else b)
    real = load_real()
    real["knockout_matches"].setdefault(ronda, {})[str(match_id)] = {
        "home": a, "away": b, "home_score": ga, "away_score": gb, "winner": winner,
    }
    save_real(real)
    print(f"✅ {ronda.upper()} P{match_id}: {a} {ga}-{gb} {b} → pasa {winner}")


def _load_elo_full() -> tuple[dict[str, float], dict[str, float], BiasesConfig, dict]:
    """Replica get_elo_with_biases() de la web, sin streamlit."""
    cfg = BiasesConfig.load()
    ensemble.set_stats_weight(cfg.stats_weight)
    results = pd.read_csv(RESULTS_CSV)
    results["date"] = pd.to_datetime(results["date"])
    train = results[results["date"] < pd.Timestamp("2026-05-21")].dropna(
        subset=["home_score", "away_score"])
    ratings = train_elo(train, decay_old_matches=True, half_life=cfg.half_life)
    es_to_en = {v: k for k, v in EN_TO_ES.items()}
    base = {t: ratings.get(es_to_en.get(t, t), 1500.0) for t in ALL_TEAMS}
    biased = cfg.apply_to(base)
    try:
        from src.data.news import get_active_deltas
        for team, d in get_active_deltas().items():
            if team in biased:
                biased[team] += d
    except Exception:
        pass
    real = load_real()
    final = recalculate_elo_with_real(biased, real)
    return base, final, cfg, real


def cmd_informe(n_sims: int) -> None:
    from src.model.live_diagnostics import compute_match_diagnostics
    from src.model.calibration import aggregate_metrics
    from src.model.tournament_sim import run_monte_carlo
    from src.data.snapshots import take_snapshot, SNAP_DIR

    base, elo, cfg, real = _load_elo_full()
    biased = elo  # ya incluye resultados reales
    n_group = len([v for v in real.get("group_matches", {}).values() if v])
    n_ko = sum(len(v) for v in real.get("knockout_matches", {}).values())
    print("=" * 70)
    print(f"📋 INFORME DIARIO · {pd.Timestamp.now():%d %b %Y} · "
          f"{n_group + n_ko}/104 partidos registrados")
    print("=" * 70)

    # ---------- 1. Rendimiento del modelo en los partidos jugados ----------
    cfg_w = cfg.stats_weight
    if n_group + n_ko:
        print(f"\n🎯 PARTIDO A PARTIDO (ensemble {cfg_w*100:.0f}% stats):")
        diags = compute_match_diagnostics(BiasesConfig.load().apply_to(base), real)
        for d in diags:
            probs = {"H": d.p_home, "D": d.p_draw, "A": d.p_away}
            pick = max(probs, key=probs.get)
            hit = "✓" if pick == d.outcome else "✗"
            print(f"  {hit} {d.home} {d.home_score}-{d.away_score} {d.away}  "
                  f"(modelo: {d.p_home*100:.0f}/{d.p_draw*100:.0f}/{d.p_away*100:.0f} · "
                  f"xG {d.xg_home:.1f}-{d.xg_away:.1f} · surprise {d.surprise:.2f} · "
                  f"Brier {d.brier:.3f})")

        print("\n🥊 COMPARATIVA DE MOTORES (partidos reales hasta hoy):")
        base_biased = BiasesConfig.load().apply_to(base)
        for label, w in [("Elo puro      ", 0.0),
                         (f"Ensemble ({cfg_w:.2f})", cfg_w),
                         ("XGBoost stats ", 1.0)]:
            ensemble.set_stats_weight(w)
            dd = compute_match_diagnostics(base_biased, real)
            preds = [((x.p_home, x.p_draw, x.p_away), x.outcome) for x in dd]
            s = aggregate_metrics(preds)
            print(f"  {label}  top1 {s.hit_rate_top1*100:3.0f}%  "
                  f"brier {s.mean_brier:.3f}  rps {s.mean_rps:.3f}")
        ensemble.set_stats_weight(cfg_w)
    else:
        print("\n(No hay partidos registrados todavía: usa `python scripts/dia.py add ...`)")

    # ---------- 2. Probabilidades actualizadas ----------
    print(f"\n🏆 SIMULACIÓN ACTUALIZADA ({n_sims:,} torneos):")
    summary = run_monte_carlo(elo, n_sims=n_sims, seed=42, real_results=real)
    champ = sorted(summary.champion_probs.items(), key=lambda x: -x[1])[:10]

    # Delta vs el último snapshot anterior a hoy
    prev = {}
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    snaps = sorted(SNAP_DIR.glob("*.json")) if SNAP_DIR.exists() else []
    snaps = [s for s in snaps if s.stem < today]
    if snaps:
        prev = (json.loads(snaps[-1].read_text()).get("champion") or {})
    for i, (t, p) in enumerate(champ, 1):
        delta = ""
        if prev:
            d = (p - prev.get(t, 0)) * 100
            arrow = "▲" if d > 0.05 else ("▼" if d < -0.05 else "·")
            delta = f"  {arrow} {d:+.1f}pp vs {snaps[-1].stem}"
        print(f"  {i:2d}. {t:18s} {p*100:5.1f}%{delta}")

    snap_dict = {
        "champion": summary.champion_probs, "finalist": summary.finalist_probs,
        "semifinal": summary.semifinal_probs, "quarter": summary.quarter_probs,
        "r16": summary.r16_probs, "group_winner": summary.group_winner_probs,
        "group_top3": summary.group_top3_probs,
    }
    path = take_snapshot(snap_dict, force=True)
    print(f"\n📸 Snapshot del día guardado: {path}")

    # ---------- 3. Próximos partidos con resultado esperado ----------
    sched = _schedule()
    played_keys = set(real.get("group_matches", {}).keys())
    pending = sched[~sched.apply(
        lambda r: f"{r['home_es']} vs {r['away_es']}" in played_keys
        or f"{r['away_es']} vs {r['home_es']}" in played_keys, axis=1)]
    upcoming = pending[pending["date"] >= pd.Timestamp.now().normalize()].head(8)
    if len(upcoming):
        print("\n🔮 PRÓXIMOS PARTIDOS (resultado esperado del ensemble):")
        from src.tournament.groups import HOST_NATIONS
        for _, m in upcoming.iterrows():
            h, a = m["home_es"], m["away_es"]
            ha = HOME_ADVANTAGE if (h in HOST_NATIONS and a not in HOST_NATIONS) else (
                -HOME_ADVANTAGE if (a in HOST_NATIONS and h not in HOST_NATIONS) else 0.0)
            lh, la = expected_goals_ensemble(elo.get(h, 1500), elo.get(a, 1500), h, a,
                                             home_advantage=ha)
            p = match_outcome_probs(lh, la, use_dc=True)
            (bh, ba), bp = representative_score(lh, la, use_dc=True)
            print(f"  {m['date']:%d %b} · {h} vs {a}: esperado {bh}-{ba} "
                  f"(xG {lh:.2f}-{la:.2f} · 1X2 {p[0]*100:.0f}/{p[1]*100:.0f}/{p[2]*100:.0f})")

    print("\n✅ Listo. La web ya refleja todo (refresca con R si la tienes abierta).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Registrar resultados de fase de grupos")
    p_add.add_argument("scores", nargs="+", help='"Equipo1 2-0 Equipo2" …')

    p_ko = sub.add_parser("ko", help="Registrar resultado de eliminatoria")
    p_ko.add_argument("ronda", choices=["r32", "r16", "qf", "sf", "final"])
    p_ko.add_argument("match_id", type=int, help="Nº de partido FIFA (73-104)")
    p_ko.add_argument("score", help='"Equipo1 2-1 Equipo2"')
    p_ko.add_argument("--ganador", help="Necesario si hay empate (penaltis)")

    p_inf = sub.add_parser("informe", help="Informe diario: rendimiento + probabilidades")
    p_inf.add_argument("--sims", type=int, default=10_000)

    args = ap.parse_args()
    if args.cmd == "add":
        cmd_add(args.scores)
    elif args.cmd == "ko":
        cmd_ko(args.ronda, args.match_id, args.score, args.ganador)
    elif args.cmd == "informe":
        cmd_informe(args.sims)


if __name__ == "__main__":
    main()
