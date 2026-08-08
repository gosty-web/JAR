"""Windows native OCR fallback for the Perception Layer.

This module provides the Vision/OCR fallback for when the accessibility tree
is empty or incomplete (DECISIONS.md ADR 2). It uses the built-in Windows
10/11 OCR API via the `winrt` package, avoiding the need for heavy external
dependencies like Tesseract or slow cloud vision APIs.

Requirements:
    pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage.Streams pillow
"""

import asyncio
import io
import logging
import time
from typing import Optional

from core.perception.models import BoundingBox, ControlType, ScreenState, UIElement

logger = logging.getLogger(__name__)

# Lazy imports for Windows-only modules
_ocr = None
_imaging = None
_streams = None

def _init_winrt() -> None:
    global _ocr, _imaging, _streams
    if _ocr is None:
        try:
            import winrt.windows.media.ocr as ocr
            import winrt.windows.graphics.imaging as imaging
            import winrt.windows.storage.streams as streams
            _ocr = ocr
            _imaging = imaging
            _streams = streams
        except ImportError as e:
            raise RuntimeError(
                "WinRT OCR modules not installed. "
                "Run: pip install winrt-Windows.Media.Ocr winrt-Windows.Graphics.Imaging winrt-Windows.Storage.Streams"
            ) from e


async def _recognize_image(image_bytes: bytes) -> tuple[list[UIElement], int, int]:
    """Run Windows native OCR on image bytes and return UIElements."""
    _init_winrt()
    
    # Needs to run in an async context because WinRT APIs are async
    engine = _ocr.OcrEngine.try_create_from_user_profile_languages()
    if not engine:
        raise RuntimeError("Failed to create WinRT OCR engine. Ensure Windows language pack is installed.")

    # Convert Python bytes to WinRT IRandomAccessStream
    stream = _streams.InMemoryRandomAccessStream()
    data_writer = _streams.DataWriter(stream)
    data_writer.write_bytes(image_bytes)
    await data_writer.store_async()
    stream.seek(0)
    
    # Decode the image stream into a SoftwareBitmap
    decoder = await _imaging.BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    
    img_width = bitmap.pixel_width
    img_height = bitmap.pixel_height

    # Run OCR
    result = await engine.recognize_async(bitmap)
    
    elements: list[UIElement] = []
    element_id_counter = 1
    
    # Convert OCR lines/words to UIElements
    if result and result.lines:
        for line in result.lines:
            text = line.text.strip()
            if not text:
                continue
                
            # Line bounding box from words
            left = min([int(w.bounding_rect.x) for w in line.words])
            top = min([int(w.bounding_rect.y) for w in line.words])
            right = max([int(w.bounding_rect.x + w.bounding_rect.width) for w in line.words])
            bottom = max([int(w.bounding_rect.y + w.bounding_rect.height) for w in line.words])
            
            bbox = BoundingBox(left=left, top=top, width=right-left, height=bottom-top)
            
            # Treat OCR text chunks as text elements. The LLM or reasoning layer 
            # will infer if they are buttons or inputs based on context and surrounding elements.
            element = UIElement(
                element_id=element_id_counter,
                control_type=ControlType.TEXT,
                name=text,
                value=text,
                bbox=bbox,
                is_enabled=True,
                properties={"source": "vision_ocr"}
            )
            elements.append(element)
            element_id_counter += 1
            
    return elements, img_width, img_height


def read_screen_vision(image_path: Optional[str] = None) -> ScreenState:
    """Read screen state using Vision/OCR.
    
    Args:
        image_path: If provided, read from this image file instead of taking a screenshot.
                    Useful for testing in headless environments.
                    
    Returns:
        ScreenState populated with OCR elements.
    """
    start_time = time.time()
    
    try:
        if image_path:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
        else:
            from PIL import ImageGrab
            try:
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                image_bytes = buf.getvalue()
            except OSError as e:
                logger.error("Failed to grab screen (headless environment?): %s", e)
                return ScreenState(
                    timestamp=time.time(),
                    source="vision_fallback_error",
                )
                
        # Run async OCR synchronously (we are in a synchronous function)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            elements, w, h = loop.run_until_complete(_recognize_image(image_bytes))
        finally:
            loop.close()
            
        elapsed = time.time() - start_time
        logger.info(
            "Vision/OCR found %d text blocks in %.0fms",
            len(elements),
            elapsed * 1000,
        )
        
        return ScreenState(
            timestamp=time.time(),
            elements=elements,
            element_count=len(elements),
            source="vision_ocr",
        )
        
    except Exception as e:
        logger.error("Vision/OCR fallback failed: %s", e, exc_info=True)
        return ScreenState(
            timestamp=time.time(),
            source="vision_fallback_error",
        )
