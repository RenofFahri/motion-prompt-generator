"""Export :class:`PromptResult` batches to plain text and to the CSV formats accepted by
Adobe Stock and Shutterstock contributor portals.

Both marketplaces accept a CSV mapping filename to title, keywords, and category.
The columns differ slightly so we emit two separate files.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from .generator import PromptResult

# Adobe Stock contributor portal accepts: Filename, Title, Keywords, Category, Releases
ADOBE_HEADERS = ["Filename", "Title", "Keywords", "Category", "Releases"]

# Shutterstock contributor portal: Filename, Description, Keywords, Categories, Editorial,
# Mature content, illustration
SHUTTERSTOCK_HEADERS = [
    "Filename",
    "Description",
    "Keywords",
    "Categories",
    "Editorial",
    "Mature content",
    "Illustration",
]


def write_text_batch(path: Path | str, results: Iterable[PromptResult]) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        for i, r in enumerate(results, 1):
            fh.write(f"=== Prompt #{i} ===\n")
            fh.write(r.prompt + "\n\n")
            fh.write("Negative: " + r.negative_prompt + "\n\n")
            fh.write("Title: " + r.metadata.title + "\n")
            fh.write("Description: " + r.metadata.description + "\n")
            fh.write("Category: " + r.metadata.category + "\n")
            fh.write("Keywords: " + r.metadata.keyword_csv() + "\n")
            fh.write("\n")
    return p


def write_adobe_stock_csv(
    path: Path | str,
    results: Iterable[PromptResult],
    *,
    filename_prefix: str = "motion",
) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(ADOBE_HEADERS)
        for i, r in enumerate(results, 1):
            filename = f"{filename_prefix}_{i:03d}.mp4"
            writer.writerow(
                [
                    filename,
                    r.metadata.title,
                    r.metadata.keyword_csv(),
                    r.metadata.category,
                    "",
                ]
            )
    return p


def write_shutterstock_csv(
    path: Path | str,
    results: Iterable[PromptResult],
    *,
    filename_prefix: str = "motion",
) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(SHUTTERSTOCK_HEADERS)
        for i, r in enumerate(results, 1):
            filename = f"{filename_prefix}_{i:03d}.mp4"
            writer.writerow(
                [
                    filename,
                    r.metadata.description,
                    r.metadata.keyword_csv(),
                    r.metadata.category,
                    "no",
                    "no",
                    "no",
                ]
            )
    return p
