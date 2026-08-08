"""Test script for the Vision/OCR fallback layer.

This verifies that the winrt OCR engine can parse text from an image
and convert it to UIElements.
"""
import sys
import logging
import json

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, ".")

from core.perception.vision_reader import read_screen_vision

def main():
    print("=" * 60)
    print("JAR Perception Layer - Vision/OCR Test")
    print("=" * 60)
    
    # We use an existing image so this can run headlessly.
    # Replace with any image containing text.
    image_path = "WhatsApp Image 2026-08-07 at 19.17.10.jpeg"
    
    try:
        print(f"Reading from image: {image_path}")
        state = read_screen_vision(image_path)
    except Exception as e:
        print(f"[FAIL] Vision reader raised an exception: {e}")
        sys.exit(1)
        
    print(f"\n[OK] Found {state.element_count} OCR elements.")
    print(f"Source is: {state.source}")
    
    if state.element_count > 0:
        print("\nFirst 10 elements:")
        for elem in state.elements[:10]:
            print(f"  [{elem.element_id}] '{elem.name}' at {elem.bbox.left}, {elem.bbox.top}")
            
        print("\nCompact JSON preview:")
        print(json.dumps(state.to_compact_dict(), indent=2))
        print("\nRESULT: [PASS]")
    else:
        print("RESULT: [FAIL] - No elements found. Did the image contain text?")

if __name__ == "__main__":
    main()
