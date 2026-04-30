"""Curated taxonomy of styles, motions, and modifiers used by the prompt generator.

The lists are intentionally biased toward looks that perform well on stock-video
marketplaces (Adobe Stock, Shutterstock) — abstract, looping, text-free, broadcast-ready.
"""

from __future__ import annotations

from typing import Final

# ----- Visual styles -----------------------------------------------------------------

STYLES: Final[dict[str, str]] = {
    "3D": "highly detailed 3D rendered motion graphics, octane render, ray-traced reflections, "
          "subsurface scattering, depth of field",
    "2D": "clean 2D motion graphics, vector flat design, smooth After Effects-style animation, "
          "crisp edges",
    "8bit": "retro 8-bit pixel art motion graphics, chiptune aesthetic, limited palette, "
            "scanlines, CRT glow",
    "Flat": "minimalist flat design motion graphics, geometric shapes, bold blocks of color, "
            "Material Design influence",
    "Isometric": "isometric 3D motion graphics, tilted perspective, soft shadows, infographic "
                 "feel, clean geometry",
    "Cinematic": "cinematic motion graphics, photoreal lighting, anamorphic lens flare, film "
                 "grain, moody color grade",
    "Abstract": "abstract motion graphics, non-figurative shapes, flowing geometry, generative "
                "art aesthetic",
    "Liquid": "liquid motion graphics, fluid simulation, viscous flow, refractive surfaces, "
              "iridescent sheen",
    "Particle": "particle system motion graphics, swarming particles, volumetric light, glowing "
                "trails, depth haze",
    "Glitch": "glitch art motion graphics, datamosh artifacts, RGB split, scan distortion, "
              "VHS feedback",
    "Holographic": "holographic motion graphics, iridescent spectrum, prismatic reflections, "
                   "futuristic sci-fi sheen",
    "Low-Poly": "low-poly motion graphics, faceted geometry, flat shading, stylized minimalism",
    "Paper-Cut": "paper-cut craft motion graphics, layered paper, soft drop shadows, tactile "
                 "handmade feel",
    "Neon": "neon-lit motion graphics, glowing tube lights, dark backdrop, vibrant cyberpunk "
            "palette, bloom",
    "Watercolor": "watercolor motion graphics, hand-painted textures, soft bleed edges, "
                  "organic brush strokes",
}

# ----- Motion / animation behaviours -------------------------------------------------

MOTIONS: Final[dict[str, str]] = {
    "Slow Rotation": "slowly rotating around its central axis with smooth easing",
    "Orbiting Camera": "camera slowly orbits around the subject, cinematic dolly arc",
    "Zoom In": "smooth slow zoom-in pushing toward the subject",
    "Zoom Out": "gradual zoom-out revealing the wider scene",
    "Parallax": "multi-layer parallax movement, foreground and background drifting at different speeds",
    "Morph Transition": "elements continuously morph and transition into one another",
    "Kinetic Loop": "perfectly seamless loop, kinetic and rhythmic, beat-synced motion",
    "Particle Flow": "particles streaming in a smooth directional flow",
    "Liquid Wave": "liquid waves rolling and unfolding in slow motion",
    "Pulse / Beat": "rhythmic pulsing with subtle beats, expanding and contracting",
    "Float / Levitate": "elements gently floating and levitating with weightless drift",
    "Explode / Assemble": "parts exploding outward then reassembling into the whole",
    "Drone Flythrough": "drone-style flythrough with smooth forward camera movement",
    "Static Hero Shot": "locked-off camera, subject animates while frame stays still",
    "Tracking Pan": "camera pans laterally tracking the subject",
}

# ----- Camera, lighting, palette, mood -----------------------------------------------

CAMERAS: Final[list[str]] = [
    "static locked-off camera",
    "slow dolly forward",
    "slow dolly backward",
    "smooth orbit camera",
    "subtle handheld motion",
    "crane move from low to high",
    "top-down overhead view",
    "macro close-up lens",
    "wide establishing shot",
]

LIGHTINGS: Final[list[str]] = [
    "soft studio lighting",
    "dramatic cinematic lighting with strong rim light",
    "neon-glow lighting",
    "volumetric god rays",
    "high-key bright lighting",
    "low-key moody lighting",
    "golden hour warm sunlight",
    "cool blue hour ambience",
    "bioluminescent glow",
]

PALETTES: Final[list[str]] = [
    "vibrant saturated colors",
    "pastel soft palette",
    "monochrome black and white",
    "duotone blue and orange",
    "neon cyan and magenta cyberpunk palette",
    "warm sunset gradient",
    "cool oceanic gradient",
    "earth tones, organic palette",
    "metallic gold and silver",
    "iridescent holographic spectrum",
]

MOODS: Final[list[str]] = [
    "energetic",
    "calm and meditative",
    "futuristic",
    "luxurious and premium",
    "playful",
    "mysterious",
    "corporate and professional",
    "dreamy",
    "epic and grand",
]

# ----- Intensity presets -------------------------------------------------------------

INTENSITY_MODIFIERS: Final[dict[str, str]] = {
    "Simple": "subtle minimal motion, restrained animation, clean and uncluttered composition",
    "Medium": "balanced motion with clear focal points, moderate complexity",
    "High": "complex layered animation, rich detail, dynamic high-energy motion, multiple "
            "synchronized elements",
}

# ----- Quality keywords always appended ----------------------------------------------

QUALITY_KEYWORDS: Final[list[str]] = [
    "ultra high detail",
    "8k",
    "professional motion design",
    "broadcast quality",
    "smooth 60fps motion",
    "sharp focus",
]

# ----- Stock-marketplace safety modifiers --------------------------------------------
# Stock sites reject footage with text, watermarks, recognizable logos, faces, or brands.

STOCK_SAFE_MODIFIERS: Final[list[str]] = [
    "no text",
    "no logos",
    "no watermarks",
    "no recognizable faces",
    "no brand references",
    "seamlessly loopable",
    "16:9 aspect ratio",
    "centered composition with safe margins",
]

# ----- Tool-specific phrasing tweaks -------------------------------------------------

TOOL_PROFILES: Final[dict[str, dict[str, str]]] = {
    "Veo (Google)": {
        "prefix": "",
        "suffix": "Cinematic motion, photoreal rendering where applicable, smooth temporal coherence.",
    },
    "Runway Gen-3": {
        "prefix": "[Camera] ",
        "suffix": "Stable subject, cohesive motion, no flicker.",
    },
    "Pika": {
        "prefix": "",
        "suffix": "-camera smooth, -motion fluid",
    },
    "Kling": {
        "prefix": "",
        "suffix": "Smooth professional cinematography, high temporal stability.",
    },
    "Sora": {
        "prefix": "",
        "suffix": "Coherent physics, persistent objects, natural motion.",
    },
    "Generic": {
        "prefix": "",
        "suffix": "",
    },
}

# ----- Stock metadata category buckets -----------------------------------------------

STOCK_CATEGORIES: Final[list[str]] = [
    "Backgrounds / Textures",
    "Business / Finance",
    "Technology",
    "Abstract",
    "Science",
    "Nature",
    "Lifestyle",
    "Industrial",
    "Healthcare",
    "Education",
    "Sports / Recreation",
    "Music",
    "Food and Drink",
]

# Common stock-marketplace keyword bank (not exhaustive — used for auto-suggestion).

KEYWORD_BANK: Final[list[str]] = sorted({
    "abstract", "animation", "background", "loop", "motion", "graphic", "modern", "futuristic",
    "technology", "digital", "design", "geometric", "minimal", "creative", "concept", "art",
    "render", "3d", "cinematic", "broadcast", "intro", "transition", "vibrant", "color",
    "gradient", "particle", "energy", "flow", "wave", "smooth", "elegant", "luxury", "premium",
    "corporate", "presentation", "social media", "advertising", "marketing", "branding",
    "seamless loop", "vertical", "horizontal", "16:9", "ultra hd", "4k", "high quality",
    "lighting", "atmosphere", "dynamic", "fluid", "liquid", "smoke", "fire", "neon", "glow",
    "shine", "reflection", "studio", "scene", "visual", "effect", "vfx",
})
