# Motion Graphics Prompt Generator

Desktop GUI app (Python + CustomTkinter) untuk **generate prompt motion graphics** yang siap-pakai di tool video AI seperti **Veo, Runway Gen-3, Pika, Kling, Sora** — lengkap dengan **metadata** (title, description, keywords, category) yang siap diupload ke **Adobe Stock** dan **Shutterstock**.

![Stack: Python 3.10+ · CustomTkinter](https://img.shields.io/badge/python-3.10%2B-blue) ![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Fitur

- **Generate sampai 25 prompt sekaligus** dari 1 ide / konsep
- **15+ visual style**: 3D, 2D, 8-bit, Flat, Isometric, Cinematic, Abstract, Liquid, Particle, Glitch, Holographic, Low-Poly, Paper-Cut, Neon, Watercolor
- **15+ motion type**: Slow Rotation, Orbiting Camera, Zoom In/Out, Parallax, Morph, Kinetic Loop, Particle Flow, Liquid Wave, Pulse, Float, Explode/Assemble, Drone Flythrough, Static Hero, Tracking Pan
- **Tool-aware**: prompt otomatis disesuaikan untuk Veo / Runway Gen-3 / Pika / Kling / Sora / Generic
- **Stock-safe modifiers**: otomatis tambahkan "no text, no logos, no faces, seamlessly loopable, 16:9" supaya video lolos review Adobe Stock & Shutterstock
- **Stock metadata**: title, description, keywords (sampai 40+), kategori — **export langsung ke CSV format Adobe Stock & Shutterstock**
- **Optional Gemini AI enhancement**: rewrite prompt jadi versi yang lebih kaya & beragam (butuh API key gratis dari Google AI Studio). Mendukung **Gemini 3 Flash**, **Gemini 3.1 Pro**, Gemini 2.5 series.
- **Render Video (Local) — gratis & offline**: tombol hijau **Render Video (Local)** menggunakan **renderer procedural built-in** (numpy + Pillow + ffmpeg) untuk menghasilkan MP4 motion-graphics langsung di mesinmu. **Tidak butuh API key, tidak ada biaya, tidak butuh internet.** Cocok untuk broadcast loops, abstract backgrounds, transitions — yang justru paling laku di Adobe Stock / Shutterstock.
- **Optional Veo render (advanced, paid)**: tombol kecil **Render Video (Veo)** memanggil Google Veo (`veo-3.1-generate-preview` / `veo-3.0-generate` / `veo-2.0-generate-001`) untuk hasil photoreal. **Berbayar** — perkiraan $0.35–$0.50 per detik video.
- **100% offline by default** — Gemini & Veo hanya dipakai kalau kamu enable
- **Negative prompt** otomatis: anti low-quality, watermark, distorted faces, flicker
- **Persistent settings**: form terakhir, API key, theme di-remember
- **Dark / Light / System mode**

---

## Quick start

### Prasyarat
- Python 3.10+
- Linux: `sudo apt install python3-tk` (Tkinter biasanya sudah ada di Windows/macOS)

### Install (dev mode dari source)

```bash
git clone https://github.com/RenofFahri/motion-prompt-generator.git
cd motion-prompt-generator
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[ai,render]"                       # all features
motion-prompt-generator                              # atau:  python -m motion_prompt_generator
```

**Optional extras:**

| Extra      | Berisi                                                       | Kapan dibutuhkan                          |
|------------|--------------------------------------------------------------|-------------------------------------------|
| `[render]` | numpy, Pillow, imageio, imageio-ffmpeg                       | **Render Video (Local)** — free / offline |
| `[ai]`     | google-genai                                                 | AI Enhance (Gemini) **dan** Render Veo    |

Minimal install (cuma generate prompt + CSV, tanpa render & AI):

```bash
pip install -e .
```

---

## Cara pakai

1. **Subject / Concept** — tulis ide-mu, contoh:
   - `glowing crystal cube floating in space`
   - `abstract liquid metal flow with iridescent reflections`
   - `cyberpunk hologram city skyline at night`
2. Pilih **Style** + **Motion** + **Intensity**
3. Pilih **Target AI Tool** (Veo / Runway / Pika / Kling / Sora / Generic)
4. Atur **Resolution / FPS / Duration / Aspect Ratio**
5. Slide **count** (1–25) sesuai berapa banyak variasi yang kamu mau
6. Klik **Generate Prompts** → muncul kartu prompt + metadata
7. (Opsional) Klik **AI Enhance (Gemini)** untuk rewrite jadi versi premium
8. **Copy** per-card, **Copy All**, atau **Export**:
   - `.txt` — semua prompt + metadata
   - `Adobe CSV` — siap import di Adobe Stock contributor portal
   - `Shutterstock CSV` — siap import di Shutterstock contributor portal
9. **Render Video (Local)** — klik tombol hijau → pilih lokasi MP4 → app render abstract motion-graphics secara procedural (durasi & FPS sesuai form). Tidak butuh API key.
10. (Opsional) **Render Video (Veo)** — untuk hasil photoreal AI; butuh Gemini API key + billing aktif.

### Alur produksi stock video

1. Buka app → generate 25 prompt + metadata
2. Export Adobe & Shutterstock CSV
3. Pakai prompt-nya di Veo/Runway/Pika/Kling/Sora untuk render video MP4
4. Rename file MP4 sesuai kolom `Filename` di CSV (atau edit CSV)
5. Bulk-upload ke Adobe Stock & Shutterstock — metadata auto-fill dari CSV

---

## Renderer lokal vs Veo

| Aspek        | Render Lokal (default)                  | Render Veo (opsional)               |
|--------------|-----------------------------------------|-------------------------------------|
| Biaya        | **Gratis**                              | ~$0.35–$0.50 / detik (~$3–5 per 8s) |
| Internet     | Tidak butuh                             | Butuh                               |
| API key      | Tidak butuh                             | Butuh Gemini API + billing          |
| Kualitas     | Abstract motion graphics (broadcast-style) | Photoreal AI                     |
| Subject      | Subject text dipakai untuk seed/palette — tidak ada bentuk literal | Mengikuti subject text |
| Cocok untuk  | Loops, backgrounds, transitions, abstract VJ | Hero shots, narrative clips     |
| Output       | MP4 (h264, yuv420p) sesuai aspect ratio | MP4 dari Veo                        |

Untuk produksi stock video, **mayoritas asset yang laku di Adobe Stock & Shutterstock adalah abstract motion graphics** — yang justru lebih cocok dirender pakai mode lokal (gratis & predictable) daripada Veo (mahal & non-deterministik).

---

## Gemini API key (untuk AI Enhance & Veo render)

1. Buka [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → **Create API key** (gratis)
2. Di app klik **Settings (API Key & Models)** → paste → pilih model Gemini & Veo → **Save**
3. Sekarang tombol **AI Enhance (Gemini)** aktif
4. Untuk **Render Video (Veo)** kamu juga perlu **enable billing** di Google AI Studio. Veo dipanggil pakai key yang sama, tapi setiap render menagih akun-mu (~$0.35–$0.50/detik). App akan menampilkan estimasi biaya sebelum mulai render dan minta konfirmasi.

### Model yang didukung

**Gemini text (AI Enhance):**
`gemini-3.1-pro-preview` · `gemini-3-flash-preview` · `gemini-3.1-flash-lite-preview` · `gemini-2.5-pro` · `gemini-2.5-flash` · `gemini-2.5-flash-lite` · `gemini-2.0-flash` · `gemini-2.0-flash-lite`

**Veo video render:**
`veo-3.1-generate-preview` (default, kualitas tertinggi) · `veo-3.0-generate` · `veo-2.0-generate-001` (paling murah)

Key disimpan **lokal** di:
- Linux: `~/.config/motion-prompt-generator/config.json`
- Windows: `%APPDATA%\motion-prompt-generator\config.json`

> ⚠️ File ini plain JSON. Jangan commit ke git, jangan share screenshot folder ini.

---

## Development

```bash
pip install -e ".[dev]"
pytest -q                         # unit tests
ruff check src tests              # linter
```

### Struktur proyek

```
src/motion_prompt_generator/
├── __init__.py
├── __main__.py        # entry point
├── app.py             # CustomTkinter GUI
├── generator.py       # core prompt engine (offline, deterministic)
├── ai.py              # optional Gemini integration
├── data.py            # taxonomies: styles, motions, palettes, modifiers
├── exporter.py        # .txt + Adobe/Shutterstock CSV writers
└── config.py          # persistent app settings
```

### Cara menambah style / motion baru

Edit `src/motion_prompt_generator/data.py` — tambah entry baru ke `STYLES` atau `MOTIONS`. UI dropdown otomatis update.

---

## License

MIT — see [LICENSE](LICENSE).
