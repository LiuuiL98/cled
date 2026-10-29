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
    username: str = ""
    maximize_edge: bool = True
    lock_x_ratio: float | None = None
    lock_y_ratio: float | None = None
    lock_maximize: bool | None = None

    @property
    def has_lock_position(self) -> bool:
        return (
            isinstance(self.lock_x_ratio, (int, float))
            and isinstance(self.lock_y_ratio, (int, float))
            and 0.0 <= float(self.lock_x_ratio) <= 1.0
            and 0.0 <= float(self.lock_y_ratio) <= 1.0
        )

    @classmethod
    def load(cls, path: Path) -> "Settings":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            allowed = {key: data[key] for key in cls.__dataclass_fields__ if key in data}
            settings = cls(**allowed)
            if not settings.has_lock_position:
                settings.lock_x_ratio = None
                settings.lock_y_ratio = None
                settings.lock_maximize = None
            return settings
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
