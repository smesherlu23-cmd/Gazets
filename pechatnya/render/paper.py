"""Слой состаривания бумаги.

Состав слоя и все числа — из раздела «Рендер полосы (эффект бумаги)» README.
Слой накладывается поверх полосы с ``mix-blend-mode: multiply`` и прозрачностью
``intensity / 100 × 0.9``; чекбоксы панели «Бумага» включают отдельные группы.
"""

from __future__ import annotations

from ..models import Paper

VIGNETTE = (
    "radial-gradient(70% 52% at 50% 46%,rgba(214,196,158,0) 0,"
    "rgba(178,150,104,.26) 74%,rgba(140,112,68,.46) 100%)"
)
STAINS = [
    "radial-gradient(26% 18% at 14% 12%,rgba(156,122,62,.3),rgba(156,122,62,0) 72%)",
    "radial-gradient(22% 16% at 88% 82%,rgba(140,106,54,.32),rgba(140,106,54,0) 70%)",
    "radial-gradient(14% 9% at 68% 33%,rgba(132,98,46,.3),rgba(132,98,46,0) 74%)",
]
FOLD = (
    "linear-gradient(90deg,rgba(120,94,52,0) 47.4%,rgba(120,94,52,.22) 49.6%,"
    "rgba(255,250,238,.3) 50%,rgba(120,94,52,.2) 50.4%,rgba(120,94,52,0) 52.6%)"
)
UNEVEN = "repeating-linear-gradient(93deg,rgba(90,70,40,.06) 0 2px,rgba(90,70,40,0) 2px 7px)"

# Зерно скана: SVG-шум, единственный слой, которого не было в макете.
GRAIN = (
    "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' "
    "height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' "
    "numOctaves='3' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/>"
    "</filter><rect width='160' height='160' filter='url(%23n)' opacity='0.5'/></svg>\")"
)


def aging_opacity(paper: Paper) -> float:
    if not paper.enabled:
        return 0.0
    return round(max(0, min(100, paper.intensity)) / 100 * 0.9, 4)


def aging_background(paper: Paper) -> str:
    """Собирает значение ``background`` слоя из включённых составляющих."""
    layers: list[str] = []
    if paper.yellowing:
        layers.append(VIGNETTE)
    if paper.stains:
        layers.extend(STAINS)
    if paper.folds:
        layers.append(FOLD)
    if paper.unevenness:
        layers.append(UNEVEN)
    if paper.grain:
        layers.append(GRAIN)
    return ",".join(layers)


def aging_layer_css(paper: Paper) -> str:
    """Инлайновый style для оверлея полосы (пустая строка — слоя нет)."""
    background = aging_background(paper)
    opacity = aging_opacity(paper)
    if not background or opacity <= 0:
        return ""
    return (
        "position:absolute;inset:0;pointer-events:none;mix-blend-mode:multiply;"
        f"opacity:{opacity};background:{background};background-size:cover"
    )


def paper_tint(paper: Paper) -> str:
    """Лёгкая желтизна самой бумаги — отдельно от оверлея, чтобы не гасить текст."""
    if not paper.enabled or not paper.yellowing:
        return ""
    amount = max(0, min(100, paper.intensity)) / 100
    return f"filter:sepia({amount * 0.18:.3f}) saturate({1 + amount * 0.1:.3f})"
