"""Windows implementation of the ActionExecutor protocol."""

import logging
import time
from typing import Optional

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import uiautomation as auto
except ImportError:
    auto = None

from core.action.base import ActionExecutor

logger = logging.getLogger(__name__)

# Configure PyAutoGUI to be a bit safer and less instant
if pyautogui:
    # Disable fail-safe because in headless environments the mouse may sit at (0, 0)
    pyautogui.FAILSAFE = False
    # Pause slightly after each PyAutoGUI call
    pyautogui.PAUSE = 0.2


class WindowsExecutor:
    """Windows-specific action execution.
    
    Uses PyAutoGUI for raw physical coordinate/keyboard actions (requires focus),
    and UIAutomation for precise background invocations where possible (ADR 11).
    """

    def __init__(self):
        if pyautogui is None:
            raise RuntimeError("pyautogui is not installed. Run: pip install pyautogui")
        if auto is None:
            raise RuntimeError("uiautomation is not installed. Run: pip install uiautomation")
        
        logger.info("WindowsExecutor initialized")

    def click(self, x: int, y: int) -> None:
        """Physical mouse click. Steals focus and moves the real cursor."""
        logger.info("Physical click at (%d, %d)", x, y)
        pyautogui.click(x=x, y=y)

    def click_element(
        self,
        name: str,
        control_type: str,
        automation_id: str = "",
        bbox: Optional[dict[str, int]] = None
    ) -> bool:
        """Attempt to invoke the element via UIA natively, skipping physical mouse movement."""
        logger.info(
            "Attempting native UIA click for element name='%s', control_type='%s', id='%s'",
            name, control_type, automation_id
        )
        
        # We need to map the string control_type back to UIA ControlType if possible,
        # but to keep it fast, we can just do a broad shallow search.
        # This is a heuristic search - the Reasoning Layer gives us the element signature,
        # we re-find the live UIA object and invoke it.
        
        # Determine the root to search from (the active window is usually sufficient)
        root = auto.GetRootControl()
        
        # Build search criteria
        search_params = {"searchDepth": 7} # Reasonable depth to find focused UI quickly
        
        if name:
            search_params["Name"] = name
        if automation_id:
            search_params["AutomationId"] = automation_id
            
        # Add class name mapping if needed, but let's rely on name and ID primarily
        # ControlType mapping could be added here if we reverse map ControlType.BUTTON to auto.ControlType.ButtonControl
        # For simplicity in this early version, we just search by Name and AutomationId
        
        try:
            control = root.Control(**search_params)
            
            # 1 second timeout to find it
            if not control.Exists(1, 0.2):
                logger.warning("Could not find native UIA element to invoke. Falling back to physical click if bbox provided.")
                if bbox:
                    cx = bbox["left"] + (bbox["width"] // 2)
                    cy = bbox["top"] + (bbox["height"] // 2)
                    self.click(cx, cy)
                    return True
                return False
                
            # Element found! Try InvokePattern (buttons, links)
            pattern = control.GetInvokePattern()
            if pattern:
                logger.info("Triggering native InvokePattern")
                pattern.Invoke()
                return True
                
            # Fallback to SelectionItemPattern for list/tree/tab items
            sel_pattern = control.GetSelectionItemPattern()
            if sel_pattern:
                logger.info("Triggering native SelectionItemPattern.Select()")
                sel_pattern.Select()
                return True
                
            # Fallback to physical click on the control's bounding rect
            logger.info("No supported invoke pattern found. Falling back to UIA native Click()")
            control.Click(simulateMove=False)
            return True
            
        except Exception as e:
            logger.error("Error during native element click: %s", e)
            if bbox:
                logger.info("Falling back to coordinate physical click")
                cx = bbox["left"] + (bbox["width"] // 2)
                cy = bbox["top"] + (bbox["height"] // 2)
                self.click(cx, cy)
                return True
            return False

    def type_text(self, text: str) -> None:
        """Physical keyboard typing."""
        logger.info("Typing text (len=%d)", len(text))
        # Add a tiny delay between keystrokes to ensure OS registers them
        pyautogui.write(text, interval=0.01)

    def press_key(self, key: str) -> None:
        """Physical single key press."""
        logger.info("Pressing key: '%s'", key)
        pyautogui.press(key)

    def hotkey(self, *keys: str) -> None:
        """Physical hotkey sequence."""
        logger.info("Pressing hotkey: %s", keys)
        pyautogui.hotkey(*keys)
