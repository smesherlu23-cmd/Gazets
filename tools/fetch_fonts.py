"""Скачивает шрифтовой комплект «Печатни» из Google Fonts в assets/fonts.

Все гарнитуры распространяются по SIL Open Font License 1.1, поэтому их можно
класть в дистрибутив приложения. Скрипт нужен один раз — при сборке окружения;
само приложение в рантайме сеть не трогает.

    python tools/fetch_fonts.py
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "fonts"

# family -> (запрос к legacy css API, список подмножеств)
FAMILIES = {
    "IBM Plex Sans": ("IBM+Plex+Sans:400,500,600", "latin,latin-ext,cyrillic"),
    "IBM Plex Mono": ("IBM+Plex+Mono:400,600", "latin,latin-ext,cyrillic"),
    "Old Standard TT": ("Old+Standard+TT:400,700,400italic", "latin,latin-ext,cyrillic"),
    "PT Serif": ("PT+Serif:400,700,400italic", "latin,latin-ext,cyrillic"),
    "PT Sans Narrow": ("PT+Sans+Narrow:400,700", "latin,latin-ext,cyrillic"),
    "Oswald": ("Oswald:500,600,700", "latin,latin-ext,cyrillic"),
    "UnifrakturMaguntia": ("UnifrakturMaguntia:400", "latin,latin-ext"),
    "Bodoni Moda": ("Bodoni+Moda:400,700,400italic", "latin,latin-ext"),
}

FACE_RE = re.compile(
    r"font-family:\s*'([^']+)';\s*font-style:\s*(\w+);\s*font-weight:\s*(\d+);"
    r"(?:[^}]*?)src:\s*url\((https://[^)]+\.ttf)\)",
    re.S,
)


def slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", text)


def fetch(url: str, binary: bool = False) -> bytes | str:
    request = urllib.request.Request(url, headers={"User-Agent": "python-urllib"})
    data = urllib.request.urlopen(request, timeout=60).read()
    return data if binary else data.decode("utf-8")


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for family, (spec, subsets) in FAMILIES.items():
        css = fetch(f"https://fonts.googleapis.com/css?family={spec}&subset={subsets}")
        faces = FACE_RE.findall(css)
        if not faces:
            print(f"!! {family}: не удалось разобрать css", file=sys.stderr)
            return 1
        for name, style, weight, url in faces:
            suffix = "Italic" if style == "italic" else ""
            filename = f"{slug(name)}-{weight}{suffix}.ttf"
            target = DEST / filename
            if not target.exists():
                target.write_bytes(fetch(url, binary=True))
            manifest.append(
                {
                    "family": name,
                    "style": style,
                    "weight": int(weight),
                    "file": filename,
                    "size": target.stat().st_size,
                }
            )
            print(f"{filename:38} {target.stat().st_size // 1024:5} KB")
    (DEST / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    total = sum(int(item["size"]) for item in manifest)
    print(f"\nвсего {len(manifest)} начертаний, {total / 1024 / 1024:.1f} МБ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
