from __future__ import annotations
from typing import Any, Dict, Optional, List, Union
from pathlib import Path
import base64
from pydantic import BaseModel, ValidationError
from langchain_google_genai import ChatGoogleGenerativeAI

ImageLike = Union[str, bytes, Path]  # file path, bytes, or Path

class GeminiClient:
    def __init__(self, api_key: str, system_prompt: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=200,
        )

    # ---------- helpers ----------
    @staticmethod
    def _to_image_block(img: ImageLike, mime: str = "image/png") -> Dict[str, Any]:
        """Return a LangChain cross-provider image content block."""
        if isinstance(img, (str, Path)):
            data = Path(img).read_bytes()
        else:
            data = img
        b64 = base64.b64encode(data).decode("utf-8")
        return {"type": "image", "source_type": "base64", "mime_type": mime, "data": b64}

    # ---------- text-only (as you had) ----------
    def generate(
        self,
        user_prompt: str,
        response_schema: Optional[BaseModel] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any] | str]:
        llm = self.llm.bind(**kwargs) if kwargs else self.llm
        try:
            messages = [("system", self.system_prompt), ("user", user_prompt)]
            resp = llm.invoke(messages)
            if response_schema:
                try:
                    parsed = response_schema.model_validate_json(resp.content)
                    return parsed.model_dump()
                except ValidationError as e:
                    print(f"[GeminiClient] Schema validation failed: {e}")
                    return resp.content
            return resp.content
        except Exception as e:
            print(f"[GeminiClient] Generation failed: {e}")
            return None

    # ---------- new: vision (images) ----------
    def generate_vision(
        self,
        user_prompt: str,
        images: List[ImageLike],
        *,
        mime: str = "image/png",
        response_schema: Optional[BaseModel] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any] | str]:
        """
        Send text + 1..N images to a Gemini *vision-capable* model (e.g., gemini-2.0-flash).
        """
        llm = self.llm.bind(**kwargs) if kwargs else self.llm
        try:
            content_blocks = [{"type": "text", "text": user_prompt}]
            content_blocks += [self._to_image_block(img, mime=mime) for img in images]

            # one system + one user (human) message with multimodal content
            messages = [
                ("system", self.system_prompt),
                {"role": "user", "content": content_blocks},
            ]

            # If you want automatic structured parsing, prefer with_structured_output:
            if response_schema is not None:
                llm_struct = llm.with_structured_output(response_schema.__class__)
                resp = llm_struct.invoke(messages)  # returns a parsed pydantic instance
                return resp.dict()

            # Otherwise get free-form text
            resp = llm.invoke(messages)
            if response_schema:
                # fallback manual parse when model returns JSON text
                try:
                    parsed = response_schema.model_validate_json(resp.content)
                    return parsed.model_dump()
                except ValidationError as e:
                    print(f"[GeminiClient] Vision schema validation failed: {e}")
                    return resp.content

            return resp.content
        except Exception as e:
            print(f"[GeminiClient] Vision call failed: {e}")
            return None