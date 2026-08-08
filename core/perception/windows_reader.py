"""Windows UIAutomation accessibility tree reader.

This module wraps the `uiautomation` library (yinkaisheng/Python-UIAutomation-for-Windows)
to extract structured screen state from Windows applications.

Why UIAutomation over Vision (DECISIONS.md ADR 2):
    UIAutomation provides a semantic DOM of the OS for free - no GPU, no API calls,
    no token cost. It returns exact element types, labels, bounding boxes, and
    states in milliseconds. Vision models are 100-1000x more expensive and slower.
    We only fall back to vision when the accessibility tree is empty or incomplete.

Performance considerations:
    - Walking the ENTIRE accessibility tree from root (Desktop) is extremely expensive
      (~5-15 seconds for a busy desktop). We NEVER do this.
    - Instead, we read only the focused window's subtree, which is fast (~50-200ms).
    - For background execution (ADR 9), we can read a specific window by handle
      without needing it to be focused.
    - Element count is capped (MAX_ELEMENTS) to prevent runaway tree walks in
      applications with deeply nested or dynamically generated UI trees.

Platform: Windows only. macOS uses core.perception.macos_reader (not yet implemented).

Library docs: https://github.com/yinkaisheng/Python-UIAutomation-for-Windows
Requires: pip install uiautomation (v2.0.29+)
Must run with Administrator privileges for full element access.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Optional

from core.perception.models import BoundingBox, ControlType, ScreenState, UIElement

logger = logging.getLogger(__name__)

# Guard: only import Windows-specific modules on Windows
if sys.platform == "win32":
    import uiautomation as auto
    import ctypes
    import win32gui
    import win32process
else:
    auto = None  # type: ignore[assignment]
    win32gui = None  # type: ignore[assignment]
    win32process = None  # type: ignore[assignment]

# Safety cap: stop reading after this many elements to prevent runaway walks
# in apps with massive trees (e.g., VS Code with many open tabs, large tables).
MAX_ELEMENTS = 500

# Maximum depth to recurse into children. Most useful interactive elements
# are within 8-10 levels. Going deeper usually means we're inside a data grid
# or tree view where individual cells aren't useful action targets.
MAX_DEPTH = 12

# Maps Windows UIAutomation ControlType IDs to our standardized ControlType enum.
# IDs from: https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-controltype-ids
# The uiautomation library exposes these as integer constants.
_UIA_CONTROL_TYPE_MAP: dict[int, ControlType] = {
    50000: ControlType.BUTTON,
    50001: ControlType.BUTTON,   # Calendar -> treat as interactive
    50002: ControlType.CHECKBOX,
    50003: ControlType.COMBOBOX,
    50004: ControlType.EDIT,
    50005: ControlType.HYPERLINK,
    50006: ControlType.IMAGE,
    50007: ControlType.LIST_ITEM,
    50008: ControlType.LIST,
    50009: ControlType.MENU,
    50010: ControlType.MENU_ITEM, # MenuBar
    50011: ControlType.MENU_ITEM,
    50012: ControlType.PROGRESS_BAR,
    50013: ControlType.RADIO_BUTTON,
    50014: ControlType.SCROLL_BAR,
    50015: ControlType.SLIDER,
    50016: ControlType.SPINNER,
    50017: ControlType.STATUS_BAR,
    50018: ControlType.TAB,
    50019: ControlType.TAB_ITEM,
    50020: ControlType.TEXT,
    50021: ControlType.TOOLBAR,
    50022: ControlType.CUSTOM,    # ToolTip
    50023: ControlType.TREE,
    50024: ControlType.TREE_ITEM,
    50025: ControlType.CUSTOM,
    50026: ControlType.GROUP,
    50027: ControlType.HEADER,
    50028: ControlType.HEADER,    # HeaderItem
    50029: ControlType.TABLE,
    50030: ControlType.TITLE_BAR,
    50031: ControlType.CUSTOM,    # Thumb
    50032: ControlType.WINDOW,
    50033: ControlType.PANE,
    50034: ControlType.GROUP,     # Group
    50035: ControlType.DOCUMENT,  # Document (added for web content)
    50036: ControlType.PANE,      # SplitButton
    50037: ControlType.TABLE_ITEM,  # DataItem
    50038: ControlType.TABLE,     # DataGrid
}


def _map_control_type(uia_type_id: int) -> ControlType:
    """Convert a Windows UIAutomation ControlType ID to our standardized enum.

    Falls back to UNKNOWN for unrecognized types rather than crashing,
    since new ControlTypes can be added by Windows updates.
    """
    return _UIA_CONTROL_TYPE_MAP.get(uia_type_id, ControlType.UNKNOWN)


def _read_element(
    uia_control: auto.Control,  # type: ignore[name-defined]
    element_counter: list[int],
    depth: int = 0,
) -> Optional[UIElement]:
    """Convert a single UIAutomation Control into a UIElement.

    This is the core conversion function. It reads properties from the
    Windows accessibility API and maps them to our OS-agnostic model.

    Args:
        uia_control: The UIAutomation Control object to read.
        element_counter: Mutable list holding [count] - used to enforce
            MAX_ELEMENTS across the entire tree walk. Using a list so
            the counter is shared across recursive calls.
        depth: Current recursion depth.

    Returns:
        A UIElement, or None if the element should be skipped (offscreen,
        over element cap, or unreadable).
    """
    # Enforce element cap to prevent runaway tree walks
    if element_counter[0] >= MAX_ELEMENTS:
        return None
    if depth > MAX_DEPTH:
        return None

    element_counter[0] += 1
    current_id = element_counter[0]

    try:
        # Read core properties. Each of these is a COM call to the UIA provider,
        # so we wrap in try/except because some elements may be destroyed between
        # enumeration and property access (race condition with live UI).
        name = uia_control.Name or ""
        control_type_id = uia_control.ControlType
        class_name = uia_control.ClassName or ""
        automation_id = uia_control.AutomationId or ""
        is_enabled = uia_control.IsEnabled

        # Bounding rectangle: returns (left, top, right, bottom)
        rect = uia_control.BoundingRectangle
        bbox = None
        is_offscreen = False

        if rect and rect != (0, 0, 0, 0):
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            # Skip zero-size elements (hidden/collapsed)
            if width > 0 and height > 0:
                bbox = BoundingBox(
                    left=int(left),
                    top=int(top),
                    width=int(width),
                    height=int(height),
                )
            else:
                is_offscreen = True
        else:
            is_offscreen = True

        # Read current value (for text inputs, checkboxes, etc.)
        # Not all elements have values, so we handle gracefully.
        value = ""
        try:
            # ValuePattern is the most common way to get text from edit controls
            value_pattern = uia_control.GetValuePattern()
            if value_pattern:
                value = value_pattern.Value or ""
        except Exception:
            pass

        # Check if this element has keyboard focus
        is_focused = False
        try:
            is_focused = uia_control.HasKeyboardFocus
        except Exception:
            pass

        # Map the control type
        control_type = _map_control_type(control_type_id)

        element = UIElement(
            element_id=current_id,
            control_type=control_type,
            name=name,
            value=value,
            bbox=bbox,
            is_enabled=is_enabled,
            is_focused=is_focused,
            is_offscreen=is_offscreen,
            automation_id=automation_id,
            class_name=class_name,
            raw_control_type=control_type_id,
        )

        # Recurse into children
        if depth < MAX_DEPTH and element_counter[0] < MAX_ELEMENTS:
            try:
                children_controls = uia_control.GetChildren()
                if children_controls:
                    for child_control in children_controls:
                        child = _read_element(
                            child_control,
                            element_counter,
                            depth + 1,
                        )
                        if child is not None:
                            element.children.append(child)
            except Exception as e:
                # Some elements refuse to enumerate children (permission issues,
                # destroyed windows, etc.). Log and continue rather than crashing.
                logger.debug(
                    "Could not read children of element '%s': %s",
                    name,
                    e,
                )

        return element

    except Exception as e:
        # Element may have been destroyed between enumeration and read.
        # This is a normal race condition with live UIs, not a bug.
        logger.debug("Failed to read UIA element: %s", e)
        return None


def read_focused_window() -> ScreenState:
    """Read the accessibility tree of the currently focused window.

    This is the primary perception method. It reads ONLY the focused window's
    tree (not the entire desktop), which keeps it fast (~50-200ms).

    Implementation note: We use win32gui.GetForegroundWindow() to reliably
    get the foreground window handle, then convert it to a UIA control.
    The previous approach (auto.GetFocusedControl() + parent walk) was
    unreliable because GetFocusedControl returns the focused *element*
    inside a window (e.g., a button), and walking up sometimes overshoots
    to the Desktop. Using the Win32 API directly is the standard approach
    per Microsoft documentation.

    Returns:
        ScreenState containing all elements in the focused window.

    Raises:
        RuntimeError: If UIAutomation is not available (non-Windows platform).
    """
    if auto is None:
        raise RuntimeError(
            "UIAutomation is only available on Windows. "
            "macOS support requires core.perception.macos_reader."
        )

    start_time = time.time()

    try:
        # Use Win32 API to reliably get the foreground window handle.
        # This is more reliable than auto.GetFocusedControl() which returns
        # the focused element (button, text field) rather than the window.
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            logger.warning("No foreground window found")
            return ScreenState(
                timestamp=time.time(),
                source="accessibility_tree",
            )

        # Get window title and process name via Win32 for reliability
        window_title = win32gui.GetWindowText(hwnd) or ""
        window_class = win32gui.GetClassName(hwnd) or ""

        # Get process name
        process_name = ""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            import psutil
            proc = psutil.Process(pid)
            process_name = proc.name()
        except Exception:
            # psutil may not be installed; fall back to class name
            process_name = window_class

        # Convert the Win32 handle to a UIAutomation control
        # so we can walk its accessibility tree
        window = auto.ControlFromHandle(hwnd)
        if window is None:
            logger.warning(
                "Could not create UIA control from hwnd %s (window: '%s')",
                hwnd,
                window_title,
            )
            return ScreenState(
                timestamp=time.time(),
                active_window_title=window_title,
                active_window_process=process_name,
                source="accessibility_tree",
            )

        # Walk the tree from this window
        element_counter = [0]
        root_element = _read_element(window, element_counter, depth=0)

        elements = [root_element] if root_element else []
        total_count = element_counter[0]

        elapsed = time.time() - start_time
        logger.info(
            "Read accessibility tree: %d elements in %.0fms (window: '%s')",
            total_count,
            elapsed * 1000,
            window_title,
        )

        return ScreenState(
            timestamp=time.time(),
            active_window_title=window_title,
            active_window_process=process_name,
            elements=elements,
            element_count=total_count,
            source="accessibility_tree",
        )

    except Exception as e:
        logger.error("Failed to read accessibility tree: %s", e, exc_info=True)
        return ScreenState(
            timestamp=time.time(),
            source="accessibility_tree_error",
        )


def read_window_by_title(title: str, partial: bool = True) -> ScreenState:
    """Read the accessibility tree of a window found by title.

    This enables background execution (DECISIONS.md ADR 9): JAR can read
    a specific window's state without that window needing to be focused,
    so the user can keep working in their own window.

    Args:
        title: The window title to search for.
        partial: If True, match windows whose title contains the search string.

    Returns:
        ScreenState for the matching window, or empty ScreenState if not found.
    """
    if auto is None:
        raise RuntimeError("UIAutomation is only available on Windows.")

    start_time = time.time()

    try:
        # Search for the window
        if partial:
            window = auto.WindowControl(
                searchDepth=1,
                SubName=title,
            )
        else:
            window = auto.WindowControl(
                searchDepth=1,
                Name=title,
            )

        if not window.Exists(maxSearchSeconds=2):
            logger.warning("Window not found: '%s'", title)
            return ScreenState(
                timestamp=time.time(),
                source="accessibility_tree",
            )

        # Read the tree
        element_counter = [0]
        root_element = _read_element(window, element_counter, depth=0)
        elements = [root_element] if root_element else []
        total_count = element_counter[0]

        elapsed = time.time() - start_time
        logger.info(
            "Read window '%s': %d elements in %.0fms",
            title,
            total_count,
            elapsed * 1000,
        )

        return ScreenState(
            timestamp=time.time(),
            active_window_title=window.Name or "",
            active_window_process=window.ClassName or "",
            elements=elements,
            element_count=total_count,
            source="accessibility_tree",
        )

    except Exception as e:
        logger.error("Failed to read window '%s': %s", title, e, exc_info=True)
        return ScreenState(
            timestamp=time.time(),
            source="accessibility_tree_error",
        )


def list_open_windows() -> list[dict[str, str]]:
    """List all currently open top-level windows.

    Uses win32gui.EnumWindows for reliable window enumeration rather than
    UIA's GetRootControl().GetChildren(), which can return empty results
    on some Windows configurations.

    Used by the World-State Tracker to maintain awareness of what applications
    are running, and by the "take over" handoff feature to show the user's
    recent window activity.

    Returns:
        List of dicts with 'title', 'class_name', and 'process_id' keys.
    """
    if win32gui is None:
        raise RuntimeError("win32gui is only available on Windows.")

    windows: list[dict[str, str]] = []

    def _enum_callback(hwnd: int, _extra: None) -> bool:
        """Callback for win32gui.EnumWindows - collects visible windows."""
        # Skip invisible windows
        if not win32gui.IsWindowVisible(hwnd):
            return True

        title = win32gui.GetWindowText(hwnd)
        # Skip untitled windows and the desktop shell
        if not title or title == "Program Manager":
            return True

        class_name = win32gui.GetClassName(hwnd)
        pid = ""
        try:
            _, p = win32process.GetWindowThreadProcessId(hwnd)
            pid = str(p)
        except Exception:
            pass

        windows.append({
            "title": title,
            "class_name": class_name,
            "process_id": pid,
        })
        return True

    try:
        win32gui.EnumWindows(_enum_callback, None)
    except Exception as e:
        logger.error("Failed to enumerate windows: %s", e)

    return windows
