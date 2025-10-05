# src/utils/tables_extractor.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple
import csv
import json
import uuid

import pdfplumber

BBox = Tuple[float, float, float, float]

@dataclass
class TableArtifact:
    table_id: str
    pdf_path: str
    page: int                 # 1-based
    bbox: Optional[BBox]      # (x0, y0, x1, y1) in PDF points, if available
    title: Optional[str]      # best-effort title guess, None for MVP
    headers: List[str]
    rows: List[List[str]]     # full table rows
    row_count: int
    csv_path: str             # saved CSV file
    json_path: str            # saved JSON summary
    preview_text: str         # what you will embed/index in Chroma


def _clean_cell(x):
    if x is None:
        return ""
    x = str(x).strip()
    return x


def _make_preview_text(title: Optional[str], headers: List[str], rows: List[List[str]]) -> str:
    r1 = rows[0] if rows else []
    r2 = rows[1] if len(rows) > 1 else []
    title_txt = f"Table: {title}." if title else "Table."
    return (
        f"{title_txt} Headers: " + " | ".join(headers) +
        (f". Example rows: " + " | ".join(r1) if r1 else "") +
        (f" ; " + " | ".join(r2) if r2 else "")
    )


def extract_tables(
    pdf_path: str,
    out_dir: str = "artifacts_pdf",
    *,
    num_pages: Optional[int] = None,     # <-- NEW: if 3, take the first 3 pages only
) -> List[TableArtifact]:
    """
    MVP table extractor using pdfplumber. Returns TableArtifact list and writes CSV+JSON artifacts.

    Args:
        pdf_path: path to the PDF
        out_dir: base directory for artifacts
        num_pages: if provided and >=1, only the first N pages are processed (1..N)
    """
    pdf_path_p = Path(pdf_path)
    assert pdf_path_p.exists(), f"PDF not found: {pdf_path}"

    out_base = Path(out_dir) / "tables" / pdf_path_p.stem
    out_base.mkdir(parents=True, exist_ok=True)

    artifacts: List[TableArtifact] = []

    with pdfplumber.open(str(pdf_path_p)) as pdf:
        total = len(pdf.pages)
        limit = total if not num_pages or num_pages <= 0 else min(num_pages, total)

        for pi in range(limit):   # 0-based index of the first N pages
            page_num = pi + 1
            page = pdf.pages[pi]

            # Two simple strategies: "lines" (ruled tables) then "text" (whitespace)
            strategies = [
                {"vertical_strategy": "lines", "horizontal_strategy": "lines", "explicit_vertical_lines": None},
                {"vertical_strategy": "text", "horizontal_strategy": "text"},
            ]

            found_any = False
            for settings in strategies:
                try:
                    tables = page.find_tables(table_settings=settings)  # returns Table objects
                except Exception:
                    tables = []

                if not tables:
                    continue

                for t_idx, t in enumerate(tables):
                    try:
                        rows = [[_clean_cell(c) for c in row] for row in t.extract()]
                        if not rows:
                            continue

                        # Heuristic: first row as headers, remaining as data
                        headers = [h for h in rows[0]]
                        data_rows = rows[1:] if len(rows) > 1 else []

                        table_id = f"tbl-{page_num:04d}-{t_idx:02d}-{uuid.uuid4().hex[:6]}"
                        csv_path = out_base / f"{table_id}.csv"
                        json_path = out_base / f"{table_id}.json"

                        # Save CSV (headers + data)
                        with open(csv_path, "w", newline="", encoding="utf-8") as f:
                            w = csv.writer(f)
                            if headers:
                                w.writerow(headers)
                            for r in data_rows:
                                w.writerow(r)

                        # Build preview text for embedding
                        preview_text = _make_preview_text(None, headers, data_rows[:2])

                        art = TableArtifact(
                            table_id=table_id,
                            pdf_path=str(pdf_path_p),
                            page=page_num,
                            bbox=tuple(t.bbox) if getattr(t, "bbox", None) else None,
                            title=None,
                            headers=headers,
                            rows=data_rows,
                            row_count=len(data_rows),
                            csv_path=str(csv_path),
                            json_path=str(json_path),
                            preview_text=preview_text,
                        )

                        # Save JSON sidecar (metadata + first few rows to keep it small)
                        with open(json_path, "w", encoding="utf-8") as jf:
                            json.dump({
                                **asdict(art),
                                "rows": data_rows[:10],
                            }, jf, ensure_ascii=False, indent=2)

                        artifacts.append(art)
                        found_any = True
                    except Exception:
                        # swallow table-level errors; keep going
                        continue

                if found_any:
                    break  # don't run next strategy if this one already found tables

    return artifacts