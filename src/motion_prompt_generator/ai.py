"""Optional Gemini- and Veo-backed enhancement / video generation.

The app works fully offline; this module is only imported when the user enables AI
enhancement or clicks "Render Video (Veo)" and provides an API key.
``google-genai`` is an optional dependency — install with
``pip install motion-prompt-generator[ai]``.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .generator import PromptResult

# ----- Model catalogues --------------------------------------------------------------

# Text models the user can pick for AI Enhance (prompt rewriting).
GEMINI_TEXT_MODELS: list[str] = [
    # Gemini 3 series (preview, frontier)
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    # Gemini 2.5 series (stable, cheaper)
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    # Legacy 2.0 series (kept for users on older billing tiers)
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

# Veo video-generation models. Newer = better quality but slower / more expensive.
VEO_VIDEO_MODELS: list[str] = [
    "veo-3.1-generate-preview",
    "veo-3.0-generate",
    "veo-2.0-generate-001",
]

DEFAULT_GEMINI_TEXT_MODEL = "gemini-3-flash-preview"
DEFAULT_VEO_MODEL = "veo-3.1-generate-preview"


# ----- Prompt-rewriting Gemini client ------------------------------------------------

SYSTEM_INSTRUCTION = """\
You are an expert prompt engineer for AI text-to-video models (Veo, Runway Gen-3, Pika, Kling, Sora).
You craft prompts for stock-marketplace motion graphics (Adobe Stock, Shutterstock).

Rules:
- Keep cinematic, descriptive, comma-separated phrasing.
- Never include text, logos, brand names, recognizable faces, or watermarks in the scene.
- Always favor seamlessly loopable, broadcast-quality, abstract motion-graphic looks.
- Stay under 800 characters per prompt.
- Return strict JSON only — no prose, no markdown fences.
"""

_USER_TEMPLATE = """\
Original draft prompt:
\"\"\"{prompt}\"\"\"

Subject: {subject}
Target tool: {tool}
Aspect ratio: {aspect}
Duration: {duration}s
Resolution: {resolution}

Rewrite this into {variations} highly detailed, distinct variations optimised for the target tool.
For EACH variation also produce stock-marketplace metadata.

Respond with strict JSON of the shape:
{{
  "variations": [
    {{
      "prompt": "...",
      "title": "... (max 180 chars)",
      "description": "... (1-2 sentences)",
      "keywords": ["...", "..."],   // 25-45 single or short multi-word keywords
      "category": "..."             // one of: Backgrounds / Textures, Technology, Abstract, Nature, Business / Finance, Music, Food and Drink, Lifestyle, Industrial, Healthcare, Education, Sports / Recreation, Science
    }}
  ]
}}
"""


def _import_genai():
    """Import the google-genai SDK lazily so the rest of the app runs without it."""
    try:
        from google import genai  # type: ignore[import-not-found]
        from google.genai import types  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - exercised only without the optional dep
        raise RuntimeError(
            "google-genai is not installed. Install with `pip install "
            "motion-prompt-generator[ai]` (or `pip install google-genai`)."
        ) from exc
    return genai, types


@dataclass
class GeminiClient:
    """Rewrites prompts + metadata using a Gemini text model."""

    api_key: str
    model: str = DEFAULT_GEMINI_TEXT_MODEL

    def __post_init__(self) -> None:
        genai, types = _import_genai()
        self._genai = genai
        self._types = types
        self._client = genai.Client(api_key=self.api_key)

    def enhance(self, base: PromptResult, variations: int = 3) -> list[dict]:
        """Return a list of dicts shaped like the JSON contract above."""
        cfg = base.config_snapshot
        user = _USER_TEMPLATE.format(
            prompt=base.prompt,
            subject=cfg.get("subject", ""),
            tool=cfg.get("target_tool", "Generic"),
            aspect=cfg.get("aspect_ratio", "16:9"),
            duration=cfg.get("duration_seconds", 10),
            resolution=cfg.get("resolution", "4K"),
            variations=max(1, min(variations, 10)),
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=user,
            config=self._types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.9,
                top_p=0.95,
                response_mime_type="application/json",
            ),
        )
        text = (response.text or "").strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Gemini returned non-JSON response: {text[:300]}") from exc
        variations_out = payload.get("variations") if isinstance(payload, dict) else None
        if not isinstance(variations_out, list) or not variations_out:
            raise RuntimeError(f"Gemini returned an unexpected payload: {text[:300]}")
        return variations_out

    @staticmethod
    def list_models() -> list[str]:
        return list(GEMINI_TEXT_MODELS)


# ----- Veo video-generation client --------------------------------------------------


@dataclass
class VeoClient:
    """Renders prompts to MP4 files using the Veo video models."""

    api_key: str
    model: str = DEFAULT_VEO_MODEL

    def __post_init__(self) -> None:
        genai, types = _import_genai()
        self._genai = genai
        self._types = types
        self._client = genai.Client(api_key=self.api_key)

    def render(
        self,
        prompt: str,
        output_path: Path | str,
        *,
        duration_seconds: int = 8,
        aspect_ratio: str = "16:9",
        number_of_videos: int = 1,
        enhance_prompt: bool = True,
        on_progress: Callable[[str], None] | None = None,
        poll_interval: float = 15.0,
        timeout_seconds: float = 600.0,
    ) -> Path:
        """Generate a video and save it to ``output_path``. Returns the saved path.

        ``on_progress`` is called with short status strings (e.g. "submitting",
        "polling (45s elapsed)", "downloading") so the UI can show progress.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if on_progress:
            on_progress(f"submitting to {self.model}")

        # GenerateVideosConfig fields are loosely typed — we pass only widely supported ones.
        config_kwargs: dict[str, object] = {
            "number_of_videos": max(1, min(number_of_videos, 4)),
            "duration_seconds": max(1, min(duration_seconds, 60)),
            "aspect_ratio": aspect_ratio,
            "enhance_prompt": enhance_prompt,
        }
        try:
            config = self._types.GenerateVideosConfig(**config_kwargs)
        except TypeError:
            # Older SDK versions may not accept every kwarg — fall back to minimal config.
            config = self._types.GenerateVideosConfig(
                number_of_videos=config_kwargs["number_of_videos"],
                duration_seconds=config_kwargs["duration_seconds"],
            )

        operation = self._client.models.generate_videos(
            model=self.model,
            prompt=prompt,
            config=config,
        )

        started = time.monotonic()
        while not getattr(operation, "done", False):
            elapsed = int(time.monotonic() - started)
            if elapsed > timeout_seconds:
                raise RuntimeError(
                    f"Veo render timed out after {timeout_seconds:.0f}s — try a shorter "
                    f"duration or a different model."
                )
            if on_progress:
                on_progress(f"polling Veo… {elapsed}s elapsed")
            time.sleep(poll_interval)
            operation = self._client.operations.get(operation)

        response = getattr(operation, "response", None)
        videos = getattr(response, "generated_videos", None) or []
        if not videos:
            error = getattr(operation, "error", None)
            raise RuntimeError(f"Veo returned no videos. Error: {error}")

        if on_progress:
            on_progress("downloading MP4")
        video = videos[0].video
        # The genai SDK exposes either .save(path) or .data (bytes). Try both.
        try:
            video.save(str(out))
        except AttributeError:
            data = getattr(video, "data", None) or getattr(video, "video_bytes", None)
            if not data:
                raise RuntimeError(  # noqa: B904
                    "Veo response object has no .save() and no bytes payload."
                )
            out.write_bytes(data)

        if on_progress:
            on_progress("done")
        return out

    @staticmethod
    def list_models() -> list[str]:
        return list(VEO_VIDEO_MODELS)
