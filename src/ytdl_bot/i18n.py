from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "fa", "ar", "zh", "ru", "es")


@dataclass(frozen=True, slots=True)
class LanguageInfo:
    code: str
    label: str


LANGUAGE_INFOS: tuple[LanguageInfo, ...] = (
    LanguageInfo("en", "English"),
    LanguageInfo("fa", "فارسی"),
    LanguageInfo("ar", "العربية"),
    LanguageInfo("zh", "中文"),
    LanguageInfo("ru", "Русский"),
    LanguageInfo("es", "Español"),
)


class I18n:
    def __init__(self, locales_dir: Path) -> None:
        self._messages: dict[str, dict[str, str]] = {}
        for code in SUPPORTED_LANGUAGES:
            path = locales_dir / f"{code}.json"
            if not path.exists():
                raise FileNotFoundError(f"Missing locale file: {path}")
            data = json.loads(path.read_text(encoding="utf-8"))
            self._messages[code] = {str(k): str(v) for k, v in data.items()}

        if DEFAULT_LANGUAGE not in self._messages:
            raise RuntimeError("English locale is required")

    def language(self, code: str | None) -> str:
        if not code:
            return DEFAULT_LANGUAGE
        code = code.lower()
        if code in self._messages:
            return code
        return DEFAULT_LANGUAGE

    def t(self, lang: str | None, key: str, **kwargs: Any) -> str:
        code = self.language(lang)
        template = self._messages.get(code, {}).get(key)
        if template is None:
            template = self._messages[DEFAULT_LANGUAGE].get(key, key)
        if kwargs:
            return template.format(**kwargs)
        return template

    @property
    def languages(self) -> tuple[LanguageInfo, ...]:
        return LANGUAGE_INFOS