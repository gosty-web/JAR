"""Live integration test for the Windows UIAutomation perception layer.

This script verifies that the ScreenReader can actually read the Windows
accessibility tree. It is NOT a pytest unit test because it requires:
1. Running on Windows
2. Running with Administrator privileges (for full UIA access)
3. Having at least one visible window open

Run manually: python tests/perception/test_live_windows.py
Expected output: A JSON dump of the current screen state, including
element counts, the active window title, and interactive elements.
"""

import json
import logging
import sys

# Configure logging so we can see the perception layer's debug output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# Add project root to path for imports
sys.path.insert(0, ".")

from core.perception import ScreenReader


def main() -> None:
    print("=" * 60)
    print("JAR Perception Layer - Live Windows Test")
    print("=" * 60)

    # 1. Initialize the screen reader
    print("\n[1/4] Initializing ScreenReader...")
    try:
        reader = ScreenReader()
        print("  [OK] ScreenReader initialized successfully")
    except RuntimeError as e:
        print(f"  [FAIL] Failed to initialize: {e}")
        sys.exit(1)

    # 2. Read the focused window
    print("[2/4] Reading focused window accessibility tree (with vision fallback)...")
    state = reader.read_or_fallback()
    print(f"  [OK] Active window: '{state.active_window_title}'")
    print(f"  [OK] Process: '{state.active_window_process}'")
    print(f"  [OK] Total elements: {state.element_count}")
    print(f"  [OK] Source: {state.source}")

    if state.element_count == 0:
        print("  [WARN] WARNING: No elements found. This may indicate:")
        print("    - No window is focused")
        print("    - The focused app doesn't expose accessibility data")
        print("    - UAC elevation is needed")

    # 3. List interactive elements
    print("\n[3/4] Interactive elements found:")
    interactive = state.find_interactive()
    print(f"  Found {len(interactive)} interactive elements")
    for i, elem in enumerate(interactive[:15]):  # Show first 15
        bbox_str = ""
        if elem.bbox:
            bbox_str = f" @ ({elem.bbox.center_x}, {elem.bbox.center_y})"
        print(f"  [{elem.element_id}] {elem.control_type.value}: '{elem.display_text}'{bbox_str}")
    if len(interactive) > 15:
        print(f"  ... and {len(interactive) - 15} more")

    # 4. List open windows
    print("\n[4/4] Open windows:")
    windows = reader.list_windows()
    for w in windows[:10]:
        print(f"  - {w['title']} ({w['class_name']})")
    if len(windows) > 10:
        print(f"  ... and {len(windows) - 10} more")

    # 5. Output compact JSON for LLM context preview
    print("\n" + "=" * 60)
    print("Compact JSON (what the LLM sees):")
    print("=" * 60)
    compact = state.to_compact_dict()
    print(json.dumps(compact, indent=2, ensure_ascii=True)[:2000])

    # Summary
    print("\n" + "=" * 60)
    success = state.element_count > 0 and len(interactive) > 0
    if success:
        print("RESULT: [PASS] - Perception layer reads screen state correctly")
    else:
        print("RESULT: [PARTIAL] - Tree reads but no interactive elements found")
        print("  (This may be normal if the focused window is a simple app)")
    print("=" * 60)


if __name__ == "__main__":
    main()
