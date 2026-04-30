"""Tests for the AI module's static surface (no SDK calls).

These tests deliberately avoid instantiating ``GeminiClient`` / ``VeoClient`` so they
work whether or not the optional ``google-genai`` dependency is installed.
"""

from __future__ import annotations

from motion_prompt_generator.ai import (
    DEFAULT_GEMINI_TEXT_MODEL,
    DEFAULT_VEO_MODEL,
    GEMINI_TEXT_MODELS,
    VEO_VIDEO_MODELS,
    GeminiClient,
    VeoClient,
)


def test_gemini_models_include_3_flash_and_3_1_pro() -> None:
    assert "gemini-3-flash-preview" in GEMINI_TEXT_MODELS
    assert "gemini-3.1-pro-preview" in GEMINI_TEXT_MODELS
    # Newer Gemini 3 models are listed first.
    assert GEMINI_TEXT_MODELS[0].startswith("gemini-3")


def test_veo_models_include_3_1_and_2_0() -> None:
    assert "veo-3.1-generate-preview" in VEO_VIDEO_MODELS
    assert "veo-2.0-generate-001" in VEO_VIDEO_MODELS


def test_default_models_are_in_their_lists() -> None:
    assert DEFAULT_GEMINI_TEXT_MODEL in GEMINI_TEXT_MODELS
    assert DEFAULT_VEO_MODEL in VEO_VIDEO_MODELS


def test_static_list_models_helpers_match() -> None:
    assert GeminiClient.list_models() == GEMINI_TEXT_MODELS
    assert VeoClient.list_models() == VEO_VIDEO_MODELS
