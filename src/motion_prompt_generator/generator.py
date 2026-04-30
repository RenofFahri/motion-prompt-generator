"""Pure-Python prompt generation engine (no external API required).

The :class:`PromptGenerator` produces deterministic-but-varied prompts by sampling
from curated taxonomies in :mod:`.data`. Each call to :meth:`generate_batch`
returns a list of :class:`PromptResult` items, each carrying both the rendered
video-generation prompt and a stock-marketplace metadata block (title, keywords,
description, category) ready for Adobe Stock / Shutterstock CSV uploads.
"""

from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from . import data


@dataclass
class PromptConfig:
    """User-supplied configuration for a generation run."""

    subject: str
    style: str = "3D"
    motion: str = "Slow Rotation"
    intensity: str = "Medium"
    duration_seconds: int = 10
    aspect_ratio: str = "16:9"
    resolution: str = "4K"
    fps: int = 30
    target_tool: str = "Generic"
    extra_modifiers: str = ""
    count: int = 5
    seed: int | None = None
    stock_safe: bool = True


@dataclass
class StockMetadata:
    """Metadata block sized for Adobe Stock & Shutterstock submission forms."""

    title: str
    description: str
    keywords: list[str]
    category: str

    def keyword_csv(self) -> str:
        return ", ".join(self.keywords)


@dataclass
class PromptResult:
    """A single generated prompt plus its companion stock metadata."""

    prompt: str
    negative_prompt: str
    metadata: StockMetadata
    config_snapshot: dict[str, Any] = field(default_factory=dict)


# ----- Helpers ----------------------------------------------------------------------


_NEGATIVE_DEFAULTS = (
    "low quality, blurry, pixelated, jpeg artifacts, watermark, signature, text, "
    "logo, brand name, distorted faces, extra limbs, flickering, stutter, "
    "inconsistent lighting"
)


def _slugify_subject(subject: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9\s]", " ", subject)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _title_case(text: str) -> str:
    small = {"a", "an", "the", "of", "and", "or", "in", "on", "for", "with", "to"}
    words = text.split()
    out: list[str] = []
    for i, w in enumerate(words):
        lw = w.lower()
        if 0 < i < len(words) - 1 and lw in small:
            out.append(lw)
        else:
            out.append(lw.capitalize() if not w.isupper() else w)
    return " ".join(out)


# ----- Generator -------------------------------------------------------------------


class PromptGenerator:
    """Deterministic, taxonomy-driven prompt generator (offline)."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    # -- Public API ---------------------------------------------------------------

    def generate_batch(self, config: PromptConfig) -> list[PromptResult]:
        if not config.subject.strip():
            raise ValueError("Subject is required.")
        if config.seed is not None:
            self._rng.seed(config.seed)

        results: list[PromptResult] = []
        for _ in range(max(1, min(config.count, 50))):
            results.append(self._generate_one(config))
        return results

    # -- Internals ----------------------------------------------------------------

    def _generate_one(self, config: PromptConfig) -> PromptResult:
        subject = _slugify_subject(config.subject)
        style_clause = data.STYLES.get(config.style, data.STYLES["3D"])
        motion_clause = data.MOTIONS.get(config.motion, data.MOTIONS["Slow Rotation"])
        intensity_clause = data.INTENSITY_MODIFIERS.get(
            config.intensity, data.INTENSITY_MODIFIERS["Medium"]
        )

        camera = self._rng.choice(data.CAMERAS)
        lighting = self._rng.choice(data.LIGHTINGS)
        palette = self._rng.choice(data.PALETTES)
        mood = self._rng.choice(data.MOODS)
        quality = ", ".join(self._rng.sample(data.QUALITY_KEYWORDS, k=3))

        parts: list[str] = [
            f"{style_clause} of {subject}",
            motion_clause,
            camera,
            lighting,
            palette,
            f"{mood} mood",
            intensity_clause,
            quality,
        ]
        if config.stock_safe:
            parts.extend(data.STOCK_SAFE_MODIFIERS)
        if config.extra_modifiers.strip():
            parts.append(config.extra_modifiers.strip())
        parts.extend(
            [
                f"{config.aspect_ratio} aspect ratio",
                f"{config.resolution} resolution",
                f"{config.fps} fps",
                f"{config.duration_seconds}s duration",
            ]
        )

        body = ", ".join(parts)
        profile = data.TOOL_PROFILES.get(config.target_tool, data.TOOL_PROFILES["Generic"])
        prompt = f"{profile['prefix']}{body}".rstrip()
        if profile["suffix"]:
            prompt = f"{prompt}. {profile['suffix']}"

        metadata = self._build_metadata(config, style=config.style, motion=config.motion,
                                        palette=palette, mood=mood)

        return PromptResult(
            prompt=prompt,
            negative_prompt=_NEGATIVE_DEFAULTS,
            metadata=metadata,
            config_snapshot=asdict(config),
        )

    def _build_metadata(
        self,
        config: PromptConfig,
        *,
        style: str,
        motion: str,
        palette: str,
        mood: str,
    ) -> StockMetadata:
        subject_clean = _slugify_subject(config.subject)
        title = _title_case(
            f"{subject_clean} {style} motion graphics {motion.lower()} loop background"
        )
        # Adobe Stock allows up to 200 chars, Shutterstock recommends < 200. Cap at 180.
        if len(title) > 180:
            title = title[:177].rstrip() + "..."

        description = (
            f"{_title_case(subject_clean)} animated as {style.lower()} motion graphics with "
            f"{motion.lower()}, {palette}, {mood} mood. Seamlessly loopable {config.aspect_ratio} "
            f"{config.resolution} background suitable for intros, presentations, social media, "
            f"and broadcast use. Generated with AI."
        )

        # Build keyword list: subject tokens + style/motion/palette tokens + bank top-ups.
        kw: list[str] = []
        for token in subject_clean.lower().split():
            if len(token) > 2:
                kw.append(token)
        kw.extend(
            [
                style.lower(),
                "motion graphics",
                "animation",
                "background",
                "loop",
                "seamless loop",
                motion.lower(),
                mood.lower(),
                config.resolution.lower(),
                config.aspect_ratio,
                f"{config.fps}fps",
            ]
        )
        # Pull a deterministic-ish slice from the keyword bank to round it out toward 30-40.
        bank = list(data.KEYWORD_BANK)
        self._rng.shuffle(bank)
        for word in bank:
            if len(kw) >= 40:
                break
            if word.lower() not in (k.lower() for k in kw):
                kw.append(word)

        # Dedup while preserving order.
        seen: set[str] = set()
        deduped: list[str] = []
        for k in kw:
            kl = k.lower()
            if kl in seen:
                continue
            seen.add(kl)
            deduped.append(k)

        category = self._guess_category(config, mood)
        return StockMetadata(title=title, description=description, keywords=deduped, category=category)

    @staticmethod
    def _guess_category(config: PromptConfig, mood: str) -> str:
        s = (config.subject + " " + config.style + " " + mood).lower()
        if any(w in s for w in ("tech", "digital", "data", "circuit", "ai", "future", "cyber")):
            return "Technology"
        if any(w in s for w in ("nature", "tree", "ocean", "forest", "mountain", "flower", "leaf")):
            return "Nature"
        if any(w in s for w in ("business", "corporate", "office", "finance", "money", "chart")):
            return "Business / Finance"
        if any(w in s for w in ("food", "drink", "coffee", "cocktail", "fruit")):
            return "Food and Drink"
        if any(w in s for w in ("music", "beat", "audio", "sound", "wave")):
            return "Music"
        if config.style.lower() in {"abstract", "liquid", "particle", "glitch", "holographic"}:
            return "Abstract"
        return "Backgrounds / Textures"
