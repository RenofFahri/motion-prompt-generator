"""Persisted user settings: window state, last-used inputs, optional Gemini key.

The file lives under the platform-appropriate user config dir (``~/.config`` on
Linux, ``%APPDATA%`` on Windows). Secrets are stored in plain JSON — clearly
marked in the README — because this is a single-user desktop tool.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"
    veo_model: str = "veo-3.1-generate-preview"
    veo_render_duration: int = 8
    last_subject: str = ""
    last_style: str = "3D"
    last_motion: str = "Slow Rotation"
    last_intensity: str = "Medium"
    last_target_tool: str = "Generic"
    last_count: int = 5
    last_duration: int = 10
    last_resolution: str = "4K"
    last_fps: int = 30
    last_aspect_ratio: str = "16:9"
    last_extra_modifiers: str = ""
    stock_safe: bool = True
    appearance_mode: str = "dark"  # "dark" / "light" / "system"
    extras: dict = field(default_factory=dict)


def _config_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "motion-prompt-generator"


def config_path() -> Path:
    return _config_dir() / "config.json"


def load() -> AppConfig:
    path = config_path()
    if not path.exists():
        return AppConfig()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return AppConfig()
        cfg = AppConfig()
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
            else:
                cfg.extras[key] = value
        return cfg
    except (OSError, json.JSONDecodeError):
        return AppConfig()


def save(cfg: AppConfig) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
    return path
