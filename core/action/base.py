"""Base interfaces for the Action Layer.

This module defines the ActionExecutor protocol that all OS-specific
backends must implement.
"""

from typing import Protocol, Optional


class ActionExecutor(Protocol):
    """Protocol defining the required interface for action executors.
    
    Implementations (Windows, macOS) must support these standard actions
    which bridge the gap between Reasoning output and physical OS control.
    """

    def click(self, x: int, y: int) -> None:
        """Move the mouse to absolute coordinates and perform a left click.
        
        Args:
            x: Screen x-coordinate
            y: Screen y-coordinate
        """
        ...

    def click_element(
        self,
        name: str,
        control_type: str,
        automation_id: str = "",
        bbox: Optional[dict[str, int]] = None
    ) -> bool:
        """Perform a click on a semantic UI element directly, ideally without moving the mouse.
        
        Args:
            name: The element's name/label
            control_type: The ControlType enum string (e.g., 'button')
            automation_id: Optional automation ID for exact targeting
            bbox: Optional bounding box dict as a fallback for verification
            
        Returns:
            True if the element was found and invoked, False otherwise.
        """
        ...

    def type_text(self, text: str) -> None:
        """Type text as if it came from the physical keyboard.
        
        Args:
            text: The literal text to type.
        """
        ...

    def press_key(self, key: str) -> None:
        """Press and release a single key (e.g., 'enter', 'tab', 'esc').
        
        Args:
            key: Name of the key to press.
        """
        ...

    def hotkey(self, *keys: str) -> None:
        """Hold down multiple keys in sequence, then release them.
        
        Args:
            keys: The sequence of keys (e.g., 'ctrl', 'c').
        """
        ...
