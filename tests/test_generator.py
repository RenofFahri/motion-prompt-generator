"""Tests for the offline prompt generation engine and exporters."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from motion_prompt_generator import exporter
from motion_prompt_generator.generator import PromptConfig, PromptGenerator


def _basic_config(**overrides) -> PromptConfig:
    base = PromptConfig(subject="glowing crystal cube", count=3, seed=42)
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_generate_batch_returns_requested_count() -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(count=5))
    assert len(results) == 5
    for r in results:
        assert "glowing crystal cube" in r.prompt.lower()
        assert r.metadata.title
        assert r.metadata.description
        assert len(r.metadata.keywords) >= 15
        assert r.metadata.category


def test_generate_batch_respects_seed_for_reproducibility() -> None:
    gen_a = PromptGenerator()
    gen_b = PromptGenerator()
    a = gen_a.generate_batch(_basic_config(count=3, seed=123))
    b = gen_b.generate_batch(_basic_config(count=3, seed=123))
    assert [r.prompt for r in a] == [r.prompt for r in b]


def test_subject_required() -> None:
    gen = PromptGenerator()
    with pytest.raises(ValueError):
        gen.generate_batch(PromptConfig(subject="   "))


def test_stock_safe_modifiers_omitted_when_disabled() -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(stock_safe=False, count=1))
    assert "no logos" not in results[0].prompt.lower()


def test_stock_safe_modifiers_included_by_default() -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(count=1))
    assert "no logos" in results[0].prompt.lower()
    assert "loopable" in results[0].prompt.lower()


def test_target_tool_suffix_applied() -> None:
    gen = PromptGenerator()
    runway = gen.generate_batch(_basic_config(target_tool="Runway Gen-3", count=1))[0]
    assert runway.prompt.startswith("[Camera] ")


def test_keywords_are_unique_and_normalised() -> None:
    gen = PromptGenerator()
    r = gen.generate_batch(_basic_config(count=1))[0]
    lowered = [k.lower() for k in r.metadata.keywords]
    assert len(lowered) == len(set(lowered))
    assert len(lowered) <= 50


def test_export_text_writes_all_prompts(tmp_path: Path) -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(count=3))
    out = exporter.write_text_batch(tmp_path / "prompts.txt", results)
    text = out.read_text(encoding="utf-8")
    for i in range(1, 4):
        assert f"=== Prompt #{i} ===" in text
    assert text.count("Title:") == 3


def test_adobe_stock_csv_columns(tmp_path: Path) -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(count=2))
    out = exporter.write_adobe_stock_csv(tmp_path / "adobe.csv", results)
    with out.open(encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    assert rows[0] == exporter.ADOBE_HEADERS
    assert len(rows) == 3
    assert rows[1][0].endswith(".mp4")
    assert rows[1][1]  # title
    assert rows[1][2]  # keywords
    assert rows[1][3]  # category


def test_shutterstock_csv_columns(tmp_path: Path) -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(count=2))
    out = exporter.write_shutterstock_csv(tmp_path / "shutterstock.csv", results)
    with out.open(encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    assert rows[0] == exporter.SHUTTERSTOCK_HEADERS
    assert len(rows) == 3
    # Editorial / Mature / Illustration default to "no"
    assert rows[1][4] == "no"
    assert rows[1][5] == "no"
    assert rows[1][6] == "no"


def test_count_is_clamped_to_50() -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(count=999))
    assert len(results) == 50


def test_count_minimum_is_one() -> None:
    gen = PromptGenerator()
    results = gen.generate_batch(_basic_config(count=0))
    assert len(results) == 1


def test_category_inferred_from_subject() -> None:
    gen = PromptGenerator()
    tech = gen.generate_batch(_basic_config(subject="ai circuit board glow", count=1))[0]
    nature = gen.generate_batch(_basic_config(subject="forest leaf canopy", count=1))[0]
    assert tech.metadata.category == "Technology"
    assert nature.metadata.category == "Nature"


def test_mountain_subject_is_nature_not_technology() -> None:
    """Regression: 'mountain' contains the substring 'ai' but must NOT be Technology."""
    gen = PromptGenerator()
    for subject in ("mountain peak at sunrise", "rain on glass", "painting on wall",
                    "train station platform"):
        result = gen.generate_batch(_basic_config(subject=subject, count=1))[0]
        assert result.metadata.category != "Technology", (
            f"Subject '{subject}' wrongly tagged as Technology")
    # And the canonical "mountain" subject should specifically resolve to Nature.
    mountain = gen.generate_batch(_basic_config(subject="mountain peak at sunrise", count=1))[0]
    assert mountain.metadata.category == "Nature"


def test_prompt_does_not_contradict_user_aspect_ratio() -> None:
    """Regression: STOCK_SAFE_MODIFIERS used to hardcode '16:9 aspect ratio'."""
    gen = PromptGenerator()
    result = gen.generate_batch(_basic_config(subject="vertical glow ring",
                                              aspect_ratio="9:16", count=1))[0]
    body = result.prompt.lower()
    # The user-selected aspect ratio must be present.
    assert "9:16" in body
    # The contradictory hardcoded fragment must NOT be present.
    assert "16:9 aspect ratio" not in body


def test_vary_themes_produces_distinct_style_motion_per_prompt() -> None:
    """Each prompt in a varied batch must have a unique (style, motion) pair."""
    gen = PromptGenerator()
    n = 5
    results = gen.generate_batch(_basic_config(count=n, vary_themes=True, seed=7))
    pairs = [
        (r.config_snapshot["style"], r.config_snapshot["motion"]) for r in results
    ]
    assert len(set(pairs)) == n, f"expected {n} unique themes, got {pairs}"


def test_vary_themes_first_variant_honours_user_pick() -> None:
    """The first prompt always uses the style/motion the user explicitly picked."""
    gen = PromptGenerator()
    cfg = _basic_config(
        count=4, vary_themes=True, style="Liquid", motion="Liquid Wave", seed=11,
    )
    results = gen.generate_batch(cfg)
    first = results[0].config_snapshot
    assert (first["style"], first["motion"]) == ("Liquid", "Liquid Wave")


def test_vary_themes_disabled_keeps_same_theme() -> None:
    """With vary_themes off, every variant reuses the user-picked theme."""
    gen = PromptGenerator()
    cfg = _basic_config(
        count=5, vary_themes=False, style="Neon", motion="Pulse / Beat", seed=3,
    )
    results = gen.generate_batch(cfg)
    pairs = {(r.config_snapshot["style"], r.config_snapshot["motion"]) for r in results}
    assert pairs == {("Neon", "Pulse / Beat")}


def test_vary_themes_count_one_is_not_forced_unique() -> None:
    """A single prompt batch is always the user's own pick, vary or not."""
    gen = PromptGenerator()
    r = gen.generate_batch(
        _basic_config(count=1, vary_themes=True, style="3D", motion="Slow Rotation")
    )[0]
    assert r.config_snapshot["style"] == "3D"
    assert r.config_snapshot["motion"] == "Slow Rotation"
