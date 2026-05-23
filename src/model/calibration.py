"""Métricas de calibración y precisión para el modelo de predicción.

Brier score, log-loss, RPS (Rank Probability Score), reliability bins
y hit-rate por nivel de confianza. Funciona para probabilidades 1X2
(victoria local / empate / victoria visitante).
"""
from __future__ import annotations
import math
from dataclasses import dataclass


# Outcomes ordenados como (Home, Draw, Away). Misma convención en todas
# las funciones de este módulo.
OUTCOMES = ("H", "D", "A")


def outcome_from_score(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "H"
    if home_goals < away_goals:
        return "A"
    return "D"


def brier_multi(prob: tuple[float, float, float], outcome: str) -> float:
    """Brier score multiclase: suma((p_i - y_i)^2) sobre las 3 clases.

    Rango [0, 2]. 0 = predicción perfecta. Cuanto más bajo, mejor.
    """
    targets = [1.0 if c == outcome else 0.0 for c in OUTCOMES]
    return sum((p - t) ** 2 for p, t in zip(prob, targets))


def log_loss(prob: tuple[float, float, float], outcome: str, eps: float = 1e-9) -> float:
    """Cross-entropy: -log(p_outcome). 0 = perfecto, +inf si p=0."""
    idx = OUTCOMES.index(outcome)
    p = max(min(prob[idx], 1 - eps), eps)
    return -math.log(p)


def rps(prob: tuple[float, float, float], outcome: str) -> float:
    """Rank Probability Score para resultados ordinales (H, D, A).

    Penaliza más una predicción de "victoria local" cuando gana el visitante
    que cuando empata, ya que H y A están más alejados que H y D.
    Rango [0, 1]. 0 = perfecto.
    """
    # CDF acumuladas
    cum_pred = [prob[0], prob[0] + prob[1]]            # P(<=H), P(<=D)
    targets = [1.0 if c == outcome else 0.0 for c in OUTCOMES]
    cum_targ = [targets[0], targets[0] + targets[1]]
    return 0.5 * sum((cp - ct) ** 2 for cp, ct in zip(cum_pred, cum_targ))


@dataclass
class CalibrationStats:
    n: int
    mean_brier: float
    mean_log_loss: float
    mean_rps: float
    hit_rate_top1: float  # % de veces que el outcome más probable acertó
    accuracy_by_confidence: dict[str, tuple[int, float]]  # bin: (n_picks, hit_rate)


def aggregate_metrics(
    predictions: list[tuple[tuple[float, float, float], str]],
) -> CalibrationStats:
    """Calcula todas las métricas sobre una lista de (probs, outcome_real)."""
    if not predictions:
        return CalibrationStats(0, 0.0, 0.0, 0.0, 0.0, {})

    briers, losses, rpss = [], [], []
    top1_hits = 0
    by_conf: dict[str, list[int]] = {
        "<40%": [], "40-50%": [], "50-60%": [], "60-70%": [], "70-80%": [], ">=80%": [],
    }
    for prob, outcome in predictions:
        briers.append(brier_multi(prob, outcome))
        losses.append(log_loss(prob, outcome))
        rpss.append(rps(prob, outcome))
        top_idx = max(range(3), key=lambda i: prob[i])
        top_outcome = OUTCOMES[top_idx]
        hit = int(top_outcome == outcome)
        top1_hits += hit
        # Bin por confianza del pick principal
        p_top = prob[top_idx]
        if p_top < 0.40: by_conf["<40%"].append(hit)
        elif p_top < 0.50: by_conf["40-50%"].append(hit)
        elif p_top < 0.60: by_conf["50-60%"].append(hit)
        elif p_top < 0.70: by_conf["60-70%"].append(hit)
        elif p_top < 0.80: by_conf["70-80%"].append(hit)
        else: by_conf[">=80%"].append(hit)

    return CalibrationStats(
        n=len(predictions),
        mean_brier=sum(briers) / len(briers),
        mean_log_loss=sum(losses) / len(losses),
        mean_rps=sum(rpss) / len(rpss),
        hit_rate_top1=top1_hits / len(predictions),
        accuracy_by_confidence={
            k: (len(v), (sum(v) / len(v)) if v else 0.0)
            for k, v in by_conf.items()
        },
    )


def reliability_bins(
    predictions: list[tuple[tuple[float, float, float], str]],
    n_bins: int = 10,
) -> list[dict]:
    """Reliability diagram: por bucket de probabilidad predicha, frecuencia real.

    Se hace marginal (por clase): para cada outcome H/D/A, todas las predicciones
    que dieron prob_X = p forman un bin de tamaño n. La frecuencia real es
    cuántas veces el outcome real fue X.

    Returns: lista de dicts {bin_low, bin_high, mid, n, predicted_mean, observed_freq}.
    """
    if not predictions:
        return []
    edges = [i / n_bins for i in range(n_bins + 1)]
    bins: list[dict] = [
        {"bin_low": edges[i], "bin_high": edges[i + 1],
         "mid": (edges[i] + edges[i + 1]) / 2,
         "n": 0, "pred_sum": 0.0, "obs_sum": 0.0}
        for i in range(n_bins)
    ]
    for prob, outcome in predictions:
        for idx, c in enumerate(OUTCOMES):
            p = prob[idx]
            # Asignar al bin correcto (último bin incluye 1.0)
            b_idx = min(int(p * n_bins), n_bins - 1)
            bins[b_idx]["n"] += 1
            bins[b_idx]["pred_sum"] += p
            bins[b_idx]["obs_sum"] += 1.0 if outcome == c else 0.0
    for b in bins:
        if b["n"] > 0:
            b["predicted_mean"] = b["pred_sum"] / b["n"]
            b["observed_freq"] = b["obs_sum"] / b["n"]
        else:
            b["predicted_mean"] = None
            b["observed_freq"] = None
    return bins


def shannon_entropy(probs: dict[str, float]) -> float:
    """Entropía de Shannon en bits sobre una distribución discreta.

    Útil como 'openness' del torneo: 0 = un solo ganador seguro,
    log2(48) ≈ 5.58 = totalmente abierto entre 48 equipos.
    """
    h = 0.0
    for p in probs.values():
        if p > 0:
            h -= p * math.log2(p)
    return h


def bootstrap_champion_ci(
    champions_by_sim: list[str],
    teams: list[str],
    n_boot: int = 200,
    seed: int = 42,
) -> dict[str, tuple[float, float, float]]:
    """Bootstrap del % de campeón por equipo.

    Re-muestrea con reemplazo la lista de campeones por simulación,
    devuelve (P10, mediana, P90) por equipo.
    """
    import random
    rng = random.Random(seed)
    n = len(champions_by_sim)
    if n == 0:
        return {t: (0.0, 0.0, 0.0) for t in teams}
    # Generar muestras bootstrap
    samples: dict[str, list[float]] = {t: [] for t in teams}
    for _ in range(n_boot):
        boot = [champions_by_sim[rng.randrange(n)] for _ in range(n)]
        cnt: dict[str, int] = {}
        for c in boot:
            cnt[c] = cnt.get(c, 0) + 1
        for t in teams:
            samples[t].append(cnt.get(t, 0) / n)
    out: dict[str, tuple[float, float, float]] = {}
    for t, vals in samples.items():
        vals_sorted = sorted(vals)
        p10 = vals_sorted[int(0.10 * n_boot)]
        p50 = vals_sorted[int(0.50 * n_boot)]
        p90 = vals_sorted[int(0.90 * n_boot)]
        out[t] = (p10, p50, p90)
    return out
