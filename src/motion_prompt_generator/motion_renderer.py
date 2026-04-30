"""Procedural motion-graphics renderer (no AI / no API calls).

Generates an MP4 directly from a :class:`PromptConfig` by drawing each frame with
numpy + Pillow and encoding via ``imageio`` (which ships its own ffmpeg binary).

Output is intentionally **abstract** broadcast-style motion graphics — the kind of
loops, backgrounds and transitions that sell on Adobe Stock / Shutterstock — not
photorealistic representations of the literal subject text. Colour palettes are
derived from the chosen Style and Mood; motion is driven by the chosen Motion
type.

The renderer is fully deterministic when ``seed`` is set on the config.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .generator import PromptConfig

# Map style names to two anchor RGB colours. The renderer interpolates between
# them — and varies hue per-frame for some motion types — to keep the output
# visually distinct without needing a colour expert.
_STYLE_PALETTES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "3D":          ((22, 30, 64),  (180, 210, 255)),
    "2D":          ((255, 215, 90), (245, 90, 130)),
    "8bit":        ((40, 30, 90),  (255, 90, 200)),
    "Flat":        ((30, 144, 255), (255, 220, 120)),
    "Isometric":   ((45, 60, 110), (140, 220, 200)),
    "Cinematic":   ((10, 14, 30),  (220, 150, 70)),
    "Abstract":    ((90, 30, 140), (240, 220, 90)),
    "Liquid":      ((10, 60, 120), (140, 240, 210)),
    "Particle":    ((5, 5, 25),    (180, 220, 255)),
    "Glitch":      ((20, 20, 30),  (255, 60, 200)),
    "Holographic": ((20, 80, 200), (240, 100, 255)),
    "Low-Poly":    ((40, 70, 90),  (240, 200, 130)),
    "Paper-Cut":   ((250, 230, 200), (90, 150, 200)),
    "Neon":        ((10, 0, 30),   (0, 255, 220)),
    "Watercolor":  ((230, 240, 250), (130, 180, 220)),
}

# Aspect ratio → (width, height) tuples. Width is clamped to keep render time
# reasonable; users wanting true 4K upload-ready clips can re-encode externally.
_ASPECT_TO_DIMS: dict[str, tuple[int, int]] = {
    "16:9": (1280, 720),
    "9:16": (720, 1280),
    "1:1":  (960, 960),
    "4:5":  (960, 1200),
    "21:9": (1680, 720),
}

# Map every taxonomy motion name to one of a handful of primitive motion kinds
# implemented below. Several names share a primitive but with different
# parameters so the result still differs on screen.
_MOTION_KIND: dict[str, str] = {
    "Slow Rotation":      "rotation",
    "Orbiting Camera":    "rotation",
    "Zoom In":            "zoom_in",
    "Zoom Out":           "zoom_out",
    "Parallax":           "parallax",
    "Morph Transition":   "wave",
    "Kinetic Loop":       "kinetic",
    "Particle Flow":      "particles",
    "Liquid Wave":        "wave",
    "Pulse / Beat":       "pulse",
    "Float / Levitate":   "float",
    "Explode / Assemble": "explode",
    "Drone Flythrough":   "zoom_in",
    "Static Hero Shot":   "static",
    "Tracking Pan":       "pan",
}

DEFAULT_FPS = 30
MAX_DURATION_SECONDS = 30
DEFAULT_MAX_WIDTH = 1280

# Intensity strings → motion magnitude multiplier.
_INTENSITY: dict[str, float] = {"Simple": 0.55, "Medium": 1.0, "High": 1.6}


def _palette(style: str) -> tuple[np.ndarray, np.ndarray]:
    a, b = _STYLE_PALETTES.get(style, _STYLE_PALETTES["3D"])
    return np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)


def _resolve_dims(aspect_ratio: str, max_width: int = DEFAULT_MAX_WIDTH) -> tuple[int, int]:
    w, h = _ASPECT_TO_DIMS.get(aspect_ratio, _ASPECT_TO_DIMS["16:9"])
    if w > max_width:
        scale = max_width / w
        w = max_width
        h = int(round(h * scale / 2) * 2)  # keep even for h264
    return w, h


def _gradient_background(w: int, h: int, c1: np.ndarray, c2: np.ndarray, angle: float) -> np.ndarray:
    """Return a (h, w, 3) uint8 linear gradient between c1 and c2."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (xx / max(w - 1, 1)) - 0.5
    ny = (yy / max(h - 1, 1)) - 0.5
    t = nx * math.cos(angle) + ny * math.sin(angle)
    t = (t - t.min()) / max(np.ptp(t), 1e-6)
    grad = c1[None, None, :] * (1.0 - t)[..., None] + c2[None, None, :] * t[..., None]
    return np.clip(grad, 0, 255).astype(np.uint8)


# ----- Per-kind frame painters -------------------------------------------------


def _paint_rotation(frame: int, total: int, w: int, h: int, c1, c2, intensity: float) -> Image.Image:
    t = frame / max(total - 1, 1)
    angle = 2 * math.pi * t * intensity * 0.5
    bg = _gradient_background(w, h, c1, c2, angle)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = w / 2, h / 2
    for i in range(6):
        radius = (min(w, h) * (0.15 + 0.08 * i)) * (1 + 0.05 * math.sin(2 * math.pi * t + i))
        rotation = angle * (1 + 0.3 * i)
        for spoke in range(8):
            sa = rotation + spoke * (math.pi / 4)
            x = cx + radius * math.cos(sa)
            y = cy + radius * math.sin(sa)
            r = max(2, int(min(w, h) * 0.012))
            alpha = int(120 - i * 14)
            draw.ellipse((x - r, y - r, x + r, y + r),
                         fill=(int(c2[0]), int(c2[1]), int(c2[2]), alpha))
    return img.filter(ImageFilter.GaussianBlur(radius=1.2))


def _paint_zoom(frame: int, total: int, w: int, h: int, c1, c2, intensity: float, *, into: bool) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, math.pi * 0.25)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = w / 2, h / 2
    rings = 24
    for i in range(rings):
        progress = ((i / rings) + (t if into else (1.0 - t)) * intensity) % 1.0
        radius = progress * (max(w, h) * 0.85)
        thickness = max(1, int(min(w, h) * 0.006))
        alpha = int(220 * (1 - progress))
        col = (int(c2[0]), int(c2[1]), int(c2[2]), alpha)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                     outline=col, width=thickness)
    return img


def _paint_parallax(frame: int, total: int, w: int, h: int, c1, c2, intensity: float) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, 0.0)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    layers = 5
    for layer in range(layers):
        speed = (layer + 1) / layers * intensity
        offset = (t * speed) % 1.0
        y_band = int(h * (0.15 + layer * 0.15))
        band_h = int(h * 0.08)
        for k in range(8):
            x = ((k / 8 + offset) % 1.0) * w
            col = (
                int(c2[0] * (0.5 + 0.5 * (layer / layers))),
                int(c2[1] * (0.6 + 0.4 * (layer / layers))),
                int(c2[2] * (0.7 + 0.3 * (layer / layers))),
                160 - layer * 18,
            )
            draw.rectangle((x - 60, y_band, x + 60, y_band + band_h), fill=col)
    return img


def _paint_wave(frame: int, total: int, w: int, h: int, c1, c2, intensity: float) -> Image.Image:
    t = frame / max(total - 1, 1)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = xx / w
    ny = yy / h
    wave = (
        np.sin(nx * 6 * math.pi + 2 * math.pi * t * intensity) * 0.5
        + np.sin(ny * 4 * math.pi - 2 * math.pi * t * intensity * 0.7) * 0.5
    )
    wave = (wave + 1) * 0.5  # 0..1
    grad = c1[None, None, :] * (1 - wave[..., None]) + c2[None, None, :] * wave[..., None]
    arr = np.clip(grad, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=2.0))
    return img


def _paint_pulse(frame: int, total: int, w: int, h: int, c1, c2, intensity: float) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, math.pi * 0.5)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = w / 2, h / 2
    base = min(w, h) * 0.12
    pulses = 5
    for i in range(pulses):
        phase = (t * intensity + i / pulses) % 1.0
        radius = base + phase * min(w, h) * 0.45
        alpha = int(220 * (1 - phase))
        col = (int(c2[0]), int(c2[1]), int(c2[2]), alpha)
        thickness = max(2, int(min(w, h) * 0.008))
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                     outline=col, width=thickness)
    core = base * (0.95 + 0.1 * math.sin(2 * math.pi * t * intensity * 2))
    draw.ellipse((cx - core, cy - core, cx + core, cy + core),
                 fill=(int(c2[0]), int(c2[1]), int(c2[2]), 240))
    return img.filter(ImageFilter.GaussianBlur(radius=1.5))


def _paint_float(frame: int, total: int, w: int, h: int, c1, c2, intensity: float, rng) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, math.pi * 0.7)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    if not hasattr(_paint_float, "_seeds") or _paint_float._seeds.get("rng") is not rng:
        _paint_float._seeds = {
            "rng": rng,
            "shapes": [(rng.random(), rng.random(), rng.uniform(0.4, 1.0))
                       for _ in range(20)],
        }
    for sx, sy, scale in _paint_float._seeds["shapes"]:
        bob = math.sin(2 * math.pi * (t * intensity + sx)) * 0.06
        x = sx * w
        y = (sy + bob) * h
        r = scale * min(w, h) * 0.05
        col = (int(c2[0]), int(c2[1]), int(c2[2]), int(160 * scale))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=col)
    return img.filter(ImageFilter.GaussianBlur(radius=1.6))


def _paint_particles(
    frame: int, total: int, w: int, h: int, c1, c2, intensity: float, rng
) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, math.pi * 0.3)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    if not hasattr(_paint_particles, "_seeds") or _paint_particles._seeds.get("rng") is not rng:
        _paint_particles._seeds = {
            "rng": rng,
            "particles": [
                (rng.random(), rng.random(), rng.uniform(0.5, 1.6),
                 rng.uniform(0.6, 1.4))
                for _ in range(220)
            ],
        }
    for sx, sy, speed, size in _paint_particles._seeds["particles"]:
        x = ((sx + t * speed * intensity) % 1.0) * w
        y = (sy + 0.04 * math.sin(2 * math.pi * t * speed + sx * 6)) * h
        r = size * min(w, h) * 0.005
        col = (int(c2[0]), int(c2[1]), int(c2[2]), 200)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=col)
    return img


def _paint_explode(
    frame: int, total: int, w: int, h: int, c1, c2, intensity: float, rng
) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, math.pi * 0.1)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = w / 2, h / 2
    if not hasattr(_paint_explode, "_seeds") or _paint_explode._seeds.get("rng") is not rng:
        _paint_explode._seeds = {
            "rng": rng,
            "vecs": [(rng.uniform(0, 2 * math.pi), rng.uniform(0.4, 1.0))
                     for _ in range(160)],
        }
    # Triangle wave: out, back, out, back ...
    phase = 1.0 - abs(2 * (t * intensity % 1.0) - 1.0)
    for ang, mag in _paint_explode._seeds["vecs"]:
        radius = phase * mag * min(w, h) * 0.45
        x = cx + math.cos(ang) * radius
        y = cy + math.sin(ang) * radius
        r = max(2, int(min(w, h) * 0.006 * mag))
        col = (int(c2[0]), int(c2[1]), int(c2[2]), 220)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=col)
    return img


def _paint_kinetic(frame: int, total: int, w: int, h: int, c1, c2, intensity: float) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, math.pi * 0.6)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    cell_w = w / 8
    cell_h = h / 6
    for ix in range(8):
        for iy in range(6):
            phase = ((ix + iy) / 14 + t * intensity) % 1.0
            size = max(2.0, (0.45 + 0.35 * math.sin(2 * math.pi * phase)) * min(cell_w, cell_h))
            cx = (ix + 0.5) * cell_w
            cy = (iy + 0.5) * cell_h
            col = (int(c2[0]), int(c2[1]), int(c2[2]),
                   int(80 + 120 * (0.5 + 0.5 * math.sin(2 * math.pi * phase))))
            draw.rectangle((cx - size / 2, cy - size / 2, cx + size / 2, cy + size / 2),
                           fill=col)
    return img


def _paint_pan(frame: int, total: int, w: int, h: int, c1, c2, intensity: float) -> Image.Image:
    t = frame / max(total - 1, 1)
    big = _gradient_background(w * 2, h, c1, c2, 0.0)
    offset = int((t * intensity) * w) % w
    panned = np.concatenate((big[:, offset:offset + w, :],), axis=1)
    if panned.shape[1] < w:
        panned = np.pad(panned, ((0, 0), (0, w - panned.shape[1]), (0, 0)), mode="edge")
    img = Image.fromarray(panned[:, :w, :])
    draw = ImageDraw.Draw(img, "RGBA")
    for i in range(6):
        x = ((i / 6 + t * intensity) % 1.0) * w
        col = (int(c2[0]), int(c2[1]), int(c2[2]), 100)
        draw.line((x, 0, x, h), fill=col, width=max(2, int(w * 0.004)))
    return img


def _paint_static(frame: int, total: int, w: int, h: int, c1, c2, intensity: float) -> Image.Image:
    t = frame / max(total - 1, 1)
    bg = _gradient_background(w, h, c1, c2, math.pi * 0.25 + 0.05 * math.sin(2 * math.pi * t))
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img, "RGBA")
    cx, cy = w / 2, h / 2
    breathing = 1 + 0.03 * math.sin(2 * math.pi * t * intensity)
    radius = min(w, h) * 0.22 * breathing
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 fill=(int(c2[0]), int(c2[1]), int(c2[2]), 220))
    return img.filter(ImageFilter.GaussianBlur(radius=2.0))


_PAINTERS_NEED_RNG = {"float", "particles", "explode"}


def _paint(kind: str, frame: int, total: int, w: int, h: int, c1, c2,
           intensity: float, rng: random.Random) -> Image.Image:
    if kind == "rotation":
        return _paint_rotation(frame, total, w, h, c1, c2, intensity)
    if kind == "zoom_in":
        return _paint_zoom(frame, total, w, h, c1, c2, intensity, into=True)
    if kind == "zoom_out":
        return _paint_zoom(frame, total, w, h, c1, c2, intensity, into=False)
    if kind == "parallax":
        return _paint_parallax(frame, total, w, h, c1, c2, intensity)
    if kind == "wave":
        return _paint_wave(frame, total, w, h, c1, c2, intensity)
    if kind == "pulse":
        return _paint_pulse(frame, total, w, h, c1, c2, intensity)
    if kind == "float":
        return _paint_float(frame, total, w, h, c1, c2, intensity, rng)
    if kind == "particles":
        return _paint_particles(frame, total, w, h, c1, c2, intensity, rng)
    if kind == "explode":
        return _paint_explode(frame, total, w, h, c1, c2, intensity, rng)
    if kind == "kinetic":
        return _paint_kinetic(frame, total, w, h, c1, c2, intensity)
    if kind == "pan":
        return _paint_pan(frame, total, w, h, c1, c2, intensity)
    if kind == "static":
        return _paint_static(frame, total, w, h, c1, c2, intensity)
    # Fallback for any unmapped motion name.
    return _paint_pulse(frame, total, w, h, c1, c2, intensity)


# ----- Public API --------------------------------------------------------------


def render_motion(
    cfg: PromptConfig,
    output_path: Path | str,
    *,
    on_progress: Callable[[str, float], None] | None = None,
    max_width: int = DEFAULT_MAX_WIDTH,
) -> Path:
    """Render an MP4 driven by ``cfg`` and return the saved path.

    ``on_progress(message, fraction)`` is called periodically (fraction in [0, 1]).
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    duration = max(1, min(int(cfg.duration_seconds or 6), MAX_DURATION_SECONDS))
    fps = max(8, min(int(cfg.fps or DEFAULT_FPS), 60))
    total_frames = duration * fps
    w, h = _resolve_dims(cfg.aspect_ratio or "16:9", max_width=max_width)
    c1, c2 = _palette(cfg.style or "3D")
    kind = _MOTION_KIND.get(cfg.motion or "Slow Rotation", "pulse")
    intensity = _INTENSITY.get(cfg.intensity or "Medium", 1.0)
    rng = random.Random(cfg.seed if cfg.seed is not None else 0)

    # Reset cached per-painter seeds so two consecutive renders with different
    # rng instances don't reuse stale point clouds.
    for fn in (_paint_float, _paint_particles, _paint_explode):
        if hasattr(fn, "_seeds"):
            delattr(fn, "_seeds")

    # imageio is imported lazily so the rest of the app starts even if the
    # ``[render]`` extra is absent.
    try:
        import imageio.v2 as imageio  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Local renderer needs imageio + imageio-ffmpeg. Install with "
            "`pip install motion-prompt-generator[render]`."
        ) from exc

    if on_progress:
        on_progress(f"opening {out.name} ({w}x{h} @ {fps} fps, {duration}s)", 0.0)

    writer = imageio.get_writer(
        str(out), fps=fps, codec="libx264", quality=8, macro_block_size=2,
        pixelformat="yuv420p", ffmpeg_log_level="error",
    )
    try:
        for frame in range(total_frames):
            img = _paint(kind, frame, total_frames, w, h, c1, c2, intensity, rng)
            writer.append_data(np.asarray(img.convert("RGB")))
            if on_progress and (frame % max(1, total_frames // 20) == 0):
                on_progress(f"frame {frame + 1}/{total_frames}",
                            (frame + 1) / total_frames)
    finally:
        writer.close()

    if on_progress:
        on_progress("done", 1.0)
    return out
