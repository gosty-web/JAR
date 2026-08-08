"""Platform-agnostic action executor facade.

This module provides the public API that the rest of JAR uses to perform actions.
It automatically selects the correct OS-specific implementation and presents a unified interface.

Usage:
    from core.action import ActionService

    action = ActionService()
    action.click_element(name="Submit", control_type="button")
"""

import logging
import sys

from core.action.base import ActionExecutor
from core.action.browser import BrowserAutomation

logger = logging.getLogger(__name__)


class ActionService(ActionExecutor):
    """Unified action execution interface.
    
    Automatically selects the correct OS backend and routes method calls
    to that implementation. Also exposes the browser automation module.
    """

    def __init__(self, headless_browser: bool = False) -> None:
        """Initialize the action service with the appropriate OS backend.
        
        Args:
            headless_browser: Whether to run the Playwright browser in headless mode.
                              Defaults to False per user request to allow login/visibility.
        """
        self._platform = sys.platform
        self._backend: ActionExecutor
        
        # Initialize browser automation module
        self.browser = BrowserAutomation(headless=headless_browser)

        if self._platform == "win32":
            try:
                from core.action.windows_executor import WindowsExecutor
                self._backend = WindowsExecutor()
                logger.info("ActionService initialized with WindowsExecutor backend")
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Windows action backend: {e}") from e

        elif self._platform == "darwin":
            # macOS AX API implementation - not yet built.
            raise RuntimeError(
                "macOS action backend is not yet implemented. "
                "See ROADMAP.md - this is tracked for future work."
            )
        else:
            raise RuntimeError(
                f"Unsupported platform: {self._platform}. "
                "JAR currently supports Windows and macOS."
            )

    def click(self, x: int, y: int) -> None:
        self._backend.click(x, y)

    def click_element(self, name: str, control_type: str, automation_id: str = "", bbox: dict[str, int] = None) -> bool:
        return self._backend.click_element(name, control_type, automation_id, bbox)

    def type_text(self, text: str) -> None:
        self._backend.type_text(text)

    def press_key(self, key: str) -> None:
        """Simulate pressing a specific keyboard key.
        
        Args:
            key: The key name (e.g., 'enter', 'esc', 'tab').
        """
        logger.info(f"Pressing key: {key}")
        self._backend.press_key(key)

    def hotkey(self, *keys: str) -> None:
        self._backend.hotkey(*keys)

    def write_file(self, filename: str, content: str) -> None:
        """Write content to a file.
        
        Added for the end-to-end summarize screen skill.
        
        Args:
            filename: The destination file path.
            content: The text content to write.
        """
        import os
        # Ensure it saves relative to desktop for visibility if just a basename is given
        if not os.path.isabs(filename):
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, filename)
        else:
            filepath = filename
            
        logger.info(f"Writing file to {filepath}")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to write file {filepath}: {e}")
            raise
