# src/utils/images_extractor.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple, TYPE_CHECKING
import uuid

import fitz  # PyMuPDF
from PIL import Image

if TYPE_CHECKING:
    from src.gemini_client import GeminiClient  # for type hints only

BBox = Tuple[float, float, float, float]

@dataclass
class ImageArtifact:
    image_id: str
    pdf_path: str
    page: int                 # 1-based
    bbox: Optional[BBox]      # None for embedded images when bbox unknown
    png_path: str
    caption: str
    ocr_text: Optional[str]


# ----- Optional captioner using YOUR GeminiClient (injectable) -----
# Signature: captioner(png_bytes: bytes, *, mime: str) -> str
def caption_with_gemini_client_factory(
    client: "GeminiClient",                          # forward-ref to avoid import cycles
    prompt: str = "Describe this image in 1–2 sentences.",
    model: str = "gemini-2.0-flash",
    **vision_kwargs,
) -> Callable[[bytes], str]:
    """
    Returns a function that accepts image bytes and returns a short caption
    using your GeminiClient.generate_vision().
    """
    def _caption(png_bytes: bytes, *, mime: str = "image/png") -> str:
        try:
            result = client.generate_vision(
                user_prompt=prompt,
                images=[png_bytes],     # bytes OK
                mime=mime,
                model=model,
                **vision_kwargs
            )
            if isinstance(result, str):
                return result.strip()
            if result is None:
                return ""
            return str(result).strip()
        except Exception:
            return ""
    return _caption


def _try_ocr(png_path: Path) -> Optional[str]:
    try:
        import pytesseract
        text = pytesseract.image_to_string(Image.open(png_path))
        return text.strip()[:2000]  # keep small
    except Exception:
        return None


def _mime_from_ext(ext: str) -> str:
    ext = (ext or "").lower().lstrip(".")
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "tif": "image/tiff",
        "tiff": "image/tiff",
        "bmp": "image/bmp",
        "gif": "image/gif",
    }.get(ext, "image/png")


def extract_images(
    pdf_path: str,
    out_dir: str = "artifacts_pdf",
    dpi: int = 144,
    run_ocr: bool = False,
    captioner: Optional[Callable[..., str]] = None,   # uses captioner(img_bytes, mime=...)
    save_fullpage: bool = True,
    extract_embedded: bool = True,
    *,
    num_pages: Optional[int] = None,                  # <-- NEW: take only the first N pages
) -> List[ImageArtifact]:
    """
    MVP image extractor.
    - Renders each page to PNG (full-page figure) for stable citations.
    - Optionally extracts embedded images too (if present).
    - Optionally captions via GeminiClient and runs OCR.
    - If num_pages is provided (>=1), only the first N pages are processed.
    """
    pdf_path_p = Path(pdf_path)
    assert pdf_path_p.exists(), f"PDF not found: {pdf_path}"

    out_base = Path(out_dir) / "figures" / pdf_path_p.stem
    out_base.mkdir(parents=True, exist_ok=True)

    artifacts: List[ImageArtifact] = []

    doc = fitz.open(str(pdf_path_p))
    try:
        total = len(doc)
        limit = total if not num_pages or num_pages <= 0 else min(num_pages, total)

        for pi in range(limit):  # 0-based
            page = doc[pi]
            page_num = pi + 1

            # 1) Full-page render (robust fallback that "sees" charts and vector drawings)
            if save_fullpage:
                m = fitz.Matrix(dpi / 72.0, dpi / 72.0)
                pix = page.get_pixmap(matrix=m, alpha=False)
                image_id = f"fig-p{page_num:04d}-full-{uuid.uuid4().hex[:6]}"
                png_path = out_base / f"{image_id}.png"
                pix.save(str(png_path))

                caption = ""
                if captioner:
                    caption = captioner(Path(png_path).read_bytes(), mime="image/png") or ""
                ocr_text = _try_ocr(png_path) if run_ocr else None

                rect = page.rect  # (x0, y0, x1, y1)
                artifacts.append(ImageArtifact(
                    image_id=image_id,
                    pdf_path=str(pdf_path_p),
                    page=page_num,
                    bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
                    png_path=str(png_path),
                    caption=caption,
                    ocr_text=ocr_text,
                ))

            # 2) Embedded raster images (if any). Note: bbox is not provided by PyMuPDF here.
            if extract_embedded:
                for img_idx, img in enumerate(page.get_images(full=True)):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        ext = base_image.get("ext", "png")
                        image_bytes = base_image["image"]
                        image_id = f"fig-p{page_num:04d}-img{img_idx:02d}-{uuid.uuid4().hex[:6]}"
                        file_path = out_base / f"{image_id}.{ext}"
                        with open(file_path, "wb") as f:
                            f.write(image_bytes)

                        mime = _mime_from_ext(ext)
                        caption = ""
                        if captioner:
                            caption = captioner(image_bytes, mime=mime) or ""
                        ocr_text = _try_ocr(file_path) if run_ocr else None

                        artifacts.append(ImageArtifact(
                            image_id=image_id,
                            pdf_path=str(pdf_path_p),
                            page=page_num,
                            bbox=None,
                            png_path=str(file_path),
                            caption=caption,
                            ocr_text=ocr_text,
                        ))
                    except Exception:
                        continue  # be resilient
    finally:
        doc.close()

    return artifacts