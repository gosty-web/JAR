"""Platform-agnostic screen reader facade.

This module provides the public API that the rest of JAR uses to perceive
the screen. It automatically selects the correct OS-specific implementation
(Windows UIAutomation or macOS AX API) and presents a unified interface.

All other subsystems (reasoning, action, world-state) import ScreenReader
from this module - they never import the OS-specific readers directly.
This is the module boundary described in ARCHITECTURE.md and PROJECT_STRUCTURE.md.

Usage:
    from core.perception import ScreenReader

    reader = ScreenReader()
    state = reader.read_focused_window()
    interactive = state.find_interactive()
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from core.perception.models import ScreenState

logger = logging.getLogger(__name__)


class ScreenReader:
    """Unified screen perception interface.

    Automatically selects the correct OS backend and provides a single
    API surface for reading accessibility trees, listing windows, and
    reading specific windows by title.

    This is the only class other subsystems should instantiate for
    perception. It handles platform detection, initialization errors,
    and fallback logging.
    """

    def __init__(self) -> None:
        """Initialize the screen reader with the appropriate OS backend.

        Raises:
            RuntimeError: If the current platform is not supported.
        """
        self._platform = sys.platform
        self._initialized = False

        if self._platform == "win32":
            try:
                from core.perception.windows_reader import (
                    list_open_windows as _list_windows,
                    read_focused_window as _read_focused,
                    read_window_by_title as _read_by_title,
                )
                self._read_focused = _read_focused
                self._read_by_title = _read_by_title
                self._list_windows = _list_windows
                self._initialized = True
                logger.info("ScreenReader initialized with Windows UIAutomation backend")
            except ImportError as e:
                raise RuntimeError(
                    f"Failed to import Windows UIAutomation backend: {e}. "
                    "Install with: pip install uiautomation"
                ) from e

        elif self._platform == "darwin":
            # macOS AX API implementation - not yet built.
            # Will be implemented when macOS support is added.
            raise RuntimeError(
                "macOS AX API backend is not yet implemented. "
                "See ROADMAP.md - this is tracked for future work."
            )
        else:
            raise RuntimeError(
                f"Unsupported platform: {self._platform}. "
                "JAR currently supports Windows and macOS."
            )

    def read_focused_window(self) -> ScreenState:
        """Read the accessibility tree of the currently focused window.

        This is the primary perception method used by the verification-gated
        action loop (ARCHITECTURE.md §5). It's called:
        - Before planning an action (to see current state)
        - After executing an action (to verify the result)

        Returns:
            ScreenState with all elements in the focused window.
        """
        return self._read_focused()

    def read_window(self, title: str, partial: bool = True) -> ScreenState:
        """Read the accessibility tree of a specific window by title.

        Enables background execution (ADR 9): JAR can read a window's state
        without it being focused, so the user's active window isn't disturbed.

        Args:
            title: Window title to search for.
            partial: If True, match windows containing the search string.

        Returns:
            ScreenState for the matching window, or empty if not found.
        """
        return self._read_by_title(title, partial=partial)

    def list_windows(self) -> list[dict[str, str]]:
        """List all open top-level windows.

        Used by the World-State Tracker to maintain an awareness of running
        applications, and by the "take over" handoff feature.

        Returns:
            List of window info dicts with 'title' and 'class_name' keys.
        """
        return self._list_windows()

    def read_or_fallback(
        self,
        title: Optional[str] = None,
    ) -> ScreenState:
        """Read screen state, falling back to vision if tree is empty.

        This implements the perception strategy from ARCHITECTURE.md §1:
        try the accessibility tree first (cheap, fast), fall back to
        vision/OCR only if the tree is empty or useless.

        Args:
            title: If provided, read this specific window. Otherwise read focused.

        Returns:
            ScreenState from accessibility tree or vision fallback.
        """
        if title:
            state = self.read_window(title)
        else:
            state = self.read_focused_window()

        # Check if we got useful data
        if state.element_count == 0 or state.source == "accessibility_tree_error":
            logger.warning(
                "Accessibility tree returned %d elements (source: %s). "
                "Triggering Vision/OCR fallback.",
                state.element_count,
                state.source,
            )
            try:
                from core.perception.vision_reader import read_screen_vision
                return read_screen_vision()
            except Exception as e:
                logger.error("Failed to load or execute vision fallback: %s", e)
                state.source = "accessibility_tree_empty_vision_failed"

        return state
