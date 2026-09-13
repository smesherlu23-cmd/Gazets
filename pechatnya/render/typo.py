"""Микротипографика набора: кавычки, тире, неразрывные пробелы.

Пользователь набирает текст как удобно — прямыми кавычками, дефисом вместо
тире. На полосе это сразу видно и выдаёт «не газету». Здесь текст приводится
к наборному виду при рендере; сам текст в проекте не меняется, поэтому правку
всегда можно отменить выключателем в оформлении издания.
"""

from __future__ import annotations

import re

NBSP = " "  # неразрывный пробел
THIN = " "  # тонкий пробел — между инициалами и в числах

# Короткие слова, после которых перенос строки выглядит сиротливо.
SHORT_WORDS = (
    "а в и к о с у я не ни но да же ли бы от до из за по на об во ко со то the"
).split()

_QUOTE_OPEN = re.compile(r'(^|[\s([{<—–-])"')
_QUOTE_CLOSE = re.compile(r'"')
_DASH_PAIR = re.compile(r"(\s)-{1,2}(\s)")
_DASH_START = re.compile(r"(^|\n)-\s")
_ELLIPSIS = re.compile(r"\.{3,}")
_NUMBER_GROUPS = re.compile(r"(?<=\d)\s(?=\d{3}\b)")
_INITIALS = re.compile(r"\b([А-ЯA-Z])\.\s*([А-ЯA-Z])\.\s*(?=[А-ЯA-Z][а-яa-z])")
_SINGLE_INITIAL = re.compile(r"\b([А-ЯA-Z])\.\s+(?=[А-ЯA-Z][а-яa-z])")
_NUMERO = re.compile(r"№\s*(?=\d)")
_ABBREV = re.compile(r"\b(т)\.\s*(д|п|е|ч)\.")
_UNITS = re.compile(r"(?<=\d)\s+(?=(?:р|к|мм|см|м|км|кг|г|ч|мин|%)\b)")


def _short_words_pattern() -> re.Pattern[str]:
    # заглядывание назад, а не захват: иначе два коротких слова подряд
    # («и на пристани») склеиваются только через одно
    words = "|".join(sorted(SHORT_WORDS, key=len, reverse=True))
    return re.compile(rf"(?:(?<=[\s(«„—-])|^)({words})\s+", re.IGNORECASE)


_SHORT = _short_words_pattern()


def apply(text: str) -> str:
    """Приводит текст к наборному виду. Разметку ``**`` и ``*`` не трогает."""
    if not text:
        return text

    result = _ELLIPSIS.sub("…", text)
    result = _DASH_START.sub(lambda m: f"{m.group(1)}— ", result)
    result = _DASH_PAIR.sub(lambda m: f"{NBSP}—{m.group(2)}", result)

    # кавычки: первая в паре — открывающая, остальные закрывающие
    result = _QUOTE_OPEN.sub(lambda m: f"{m.group(1)}«", result)
    result = _QUOTE_CLOSE.sub("»", result)
    result = result.replace("''", "»").replace("„", "«").replace("“", "»")

    result = _NUMERO.sub(f"№{NBSP}", result)
    result = _NUMBER_GROUPS.sub(THIN, result)
    result = _UNITS.sub(NBSP, result)
    result = _ABBREV.sub(lambda m: f"{m.group(1)}.{NBSP}{m.group(2)}.", result)
    result = _INITIALS.sub(lambda m: f"{m.group(1)}.{THIN}{m.group(2)}.{NBSP}", result)
    result = _SINGLE_INITIAL.sub(lambda m: f"{m.group(1)}.{NBSP}", result)

    # короткие слова липнут к следующему: «в доке», «и на них»
    result = _SHORT.sub(lambda m: f"{m.group(1)}{NBSP}", result)
    return result
