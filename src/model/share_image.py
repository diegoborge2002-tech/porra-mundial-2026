"""Genera una imagen PNG resumen para compartir en WhatsApp/RRSS."""
from __future__ import annotations
import io
from datetime import datetime


def generate_summary_png(
    leaderboard: list[dict],
    favoritos: list[tuple[str, float]],
    surprise_lines: list[str] | None = None,
    title: str = "Porra Mundial 2026",
    subtitle: str | None = None,
) -> bytes:
    """Genera PNG con el ranking actual y top favoritos.

    leaderboard: list of {"name", "real", "expected", "win_prob"} (ya ordenados).
    favoritos: list of (team, prob) ya ordenado descendente.

    Returns: bytes del PNG.
    """
    # Import dentro de la función para no penalizar import inicial
    import matplotlib.pyplot as plt
    import matplotlib as mpl

    # Tema oscuro consistente con la app
    BG = "#0a0e14"
    CARD = "#111827"
    TEXT = "#e5e7eb"
    DIM = "#9ca3af"
    PRIMARY = "#10b981"
    ACCENT = "#f59e0b"

    fig = plt.figure(figsize=(10, 14), dpi=120, facecolor=BG)
    gs = fig.add_gridspec(4, 1, height_ratios=[0.6, 2.5, 2.5, 1.4], hspace=0.45)

    # Header
    ax0 = fig.add_subplot(gs[0])
    ax0.set_facecolor(BG)
    ax0.axis("off")
    ax0.text(0.02, 0.6, title, fontsize=26, color=TEXT, fontweight="bold")
    if subtitle:
        ax0.text(0.02, 0.18, subtitle, fontsize=12, color=DIM)
    ax0.text(0.98, 0.6, datetime.now().strftime("%d %b %Y · %H:%M"),
              fontsize=10, color=DIM, ha="right")

    # Leaderboard
    ax1 = fig.add_subplot(gs[1])
    ax1.set_facecolor(CARD)
    ax1.axis("off")
    ax1.text(0.02, 0.94, "🏆 Liga de Amigos", fontsize=18, color=PRIMARY,
              fontweight="bold", transform=ax1.transAxes)
    top_lead = leaderboard[:8]
    y = 0.80
    for i, row in enumerate(top_lead):
        rank = i + 1
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f" {rank}"
        name = row.get("name", "—")
        real = row.get("real", 0)
        exp = row.get("expected", 0.0)
        wp = row.get("win_prob", 0.0)
        color_bar = ACCENT if rank == 1 else PRIMARY
        ax1.text(0.03, y, f"{medal}  {name}", fontsize=13, color=TEXT,
                  transform=ax1.transAxes, fontweight="bold" if rank == 1 else "normal")
        ax1.text(0.55, y, f"{real} pts reales", fontsize=11, color=DIM,
                  transform=ax1.transAxes)
        ax1.text(0.78, y, f"{exp:.1f} esp.", fontsize=11, color=DIM,
                  transform=ax1.transAxes)
        ax1.text(0.95, y, f"{wp*100:.1f}%", fontsize=12, color=color_bar,
                  transform=ax1.transAxes, ha="right", fontweight="bold")
        y -= 0.085

    # Favoritos al título
    ax2 = fig.add_subplot(gs[2])
    ax2.set_facecolor(CARD)
    ax2.axis("off")
    ax2.text(0.02, 0.94, "⭐ Favoritos al título", fontsize=18, color=ACCENT,
              fontweight="bold", transform=ax2.transAxes)
    y = 0.80
    for team, prob in favoritos[:8]:
        ax2.text(0.03, y, f"{team}", fontsize=13, color=TEXT, transform=ax2.transAxes)
        # Barra de probabilidad
        bar_x_start, bar_y, bar_w_max = 0.50, y - 0.005, 0.40
        # Trayectoria base
        rect_bg = mpl.patches.Rectangle(
            (bar_x_start, bar_y), bar_w_max, 0.018,
            facecolor="#1f2937", transform=ax2.transAxes, edgecolor="none",
        )
        ax2.add_patch(rect_bg)
        fill_w = bar_w_max * min(prob, 1.0)
        rect_fill = mpl.patches.Rectangle(
            (bar_x_start, bar_y), fill_w, 0.018,
            facecolor=PRIMARY, transform=ax2.transAxes, edgecolor="none",
        )
        ax2.add_patch(rect_fill)
        ax2.text(0.96, y, f"{prob*100:.1f}%", fontsize=12, color=PRIMARY,
                  transform=ax2.transAxes, ha="right", fontweight="bold")
        y -= 0.085

    # Sorpresas
    ax3 = fig.add_subplot(gs[3])
    ax3.set_facecolor(CARD)
    ax3.axis("off")
    if surprise_lines:
        ax3.text(0.02, 0.9, "😱 Top sorpresas recientes", fontsize=16, color="#ef4444",
                  fontweight="bold", transform=ax3.transAxes)
        y = 0.65
        for line in surprise_lines[:3]:
            ax3.text(0.03, y, line, fontsize=11, color=TEXT, transform=ax3.transAxes)
            y -= 0.22

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BG, bbox_inches="tight", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
