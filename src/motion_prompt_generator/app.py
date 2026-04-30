"""CustomTkinter GUI for Motion Graphics Prompt Generator."""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

try:  # ``pyperclip`` is optional but recommended for cross-platform clipboard support.
    import pyperclip  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    pyperclip = None  # type: ignore[assignment]

from . import config as cfg_store
from . import data, exporter
from .generator import PromptConfig, PromptGenerator, PromptResult, StockMetadata

APP_TITLE = "Motion Graphics Prompt Generator"
PADX = 10
PADY = 6


class App(ctk.CTk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self._cfg = cfg_store.load()
        ctk.set_appearance_mode(self._cfg.appearance_mode)
        ctk.set_default_color_theme("blue")

        self.title(APP_TITLE)
        self.geometry("1280x820")
        self.minsize(1080, 720)

        self._generator = PromptGenerator()
        self._results: list[PromptResult] = []

        self._build_layout()
        self._restore_last_inputs()

    # ----- Layout ----------------------------------------------------------------

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=0, minsize=420)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()
        self._build_status_bar()

    def _build_left_panel(self) -> None:
        panel = ctk.CTkFrame(self, corner_radius=10)
        panel.grid(row=0, column=0, padx=(PADX, 6), pady=(PADX, 0), sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(panel, text="Inputs", font=ctk.CTkFont(size=18, weight="bold"))
        header.grid(row=0, column=0, padx=PADX, pady=(PADX, 4), sticky="w")

        scroll = ctk.CTkScrollableFrame(panel, corner_radius=8, fg_color="transparent")
        scroll.grid(row=1, column=0, padx=PADX, pady=(0, PADY), sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        # --- Subject -------------------------------------------------------------
        ctk.CTkLabel(scroll, text="Subject / Concept", anchor="w").grid(row=0, column=0, sticky="ew")
        self.subject_text = ctk.CTkTextbox(scroll, height=90)
        self.subject_text.grid(row=1, column=0, sticky="ew", pady=(2, PADY))

        # --- Style + Motion + Intensity -----------------------------------------
        self.style_var = tk.StringVar(value=self._cfg.last_style)
        self.motion_var = tk.StringVar(value=self._cfg.last_motion)
        self.intensity_var = tk.StringVar(value=self._cfg.last_intensity)
        self.target_tool_var = tk.StringVar(value=self._cfg.last_target_tool)

        self._add_optionmenu(scroll, 2, "Style", self.style_var, list(data.STYLES.keys()))
        self._add_optionmenu(scroll, 4, "Motion Type", self.motion_var, list(data.MOTIONS.keys()))
        self._add_optionmenu(
            scroll, 6, "Animation Intensity", self.intensity_var, list(data.INTENSITY_MODIFIERS.keys())
        )
        self._add_optionmenu(
            scroll, 8, "Target AI Tool", self.target_tool_var, list(data.TOOL_PROFILES.keys())
        )

        # --- Resolution / FPS / Duration / Aspect / Count -----------------------
        self.duration_var = tk.IntVar(value=self._cfg.last_duration)
        self.fps_var = tk.IntVar(value=self._cfg.last_fps)
        self.count_var = tk.IntVar(value=self._cfg.last_count)
        self.resolution_var = tk.StringVar(value=self._cfg.last_resolution)
        self.aspect_var = tk.StringVar(value=self._cfg.last_aspect_ratio)

        self._add_optionmenu(scroll, 10, "Resolution", self.resolution_var, ["720p", "1080p", "1440p", "4K"])
        self._add_optionmenu(scroll, 12, "Aspect Ratio", self.aspect_var, ["16:9", "9:16", "1:1", "4:5", "21:9"])

        ctk.CTkLabel(scroll, text="FPS", anchor="w").grid(row=14, column=0, sticky="ew")
        self.fps_slider = ctk.CTkSlider(scroll, from_=24, to=60, number_of_steps=36,
                                        command=lambda v: self.fps_var.set(int(float(v))))
        self.fps_slider.set(self.fps_var.get())
        self.fps_slider.grid(row=15, column=0, sticky="ew", pady=(0, 2))
        self.fps_label = ctk.CTkLabel(scroll, text=f"{self.fps_var.get()} fps", anchor="w")
        self.fps_label.grid(row=16, column=0, sticky="ew", pady=(0, PADY))
        self.fps_var.trace_add("write", lambda *_: self.fps_label.configure(text=f"{self.fps_var.get()} fps"))

        ctk.CTkLabel(scroll, text="Duration (seconds)", anchor="w").grid(row=17, column=0, sticky="ew")
        self.duration_slider = ctk.CTkSlider(scroll, from_=3, to=30, number_of_steps=27,
                                             command=lambda v: self.duration_var.set(int(float(v))))
        self.duration_slider.set(self.duration_var.get())
        self.duration_slider.grid(row=18, column=0, sticky="ew", pady=(0, 2))
        self.duration_label = ctk.CTkLabel(scroll, text=f"{self.duration_var.get()}s", anchor="w")
        self.duration_label.grid(row=19, column=0, sticky="ew", pady=(0, PADY))
        self.duration_var.trace_add("write", lambda *_: self.duration_label.configure(
            text=f"{self.duration_var.get()}s"))

        ctk.CTkLabel(scroll, text="How many prompts (1-25)", anchor="w").grid(row=20, column=0, sticky="ew")
        self.count_slider = ctk.CTkSlider(scroll, from_=1, to=25, number_of_steps=24,
                                          command=lambda v: self.count_var.set(int(float(v))))
        self.count_slider.set(self.count_var.get())
        self.count_slider.grid(row=21, column=0, sticky="ew", pady=(0, 2))
        self.count_label = ctk.CTkLabel(scroll, text=f"{self.count_var.get()} prompts", anchor="w")
        self.count_label.grid(row=22, column=0, sticky="ew", pady=(0, PADY))
        self.count_var.trace_add("write", lambda *_: self.count_label.configure(
            text=f"{self.count_var.get()} prompts"))

        ctk.CTkLabel(scroll, text="Extra modifiers (optional)", anchor="w").grid(row=23, column=0, sticky="ew")
        self.extra_entry = ctk.CTkEntry(scroll, placeholder_text="e.g. studio Ghibli inspired, retro vibe")
        self.extra_entry.grid(row=24, column=0, sticky="ew", pady=(2, PADY))

        # --- Toggles ------------------------------------------------------------
        self.stock_safe_var = tk.BooleanVar(value=self._cfg.stock_safe)
        ctk.CTkSwitch(
            scroll,
            text="Stock-safe modifiers (no text/logos/faces, loopable)",
            variable=self.stock_safe_var,
        ).grid(row=25, column=0, sticky="w", pady=(0, PADY))

        # --- Action buttons -----------------------------------------------------
        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.grid(row=2, column=0, padx=PADX, pady=(0, PADX), sticky="ew")
        actions.grid_columnconfigure((0, 1), weight=1)

        self.generate_btn = ctk.CTkButton(
            actions, text="Generate Prompts", command=self.on_generate, height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.generate_btn.grid(row=0, column=0, padx=(0, 4), pady=(0, 4), sticky="ew")

        self.enhance_btn = ctk.CTkButton(
            actions, text="AI Enhance (Gemini)", command=self.on_ai_enhance, height=40,
            fg_color="#7c3aed", hover_color="#6d28d9"
        )
        self.enhance_btn.grid(row=0, column=1, padx=(4, 0), pady=(0, 4), sticky="ew")

        self.settings_btn = ctk.CTkButton(
            actions, text="Settings (API Key)", command=self.on_open_settings, height=32,
            fg_color="transparent", border_width=1, border_color="#444"
        )
        self.settings_btn.grid(row=1, column=0, columnspan=2, sticky="ew")

    def _add_optionmenu(
        self, parent: ctk.CTkScrollableFrame, row_start: int, label: str,
        var: tk.StringVar, values: list[str]
    ) -> None:
        ctk.CTkLabel(parent, text=label, anchor="w").grid(row=row_start, column=0, sticky="ew")
        ctk.CTkOptionMenu(parent, variable=var, values=values).grid(
            row=row_start + 1, column=0, sticky="ew", pady=(2, PADY)
        )

    def _build_right_panel(self) -> None:
        panel = ctk.CTkFrame(self, corner_radius=10)
        panel.grid(row=0, column=1, padx=(6, PADX), pady=(PADX, 0), sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.grid(row=0, column=0, padx=PADX, pady=(PADX, 4), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Generated Prompts",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")

        export_bar = ctk.CTkFrame(header, fg_color="transparent")
        export_bar.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(export_bar, text="Copy All", width=90, command=self.on_copy_all).grid(
            row=0, column=0, padx=(0, 4))
        ctk.CTkButton(export_bar, text="Save .txt", width=90, command=self.on_export_txt).grid(
            row=0, column=1, padx=4)
        ctk.CTkButton(export_bar, text="Adobe CSV", width=100, command=self.on_export_adobe).grid(
            row=0, column=2, padx=4)
        ctk.CTkButton(export_bar, text="Shutterstock CSV", width=140,
                      command=self.on_export_shutterstock).grid(row=0, column=3, padx=(4, 0))

        self.results_frame = ctk.CTkScrollableFrame(panel, corner_radius=8)
        self.results_frame.grid(row=1, column=0, padx=PADX, pady=(0, PADX), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)

        self._render_empty_state()

    def _render_empty_state(self) -> None:
        for child in self.results_frame.winfo_children():
            child.destroy()
        msg = (
            "No prompts yet.\n\n"
            "1. Type a subject (e.g. \"glowing crystal cube\", \"abstract liquid metal flow\")\n"
            "2. Pick a style + motion\n"
            "3. Click Generate Prompts\n\n"
            "Tip: enable AI Enhance for richer Gemini-rewritten variations\n"
            "(needs a Gemini API key — set in Settings)."
        )
        ctk.CTkLabel(
            self.results_frame, text=msg, justify="left",
            font=ctk.CTkFont(size=13), text_color="#888"
        ).grid(row=0, column=0, padx=PADX, pady=PADX, sticky="w")

    def _build_status_bar(self) -> None:
        self.status_var = tk.StringVar(value="Ready.")
        status = ctk.CTkLabel(
            self, textvariable=self.status_var, anchor="w", font=ctk.CTkFont(size=12)
        )
        status.grid(row=1, column=0, columnspan=2, padx=PADX, pady=(2, PADX), sticky="ew")

    # ----- State persistence -----------------------------------------------------

    def _restore_last_inputs(self) -> None:
        if self._cfg.last_subject:
            self.subject_text.insert("1.0", self._cfg.last_subject)
        if self._cfg.last_extra_modifiers:
            self.extra_entry.insert(0, self._cfg.last_extra_modifiers)

    def _persist_inputs(self, prompt_cfg: PromptConfig) -> None:
        self._cfg.last_subject = prompt_cfg.subject
        self._cfg.last_style = prompt_cfg.style
        self._cfg.last_motion = prompt_cfg.motion
        self._cfg.last_intensity = prompt_cfg.intensity
        self._cfg.last_target_tool = prompt_cfg.target_tool
        self._cfg.last_count = prompt_cfg.count
        self._cfg.last_duration = prompt_cfg.duration_seconds
        self._cfg.last_resolution = prompt_cfg.resolution
        self._cfg.last_fps = prompt_cfg.fps
        self._cfg.last_aspect_ratio = prompt_cfg.aspect_ratio
        self._cfg.last_extra_modifiers = prompt_cfg.extra_modifiers
        self._cfg.stock_safe = prompt_cfg.stock_safe
        cfg_store.save(self._cfg)

    # ----- Actions ---------------------------------------------------------------

    def _read_form(self) -> PromptConfig:
        subject = self.subject_text.get("1.0", "end").strip()
        return PromptConfig(
            subject=subject,
            style=self.style_var.get(),
            motion=self.motion_var.get(),
            intensity=self.intensity_var.get(),
            duration_seconds=int(self.duration_var.get()),
            aspect_ratio=self.aspect_var.get(),
            resolution=self.resolution_var.get(),
            fps=int(self.fps_var.get()),
            target_tool=self.target_tool_var.get(),
            extra_modifiers=self.extra_entry.get().strip(),
            count=int(self.count_var.get()),
            stock_safe=self.stock_safe_var.get(),
        )

    def on_generate(self) -> None:
        try:
            cfg = self._read_form()
            self._results = self._generator.generate_batch(cfg)
        except ValueError as exc:
            messagebox.showwarning("Missing input", str(exc))
            return
        self._persist_inputs(cfg)
        self._render_results()
        self.status_var.set(f"Generated {len(self._results)} prompts (offline templates).")

    def on_ai_enhance(self) -> None:
        if not self._cfg.gemini_api_key:
            messagebox.showinfo(
                "Gemini API key required",
                "Open Settings and paste your Gemini API key to use AI enhancement.\n\n"
                "Get a free key at https://aistudio.google.com/app/apikey",
            )
            return
        cfg = self._read_form()
        if not cfg.subject.strip():
            messagebox.showwarning("Missing input", "Subject is required.")
            return
        self._persist_inputs(cfg)
        self.status_var.set("Calling Gemini... this may take a few seconds.")
        self.enhance_btn.configure(state="disabled")
        self.generate_btn.configure(state="disabled")

        def _worker() -> None:
            try:
                from .ai import GeminiClient

                base = self._generator.generate_batch(
                    PromptConfig(**{**cfg.__dict__, "count": 1})
                )[0]
                client = GeminiClient(api_key=self._cfg.gemini_api_key, model=self._cfg.gemini_model)
                variations = client.enhance(base, variations=cfg.count)
                results = self._merge_ai_variations(base, variations, cfg)
                self.after(0, lambda: self._on_ai_done(results, None))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda exc=exc: self._on_ai_done([], exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _merge_ai_variations(
        self, base: PromptResult, variations: list[dict], cfg: PromptConfig
    ) -> list[PromptResult]:
        out: list[PromptResult] = []
        for v in variations:
            keywords = v.get("keywords") or []
            if not isinstance(keywords, list):
                keywords = [str(keywords)]
            md = StockMetadata(
                title=str(v.get("title") or base.metadata.title)[:200],
                description=str(v.get("description") or base.metadata.description),
                keywords=[str(k) for k in keywords][:50],
                category=str(v.get("category") or base.metadata.category),
            )
            out.append(
                PromptResult(
                    prompt=str(v.get("prompt") or base.prompt),
                    negative_prompt=base.negative_prompt,
                    metadata=md,
                    config_snapshot=base.config_snapshot,
                )
            )
        return out or [base]

    def _on_ai_done(self, results: list[PromptResult], error: Exception | None) -> None:
        self.enhance_btn.configure(state="normal")
        self.generate_btn.configure(state="normal")
        if error:
            self.status_var.set(f"AI enhance failed: {error}")
            messagebox.showerror("AI enhance failed", str(error))
            return
        self._results = results
        self._render_results()
        self.status_var.set(f"AI generated {len(results)} enhanced prompts.")

    # ----- Rendering -------------------------------------------------------------

    def _render_results(self) -> None:
        for child in self.results_frame.winfo_children():
            child.destroy()
        if not self._results:
            self._render_empty_state()
            return
        for i, r in enumerate(self._results, 1):
            self._render_result_card(i, r)

    def _render_result_card(self, index: int, result: PromptResult) -> None:
        card = ctk.CTkFrame(self.results_frame, corner_radius=8)
        card.grid(sticky="ew", padx=4, pady=6)
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, padx=PADX, pady=(PADX, 2), sticky="ew")
        head.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            head, text=f"#{index} — {result.metadata.title}",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w", justify="left", wraplength=720,
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            head, text="Copy", width=70,
            command=lambda r=result: self._copy_to_clipboard(r.prompt, "Prompt copied."),
        ).grid(row=0, column=1, padx=(6, 0))

        prompt_box = ctk.CTkTextbox(card, height=110, wrap="word")
        prompt_box.grid(row=1, column=0, padx=PADX, pady=(2, 4), sticky="ew")
        prompt_box.insert("1.0", result.prompt)
        prompt_box.configure(state="disabled")

        meta_row = ctk.CTkFrame(card, fg_color="transparent")
        meta_row.grid(row=2, column=0, padx=PADX, pady=(0, 4), sticky="ew")
        meta_row.grid_columnconfigure(0, weight=1)
        meta = (
            f"Category: {result.metadata.category}    |    "
            f"{len(result.metadata.keywords)} keywords    |    "
            f"Negative: included"
        )
        ctk.CTkLabel(meta_row, text=meta, anchor="w", text_color="#9ca3af",
                     font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            meta_row, text="Copy keywords", width=120,
            command=lambda r=result: self._copy_to_clipboard(r.metadata.keyword_csv(), "Keywords copied."),
        ).grid(row=0, column=1, padx=4)
        ctk.CTkButton(
            meta_row, text="Copy metadata", width=120,
            command=lambda r=result: self._copy_to_clipboard(self._metadata_block(r), "Metadata copied."),
        ).grid(row=0, column=2)

    @staticmethod
    def _metadata_block(r: PromptResult) -> str:
        return (
            f"Title: {r.metadata.title}\n"
            f"Description: {r.metadata.description}\n"
            f"Category: {r.metadata.category}\n"
            f"Keywords: {r.metadata.keyword_csv()}\n"
        )

    # ----- Clipboard / export ----------------------------------------------------

    def _copy_to_clipboard(self, text: str, status: str) -> None:
        try:
            if pyperclip is not None:
                pyperclip.copy(text)
            else:  # pragma: no cover - fallback
                self.clipboard_clear()
                self.clipboard_append(text)
            self.status_var.set(status)
        except Exception as exc:  # noqa: BLE001
            self.status_var.set(f"Clipboard error: {exc}")

    def on_copy_all(self) -> None:
        if not self._results:
            self.status_var.set("Nothing to copy yet.")
            return
        body = "\n\n".join(
            f"=== Prompt #{i} ===\n{r.prompt}\n\n{self._metadata_block(r)}"
            for i, r in enumerate(self._results, 1)
        )
        self._copy_to_clipboard(body, f"Copied {len(self._results)} prompts to clipboard.")

    def _ensure_results(self) -> bool:
        if not self._results:
            messagebox.showinfo("Nothing to export", "Generate prompts first.")
            return False
        return True

    def on_export_txt(self) -> None:
        if not self._ensure_results():
            return
        path = filedialog.asksaveasfilename(
            title="Save prompts as text", defaultextension=".txt",
            filetypes=[("Text", "*.txt")], initialfile="motion_prompts.txt",
        )
        if not path:
            return
        out = exporter.write_text_batch(Path(path), self._results)
        self.status_var.set(f"Saved {out}")

    def on_export_adobe(self) -> None:
        if not self._ensure_results():
            return
        path = filedialog.asksaveasfilename(
            title="Adobe Stock CSV", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")], initialfile="adobe_stock_metadata.csv",
        )
        if not path:
            return
        out = exporter.write_adobe_stock_csv(Path(path), self._results)
        self.status_var.set(f"Saved {out}")
        messagebox.showinfo(
            "Adobe Stock CSV ready",
            f"Saved to:\n{out}\n\n"
            "Upload your .mp4 files to Adobe Stock contributor portal, then import this CSV "
            "to bulk-fill metadata. Replace placeholder filenames if needed.",
        )

    def on_export_shutterstock(self) -> None:
        if not self._ensure_results():
            return
        path = filedialog.asksaveasfilename(
            title="Shutterstock CSV", defaultextension=".csv",
            filetypes=[("CSV", "*.csv")], initialfile="shutterstock_metadata.csv",
        )
        if not path:
            return
        out = exporter.write_shutterstock_csv(Path(path), self._results)
        self.status_var.set(f"Saved {out}")

    # ----- Settings dialog -------------------------------------------------------

    def on_open_settings(self) -> None:
        SettingsDialog(self, self._cfg, on_save=self._on_settings_saved)

    def _on_settings_saved(self) -> None:
        cfg_store.save(self._cfg)
        self.status_var.set("Settings saved.")


class SettingsDialog(ctk.CTkToplevel):
    """Modal-ish settings window for Gemini API key and appearance mode."""

    def __init__(self, master: App, cfg, on_save) -> None:
        super().__init__(master)
        self.title("Settings")
        self.geometry("560x340")
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self._cfg = cfg
        self._on_save = on_save

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="Gemini API key", anchor="w",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=PADX, pady=(PADX, 2), sticky="ew")

        self.key_entry = ctk.CTkEntry(self, show="*", placeholder_text="paste your key")
        self.key_entry.grid(row=1, column=0, padx=PADX, pady=(0, 2), sticky="ew")
        self.key_entry.insert(0, cfg.gemini_api_key)

        ctk.CTkLabel(
            self, anchor="w", justify="left", text_color="#9ca3af",
            text="Stored locally at ~/.config/motion-prompt-generator/config.json.\n"
                 "Get a free key: https://aistudio.google.com/app/apikey",
            font=ctk.CTkFont(size=11),
        ).grid(row=2, column=0, padx=PADX, pady=(0, PADY), sticky="ew")

        ctk.CTkLabel(self, text="Gemini model", anchor="w").grid(
            row=3, column=0, padx=PADX, pady=(PADY, 2), sticky="ew")
        self.model_var = tk.StringVar(value=cfg.gemini_model)
        try:
            from .ai import GeminiClient
            models = GeminiClient.list_models()
        except Exception:
            models = ["gemini-2.0-flash"]
        ctk.CTkOptionMenu(self, variable=self.model_var, values=models).grid(
            row=4, column=0, padx=PADX, pady=(0, PADY), sticky="ew")

        ctk.CTkLabel(self, text="Appearance", anchor="w").grid(
            row=5, column=0, padx=PADX, pady=(PADY, 2), sticky="ew")
        self.appearance_var = tk.StringVar(value=cfg.appearance_mode)
        ctk.CTkOptionMenu(
            self, variable=self.appearance_var, values=["dark", "light", "system"],
            command=lambda v: ctk.set_appearance_mode(v),
        ).grid(row=6, column=0, padx=PADX, pady=(0, PADY), sticky="ew")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=7, column=0, padx=PADX, pady=PADX, sticky="ew")
        btns.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="Cancel", command=self.destroy,
                      fg_color="transparent", border_width=1, border_color="#444").grid(
            row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkButton(btns, text="Save", command=self._save).grid(
            row=0, column=1, padx=(4, 0), sticky="ew")

    def _save(self) -> None:
        self._cfg.gemini_api_key = self.key_entry.get().strip()
        self._cfg.gemini_model = self.model_var.get()
        self._cfg.appearance_mode = self.appearance_var.get()
        self._on_save()
        self.destroy()
