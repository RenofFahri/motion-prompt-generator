"""Optional Gemini-backed enhancement for prompts.

The app works offline; this module is only imported when the user enables AI
enhancement and provides an API key. ``google-generativeai`` is an optional
dependency — install it with ``pip install motion-prompt-generator[ai]``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .generator import PromptResult

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


@dataclass
class GeminiClient:
    api_key: str
    model: str = "gemini-2.0-flash"

    def __post_init__(self) -> None:
        try:
            import google.generativeai as genai  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - exercised only without the optional dep
            raise RuntimeError(
                "google-generativeai is not installed. Install with `pip install "
                "motion-prompt-generator[ai]` (or `pip install google-generativeai`)."
            ) from exc
        genai.configure(api_key=self.api_key)
        self._genai = genai
        self._model = genai.GenerativeModel(self.model, system_instruction=SYSTEM_INSTRUCTION)

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
        response = self._model.generate_content(
            user,
            generation_config={
                "temperature": 0.9,
                "top_p": 0.95,
                "response_mime_type": "application/json",
            },
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
        """A stable short-list shown in the settings dropdown."""
        return [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
