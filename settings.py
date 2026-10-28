from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_LOGIN_URL = "https://elearningbluefe.e-chinalife.com/els/learner-studentpc-fe/"


def app_data_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    path = base / "ChinaLifeEShopAssistant"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


@dataclass
class Settings:
    login_url: str = DEFAULT_LOGIN_URL
    target_url: str = ""
    success_url_contains: str = ""
    success_selector: str = ""
    keep_profile: bool = True

    @classmethod
    def load(cls, path: Path) -> "Settings":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            allowed = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
            return cls(**allowed)
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
