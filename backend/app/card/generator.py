from __future__ import annotations

from io import BytesIO
from pathlib import Path

import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont

from app.models.fingerprint import AxisScores, FingerprintDict

CARD_SIZE = (1200, 630)
_BG = "#060C1A"

# Glass Atlas palette (literal for Pillow — no CSS vars)
_CYAN        = "#38E1FF"
_BLUE        = "#4D8DFF"
_TEXT_PRI    = "#EAF2FF"
_TEXT_SEC    = "#9DB2D4"
_TEXT_TER    = "#5C708F"
_GRID        = "rgba(125,165,230,0.10)"
_GLASS_BG    = (18, 30, 56)
_BG_RAISED   = (10, 19, 38)
_BG_BASE_RGB = (6, 12, 26)

_DATA_COLORS = {
    "FEATURE":      "#2FD4A7",
    "REFACTOR":     "#6E8BFF",
    "BUGFIX":       "#FF6E8A",
    "TEST":         "#38E1FF",
    "ARCHITECTURE": "#B98CFF",
    "DOCS":         "#9DB2D4",
    "CHORE":        "#5C708F",
}


def _font_path(name: str) -> Path:
    return Path(__file__).parent / "fonts" / name


def _load_font(name: str, size: int) -> ImageFont.ImageFont:
    path = _font_path(name)
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def _render_radar_chart(axes: AxisScores) -> bytes:
    categories = [
        "Shipping\nVelocity",
        "Bug-Fix\nRatio",
        "Refactor\nHabit",
        "Test\nCoverage",
        "Architecture\nChurn",
        "Consistency",
    ]
    values = [
        axes.shipping_velocity,
        axes.bugfix_ratio,
        axes.refactor_habit,
        axes.test_coverage_signal,
        axes.architecture_churn,
        axes.consistency_score,
    ]
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            mode="lines",
            line={"color": _CYAN, "width": 3},
            fill="toself",
            fillcolor="rgba(56, 225, 255, 0.15)",
        )
    )
    fig.update_layout(
        paper_bgcolor=_BG,
        font={"color": _TEXT_SEC, "family": "Inter, sans-serif"},
        polar={
            "bgcolor": _BG,
            "radialaxis": {
                "range": [0, 10],
                "tickcolor": _GRID,
                "gridcolor": _GRID,
                "tickfont": {"color": _TEXT_TER},
            },
            "angularaxis": {
                "tickcolor": _TEXT_TER,
                "gridcolor": _GRID,
                "tickfont": {"color": _TEXT_SEC},
            },
        },
        width=500,
        height=500,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        showlegend=False,
    )
    return fig.to_image(format="png", engine="kaleido")


def _draw_gradient_overlay(card: Image.Image) -> None:
    width, height = card.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    center_x, center_y = int(width * 0.7), int(height * 0.2)
    max_radius = int((width**2 + height**2) ** 0.5)

    draw = ImageDraw.Draw(overlay)
    for radius in range(max_radius, 0, -6):
        alpha = int(60 * (1 - radius / max_radius))
        color = (56, 225, 255, max(alpha, 0))
        bbox = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
        draw.ellipse(bbox, fill=color)

    card.alpha_composite(overlay)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_card(fingerprint: FingerprintDict, narrative: str) -> bytes:
    card = Image.new("RGBA", CARD_SIZE, _BG)
    _draw_gradient_overlay(card)
    draw = ImageDraw.Draw(card)

    # Font loading — falls back to PIL bitmap if TTF not present in fonts/
    sg_bold_22  = _load_font("SpaceGrotesk-Bold.ttf", 22)
    inter_12    = _load_font("Inter-Regular.ttf", 12)
    inter_13_sb = _load_font("Inter-SemiBold.ttf", 13)
    inter_14    = _load_font("Inter-Regular.ttf", 14)
    jb_18       = _load_font("JetBrainsMono-Regular.ttf", 18)
    jb_14       = _load_font("JetBrainsMono-Regular.ttf", 14)

    # Header bar
    draw.rectangle((0, 0, 1200, 60), fill=(*_BG_BASE_RGB, 230))
    draw.text((40, 18), "GridPath", fill=_CYAN, font=jb_18)

    username_text = f"@{fingerprint.username}"
    uname_width = draw.textlength(username_text, font=sg_bold_22)
    draw.text(((1200 - uname_width) / 2, 16), username_text, fill=_TEXT_PRI, font=sg_bold_22)

    date_width = draw.textlength(fingerprint.date_range, font=jb_14)
    draw.text((1160 - date_width, 22), fingerprint.date_range, fill=_TEXT_TER, font=jb_14)

    # Left panel: radar chart
    radar_png = _render_radar_chart(fingerprint.axes)
    radar_image = Image.open(BytesIO(radar_png)).convert("RGBA").resize((480, 480))
    card.alpha_composite(radar_image, (40, 80))

    # Right panel: labels
    draw.text((580, 85), "DEVELOPER FINGERPRINT", fill=_TEXT_TER, font=inter_12)

    distribution = fingerprint.commit_label_distribution.model_dump()
    top_labels = sorted(distribution.items(), key=lambda kv: kv[1], reverse=True)[:3]

    pill_x = 580
    for label, count in top_labels:
        text = f"{label}  {count}"
        text_w = int(draw.textlength(text, font=inter_12))
        pill_w = text_w + 40
        draw.rounded_rectangle((pill_x, 120, pill_x + pill_w, 148), radius=14, fill=(*_BG_RAISED, 255))
        dot_color = _DATA_COLORS.get(label, _TEXT_TER)
        draw.ellipse((pill_x + 10, 130, pill_x + 18, 138), fill=dot_color)
        draw.text((pill_x + 24, 127), text, fill=_TEXT_PRI, font=inter_12)
        pill_x += pill_w + 12

    draw.text((580, 170), fingerprint.style_evolution, fill=_TEXT_SEC, font=inter_13_sb)

    # Narrative strip
    draw.line((580, 430, 1160, 430), fill=(*_BG_RAISED, 255), width=1)
    first_sentence = narrative.split(".")[0].strip()
    if first_sentence:
        first_sentence = f"{first_sentence}."
    lines = _wrap_text(draw, first_sentence, inter_14, 580)
    y = 446
    for line in lines[:4]:
        draw.text((580, y), line, fill=_TEXT_SEC, font=inter_14)
        y += 22

    # Footer bar
    draw.line((40, 570, 1160, 570), fill=(*_BG_RAISED, 200), width=1)
    langs = ", ".join(fingerprint.top_languages)
    stat_text = (
        f"{fingerprint.total_commits_analyzed} commits · "
        f"{fingerprint.repos_analyzed} repos · {langs}"
    )
    draw.rounded_rectangle((40, 582, 760, 612), radius=12, fill=(*_BG_RAISED, 255))
    draw.text((56, 590), stat_text, fill=_TEXT_PRI, font=jb_14)

    watermark = "github.com/agilap/gridpath"
    wm_width = draw.textlength(watermark, font=jb_14)
    draw.text((1160 - wm_width, 590), watermark, fill=_TEXT_TER, font=jb_14)

    out = BytesIO()
    card.convert("RGB").save(out, format="PNG")
    return out.getvalue()
