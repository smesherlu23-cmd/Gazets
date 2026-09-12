"""Шрифтовой комплект: встроенные гарнитуры + системные.

Приложение офлайновое, поэтому все восемь гарнитур лежат рядом с кодом
(`assets/fonts`, все — SIL OFL 1.1). Тот же список отдаётся Flet для интерфейса
и движку рендера в виде правил ``@font-face`` с путями ``file://``.
"""

from __future__ import annotations

import functools
import json
import pathlib
import platform
import subprocess
from dataclasses import dataclass

ASSETS = pathlib.Path(__file__).resolve().parent.parent / "assets"
FONT_DIR = ASSETS / "fonts"

# Гарнитуры без кириллицы — о них панель бренда предупреждает и подставляет запас.
LATIN_ONLY = {"UnifrakturMaguntia", "Bodoni Moda"}

FALLBACK_FOR_CYRILLIC = "Old Standard TT"

UI_FONT = "IBM Plex Sans"
UI_MONO = "IBM Plex Mono"


@dataclass(frozen=True)
class FontFace:
    family: str
    style: str
    weight: int
    file: str

    @property
    def path(self) -> pathlib.Path:
        return FONT_DIR / self.file


@functools.lru_cache(maxsize=1)
def bundled_faces() -> tuple[FontFace, ...]:
    manifest = FONT_DIR / "manifest.json"
    if not manifest.exists():
        return ()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    faces = [
        FontFace(item["family"], item["style"], int(item["weight"]), item["file"])
        for item in data
        if (FONT_DIR / item["file"]).exists()
    ]
    return tuple(faces)


@functools.lru_cache(maxsize=1)
def bundled_families() -> tuple[str, ...]:
    seen: list[str] = []
    for face in bundled_faces():
        if face.family not in seen:
            seen.append(face.family)
    return tuple(seen)


@functools.lru_cache(maxsize=1)
def system_families() -> tuple[str, ...]:
    """Гарнитуры, установленные в системе (ТЗ, п. 4.2 — «из установленных»)."""
    names: set[str] = set()
    try:
        if platform.system() == "Windows":
            import winreg  # type: ignore[import-not-found]

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
            )
            for index in range(winreg.QueryInfoKey(key)[1]):
                name, _, _ = winreg.EnumValue(key, index)
                name = name.split("(")[0].strip()
                for suffix in (" Bold", " Italic", " Regular", " Light", " Semibold"):
                    if name.endswith(suffix):
                        name = name[: -len(suffix)].strip()
                if name:
                    names.add(name)
        else:
            out = subprocess.run(
                ["fc-list", "--format", "%{family[0]}\n"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            names.update(line.strip() for line in out.stdout.splitlines() if line.strip())
    except Exception:  # системный список не критичен — встроенных хватает
        return ()
    return tuple(sorted(names))


def available_families() -> list[str]:
    """Список для селектов панели «Типографика»: сначала встроенные."""
    bundled = list(bundled_families())
    extra = [name for name in system_families() if name not in bundled]
    return bundled + extra


def font_face_css() -> str:
    """Правила @font-face для рендера полосы (пути — абсолютные file://)."""
    rules = []
    for face in bundled_faces():
        rules.append(
            "@font-face{{font-family:'{family}';font-style:{style};font-weight:{weight};"
            "src:url('{url}') format('truetype');font-display:block}}".format(
                family=face.family,
                style=face.style,
                weight=face.weight,
                url=face.path.as_uri(),
            )
        )
    return "".join(rules)


def flet_fonts() -> dict[str, str]:
    """Карта для ``page.fonts``.

    Пути отдаются относительно каталога ассетов (``assets_dir`` в ``ft.run``):
    так шрифты одинаково подхватываются и десктопным окном, и веб-режимом.
    """
    fonts: dict[str, str] = {}
    for face in bundled_faces():
        if face.style != "normal":
            continue
        suffix = {400: "", 500: " Medium", 600: " SemiBold", 700: " Bold"}.get(
            face.weight, f" {face.weight}"
        )
        fonts[f"{face.family}{suffix}"] = f"/fonts/{face.file}"
    return fonts


def supports_cyrillic(family: str) -> bool:
    return family not in LATIN_ONLY


def resolve_for_text(family: str, text: str) -> str:
    """Подменяет гарнитуру запасной антиквой, если в ней нет кириллицы."""
    if supports_cyrillic(family):
        return family
    if any("Ѐ" <= char <= "ӿ" for char in text):
        return FALLBACK_FOR_CYRILLIC
    return family
