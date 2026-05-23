"""Componentes UI reutilizables (renderizado HTML custom)."""
from __future__ import annotations
import streamlit as st

from app.styles import PRIMARY, ACCENT, GOOD, DANGER, TEXT, TEXT_DIM, BG_CARD


def team_header(name: str, flag_url: str, group: str, confederation: str,
                wc_titles: int, elo_base: float, elo_delta: float = 0) -> str:
    delta_str = ""
    if elo_delta:
        sign = "+" if elo_delta > 0 else ""
        color = GOOD if elo_delta > 0 else DANGER
        delta_str = f' <span style="color: {color};">({sign}{int(elo_delta)})</span>'
    titles_str = f"🏆 {wc_titles}" if wc_titles else "—"
    return f"""
    <div class="team-card-header">
        <img src="{flag_url}" class="team-flag" alt="{name}">
        <div>
            <p class="team-name">{name}</p>
            <p class="team-meta">Grupo {group} · {confederation} · Mundiales: {titles_str} · Elo: {int(elo_base + elo_delta)}{delta_str}</p>
        </div>
    </div>
    """


def prob_bar(label: str, pct: float) -> str:
    pct = max(0, min(100, pct))
    return f"""
    <div class="prob-row">
        <span class="prob-label">{label}</span>
        <div class="prob-bar-container">
            <div class="prob-bar" style="width: {pct}%;"></div>
        </div>
        <span class="prob-value">{pct:.1f}%</span>
    </div>
    """


def form_streak(streak: str) -> str:
    """streak: cadena 'WDLWW...' cronologica (mas antiguo a la izquierda)."""
    pills = "".join(f'<div class="form-pill form-{c}">{c}</div>' for c in streak)
    return f'<div class="form-streak">{pills}</div>'


def big_stat(value: str | int | float, label: str, tooltip: str = "") -> str:
    tooltip_attr = f' title="{tooltip}"' if tooltip else ""
    info_icon = (' <span style="color:#9ca3af; font-size:0.65rem; cursor:help;">ⓘ</span>'
                  if tooltip else "")
    return f"""
    <div class="big-stat"{tooltip_attr}>
        <div class="big-stat-value">{value}</div>
        <div class="big-stat-label">{label}{info_icon}</div>
    </div>
    """


def match_row(date: str, home: str, away: str, score: str = "-") -> str:
    return f"""
    <div class="match-row">
        <span class="match-date">{date}</span>
        <span class="match-teams">{home} <span style="color:{TEXT_DIM}">vs</span> {away}</span>
        <span class="match-score">{score}</span>
    </div>
    """


def team_card_compact(name: str, flag_url: str, group: str,
                      p_champion: float, p_qualify: float, elo: float) -> str:
    """Card compacta para usar en grids."""
    return f"""
    <div class="team-card">
        <div class="team-card-header">
            <img src="{flag_url}" class="team-flag" alt="{name}">
            <div>
                <p class="team-name">{name}</p>
                <p class="team-meta">Grupo {group} · Elo {int(elo)}</p>
            </div>
        </div>
        {prob_bar("Octavos", p_qualify * 100)}
        {prob_bar("Campeón", p_champion * 100)}
    </div>
    """
