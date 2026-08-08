import asyncio
import winrt.windows.media.ocr as ocr
import winrt.windows.graphics.imaging as imaging
import winrt.windows.storage.streams as streams
import io
from PIL import ImageGrab

async def main():
    print("Testing winrt OCR...")
    engine = ocr.OcrEngine.try_create_from_user_profile_languages()
    if not engine:
        print("Failed to create OCR engine")
        return
        
    print("Engine created. Taking screenshot...")
    # Take a screenshot
    img = ImageGrab.grab()
    
    # Save to bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    data = buf.read()
    
    # Convert to WinRT stream
    stream = streams.InMemoryRandomAccessStream()
    data_writer = streams.DataWriter(stream)
    data_writer.write_bytes(list(data))
    await data_writer.store_async()
    stream.seek(0)
    
    # Create SoftwareBitmap
    decoder = await imaging.BitmapDecoder.create_async(stream)
    bitmap = await decoder.get_software_bitmap_async()
    
    print("Recognizing text...")
    result = await engine.recognize_async(bitmap)
    print(f"Recognized {len(result.lines)} lines of text.")
    for line in result.lines[:5]:
        print(line.text)

if __name__ == "__main__":
    asyncio.run(main())
