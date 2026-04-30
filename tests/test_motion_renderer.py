"""Tests for the procedural local motion renderer."""
# ruff: noqa: E402, I001

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("PIL")
pytest.importorskip("imageio")
pytest.importorskip("imageio_ffmpeg")

from motion_prompt_generator.generator import PromptConfig  # noqa: E402
from motion_prompt_generator.motion_renderer import (  # noqa: E402
    DEFAULT_MAX_WIDTH,
    _MOTION_KIND,
    _resolve_dims,
    render_motion,
)


def _cfg(**kw) -> PromptConfig:
    base = PromptConfig(
        subject="glow ring", style="Neon", motion="Particle Flow",
        intensity="Medium", duration_seconds=1, fps=10, aspect_ratio="16:9",
        seed=7,
    )
    for k, v in kw.items():
        setattr(base, k, v)
    return base


def test_resolve_dims_clamps_to_max_width() -> None:
    w, h = _resolve_dims("16:9", max_width=480)
    assert w == 480
    assert h % 2 == 0
    assert h < 480  # 16:9 means h < w


def test_every_taxonomy_motion_maps_to_a_painter_kind() -> None:
    from motion_prompt_generator.data import MOTIONS

    for motion in MOTIONS:
        assert motion in _MOTION_KIND, f"Motion '{motion}' is unmapped in renderer"


def test_render_motion_writes_a_playable_mp4(tmp_path: Path) -> None:
    out = render_motion(_cfg(), tmp_path / "out.mp4", max_width=320)
    assert out.exists()
    # ftyp box must appear in the first 64 bytes of any MP4 / MOV file.
    head = out.read_bytes()[:64]
    assert b"ftyp" in head, f"Output is not a valid MP4 (head={head!r})"
    # 1s @ 10fps + headers should still be at least a few KB.
    assert out.stat().st_size > 1000


def test_render_motion_uses_max_width_argument(tmp_path: Path) -> None:
    out = render_motion(_cfg(), tmp_path / "out.mp4", max_width=320)
    assert out.exists() and out.stat().st_size > 0


def test_render_motion_progress_callback_is_invoked(tmp_path: Path) -> None:
    seen: list[tuple[str, float]] = []

    def progress(msg: str, frac: float) -> None:
        seen.append((msg, frac))

    render_motion(_cfg(), tmp_path / "out.mp4", on_progress=progress, max_width=320)
    assert seen, "progress callback was never called"
    fractions = [f for _, f in seen]
    assert fractions[0] == 0.0
    assert fractions[-1] == 1.0
    assert all(0.0 <= f <= 1.0 for f in fractions)


@pytest.mark.parametrize("motion", [
    "Slow Rotation", "Zoom In", "Zoom Out", "Liquid Wave", "Pulse / Beat",
    "Float / Levitate", "Particle Flow", "Explode / Assemble", "Kinetic Loop",
    "Tracking Pan", "Static Hero Shot", "Parallax",
])
def test_each_motion_kind_renders_without_crashing(tmp_path: Path, motion: str) -> None:
    out = render_motion(_cfg(motion=motion), tmp_path / f"{motion}.mp4", max_width=240)
    assert out.exists() and out.stat().st_size > 1000


def test_default_max_width_constant() -> None:
    assert DEFAULT_MAX_WIDTH == 1280
