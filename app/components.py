"""Componentes UI reutilizables (renderizado HTML custom)."""
from __future__ import annotations
from typing import Callable
import streamlit as st

from app.styles import PRIMARY, ACCENT, GOOD, DANGER, TEXT, TEXT_DIM, BG_CARD
from src.data.team_profile import ISO_CODES


# ─────────────────────────────────────────────────────────────────────
#  Tabla premium reutilizable (.wc-ptable) — sustituye a st.dataframe.
#  columns: lista de specs {label, key, kind, ...opts}
#    kinds: team | text | num | pct | bar | delta | grad
#    opts:  fmt (str.format), suffix, max (escala bar/grad), champ (bar violeta),
#           diverge (grad verde+/rojo−), hex (color base grad), align
# ─────────────────────────────────────────────────────────────────────
def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def table_flag(team: str, w: int = 22) -> str:
    iso = ISO_CODES.get(team, "un")
    return (f'<img src="https://flagcdn.com/w40/{iso}.png" style="width:{w}px;height:{round(w*0.7)}px;'
            f'border-radius:3px;object-fit:cover;box-shadow:0 1px 2px rgba(0,0,0,.4);vertical-align:middle;">')


def _cell(row: dict, col: dict) -> str:
    kind = col["kind"]
    v = row.get(col["key"])
    if kind == "team":
        return f'<td class="lft"><div class="pteam">{table_flag(v)}{v}</div></td>'
    if kind == "text":
        return f'<td class="lft" style="font-weight:600;white-space:nowrap;">{v}</td>'
    if kind == "num":
        s = col.get("fmt", "{:.0f}").format(v) + col.get("suffix", "")
        return (f'<td style="text-align:right;font-variant-numeric:tabular-nums;font-weight:600;'
                f'white-space:nowrap;">{s}</td>')
    if kind == "pct":
        return (f'<td style="text-align:right;font-variant-numeric:tabular-nums;font-weight:600;'
                f'white-space:nowrap;">{v:.0f}%</td>')
    if kind == "delta":
        c = GOOD if v > 0 else (DANGER if v < 0 else TEXT_DIM)
        return (f'<td style="text-align:right;font-variant-numeric:tabular-nums;font-weight:700;'
                f'white-space:nowrap;color:{c};">{v:+.0f}</td>')
    if kind == "bar":
        champ = " champ" if col.get("champ") else ""
        dim = " dim" if v < 8 else ""
        return (f'<td><div class="wc-pcell{champ}{dim}"><div class="fill" style="width:{max(v, 2):.0f}%"></div>'
                f'<div class="v">{v:.1f}</div></div></td>')
    if kind == "grad":
        mx = col.get("max", 100) or 1
        if col.get("diverge"):
            hue, a = (GOOD if v >= 0 else DANGER), min(abs(v) / mx, 1) * 0.5
        else:
            hue, a = col.get("hex", "#ef4444"), min(abs(v) / mx, 1) * 0.6
        bg = _hex_to_rgba(hue, a)
        s = col.get("fmt", "{:+.0f}").format(v)
        return (f'<td style="text-align:right;"><span style="display:inline-block;background:{bg};border-radius:6px;'
                f'padding:3px 9px;font-weight:800;font-variant-numeric:tabular-nums;">{s}</span></td>')
    return f'<td>{v}</td>'


def render_table(rows: list[dict], columns: list[dict],
                 highlight: Callable[[dict], bool] | None = None,
                 max_height: str | None = None) -> None:
    """Pinta una tabla premium directamente (st.markdown). Ver specs arriba.

    max_height: p.ej. '560px' para tablas largas → contenedor con scroll vertical
    y cabecera fija.
    """
    wrap = "overflow-x:auto;"
    if max_height:
        wrap += f"max-height:{max_height};overflow-y:auto;"
    html = [f'<div style="{wrap}"><table class="wc-ptable"><thead><tr>']
    for c in columns:
        cls = ' class="lft"' if c["kind"] in ("team", "text") else ''
        html.append(f'<th{cls}>{c["label"]}</th>')
    html.append('</tr></thead><tbody>')
    for r in rows:
        sel = " class='sel'" if highlight and highlight(r) else ""
        html.append(f'<tr{sel}>' + "".join(_cell(r, c) for c in columns) + '</tr>')
    html.append('</tbody></table></div>')
    st.markdown("".join(html), unsafe_allow_html=True)


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
