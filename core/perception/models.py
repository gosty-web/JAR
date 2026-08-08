"""OS-agnostic data models for the Perception Layer.

These models define the structured representation of screen elements that
the rest of JAR consumes. They are intentionally decoupled from any specific
OS accessibility API so that the Windows (UIAutomation) and macOS (AX API)
implementations can both produce the same output format.

Design rationale (ARCHITECTURE.md §1, DECISIONS.md ADR 2):
    The accessibility tree is JAR's primary perception source. It provides
    cheap, instantaneous, semantic element data (roles, labels, bounding boxes)
    without the cost of vision models. Vision/OCR is fallback only.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class ControlType(enum.Enum):
    """Standardized control types across Windows UIAutomation and macOS AX API.

    These map to the most common interactive elements an agent would need
    to reason about. The raw OS-specific control type ID is preserved in
    UIElement.raw_control_type for cases where finer granularity is needed.
    """

    WINDOW = "window"
    BUTTON = "button"
    TEXT = "text"
    EDIT = "edit"  # Text input field
    CHECKBOX = "checkbox"
    RADIO_BUTTON = "radio_button"
    COMBOBOX = "combobox"
    LIST = "list"
    LIST_ITEM = "list_item"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    TAB = "tab"
    TAB_ITEM = "tab_item"
    TREE = "tree"
    TREE_ITEM = "tree_item"
    TOOLBAR = "toolbar"
    STATUS_BAR = "status_bar"
    SCROLL_BAR = "scroll_bar"
    HYPERLINK = "hyperlink"
    IMAGE = "image"
    DOCUMENT = "document"
    PANE = "pane"
    GROUP = "group"
    SLIDER = "slider"
    SPINNER = "spinner"
    PROGRESS_BAR = "progress_bar"
    TABLE = "table"
    TABLE_ITEM = "table_item"
    HEADER = "header"
    TITLE_BAR = "title_bar"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class BoundingBox:
    """Screen-space bounding box for a UI element.

    All coordinates are in absolute screen pixels (not relative to parent).
    This matches how both UIAutomation and AX API report positions.
    """

    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        """Right edge x-coordinate."""
        return self.left + self.width

    @property
    def bottom(self) -> int:
        """Bottom edge y-coordinate."""
        return self.top + self.height

    @property
    def center_x(self) -> int:
        """Horizontal center - used as click target."""
        return self.left + self.width // 2

    @property
    def center_y(self) -> int:
        """Vertical center - used as click target."""
        return self.top + self.height // 2

    def contains_point(self, x: int, y: int) -> bool:
        """Check if a screen point falls within this bounding box."""
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def to_dict(self) -> dict[str, int]:
        """Serialize for World-State storage and LLM context."""
        return {
            "left": self.left,
            "top": self.top,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class UIElement:
    """A single element from the OS accessibility tree.

    This is the atomic unit of perception in JAR. Every interactive thing
    on screen becomes one of these. The verification-gated action loop
    (ARCHITECTURE.md §5) uses UIElements for both planning actions and
    verifying their results.

    Attributes:
        element_id: Unique identifier for this element within a single snapshot.
            NOT stable across snapshots - elements get new IDs on each read.
            Used for within-snapshot references (e.g., "click element #7").
        control_type: Standardized type (button, text field, etc.)
        name: Human-readable label (e.g., "Submit", "File menu")
        value: Current value if applicable (e.g., text in an edit field)
        bbox: Screen-space bounding box for click targeting
        is_enabled: Whether the element can be interacted with
        is_focused: Whether the element currently has keyboard focus
        is_offscreen: Whether the element is scrolled out of view
        automation_id: The developer-assigned automation ID, if any.
            Useful for stable element targeting across sessions.
        class_name: The OS-level class name (e.g., "Button", "Edit")
        raw_control_type: The raw OS-specific control type integer
        children: Child elements in the tree hierarchy
        properties: Additional OS-specific properties (patterns, states)
    """

    element_id: int
    control_type: ControlType
    name: str = ""
    value: str = ""
    bbox: Optional[BoundingBox] = None
    is_enabled: bool = True
    is_focused: bool = False
    is_offscreen: bool = False
    automation_id: str = ""
    class_name: str = ""
    raw_control_type: int = 0
    children: list[UIElement] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    @property
    def is_interactive(self) -> bool:
        """Whether this element is something the agent could act on.

        Filters out static labels, decorative elements, and disabled controls.
        The action planner uses this to narrow the set of candidate targets.
        """
        interactive_types = {
            ControlType.BUTTON,
            ControlType.EDIT,
            ControlType.CHECKBOX,
            ControlType.RADIO_BUTTON,
            ControlType.COMBOBOX,
            ControlType.HYPERLINK,
            ControlType.LIST_ITEM,
            ControlType.MENU_ITEM,
            ControlType.TAB_ITEM,
            ControlType.TREE_ITEM,
            ControlType.SLIDER,
            ControlType.SPINNER,
        }
        return (self.is_enabled and self.control_type in interactive_types) or self.properties.get("source") == "vision_ocr"

    @property
    def display_text(self) -> str:
        """Best human-readable text representation of this element.

        Prefers name over value, falls back to class_name. Used when
        serializing the tree for LLM context (we want the model to see
        what a human would see as the label).
        """
        return self.name or self.value or self.class_name or "unnamed"

    def to_compact_dict(self) -> dict[str, Any]:
        """Compact serialization for LLM context windows.

        This is deliberately terse - every token in the LLM context costs
        money and attention. We include only what the model needs to decide
        what to click/type next. Full details are available in to_full_dict().

        Design note: This format is what gets injected into the LLM prompt
        as the "current screen state." Keeping it small is critical for
        context window management (ARCHITECTURE.md §4).
        """
        result: dict[str, Any] = {
            "id": self.element_id,
            "type": self.control_type.value,
            "name": self.display_text,
        }
        if self.value and self.value != self.name:
            result["value"] = self.value[:200]  # Truncate long values
        if self.bbox:
            result["bbox"] = self.bbox.to_dict()
        if not self.is_enabled:
            result["disabled"] = True
        if self.is_focused:
            result["focused"] = True
        return result

    def to_full_dict(self) -> dict[str, Any]:
        """Full serialization including children and all properties.

        Used for World-State snapshots and debugging, not for LLM context.
        """
        result = self.to_compact_dict()
        result["automation_id"] = self.automation_id
        result["class_name"] = self.class_name
        result["is_offscreen"] = self.is_offscreen
        if self.children:
            result["children"] = [c.to_full_dict() for c in self.children]
        if self.properties:
            result["properties"] = self.properties
        return result

    def find_by_name(self, name: str, partial: bool = False) -> list[UIElement]:
        """Search this element and all descendants for elements matching a name.

        Args:
            name: The name to search for.
            partial: If True, match elements whose name contains the search
                     string (case-insensitive). If False, exact match only.

        Returns:
            List of matching UIElements (may be empty).
        """
        results: list[UIElement] = []
        if partial:
            if name.lower() in self.name.lower():
                results.append(self)
        else:
            if self.name == name:
                results.append(self)
        for child in self.children:
            results.extend(child.find_by_name(name, partial=partial))
        return results

    def find_by_type(self, control_type: ControlType) -> list[UIElement]:
        """Search this element and all descendants for elements of a given type.

        Args:
            control_type: The ControlType to filter by.

        Returns:
            List of matching UIElements (may be empty).
        """
        results: list[UIElement] = []
        if self.control_type == control_type:
            results.append(self)
        for child in self.children:
            results.extend(child.find_by_type(control_type))
        return results

    def find_interactive(self) -> list[UIElement]:
        """Return all interactive descendants (buttons, inputs, links, etc.).

        This is the primary method the action planner uses to enumerate
        "what can I click/type on right now?"
        """
        results: list[UIElement] = []
        if self.is_interactive:
            results.append(self)
        for child in self.children:
            results.extend(child.find_interactive())
        return results

    def flatten(self) -> list[UIElement]:
        """Flatten the tree into a list, depth-first.

        Useful for assigning sequential element_ids or for iterating
        without recursion.
        """
        result: list[UIElement] = [self]
        for child in self.children:
            result.extend(child.flatten())
        return result


@dataclass
class ScreenState:
    """A complete snapshot of the current screen state.

    This is what the Perception Layer produces and what the Reasoning Layer
    consumes. It represents "what is true on screen right now" at a point
    in time.

    The World-State Tracker (ARCHITECTURE.md §4) stores these snapshots
    to enable before/after comparison in the verification-gated action loop.

    Attributes:
        timestamp: When this snapshot was taken (epoch seconds).
        active_window_title: Title of the currently focused window.
        active_window_process: Process name of the focused window.
        elements: The root-level UI elements (typically top-level windows).
        element_count: Total number of elements in the tree (including nested).
        source: How this state was obtained ("accessibility_tree" or "vision_fallback").
    """

    timestamp: float
    active_window_title: str = ""
    active_window_process: str = ""
    elements: list[UIElement] = field(default_factory=list)
    element_count: int = 0
    source: str = "accessibility_tree"

    def find_by_name(self, name: str, partial: bool = False) -> list[UIElement]:
        """Search all elements for matches by name."""
        results: list[UIElement] = []
        for element in self.elements:
            results.extend(element.find_by_name(name, partial=partial))
        return results

    def find_interactive(self) -> list[UIElement]:
        """Return all interactive elements across the entire screen."""
        results: list[UIElement] = []
        for element in self.elements:
            results.extend(element.find_interactive())
        return results

    def to_compact_dict(self) -> dict[str, Any]:
        """Compact serialization for LLM context.

        Only includes the active window's interactive elements to keep
        the token count manageable. Full state is available via to_full_dict().
        """
        interactive = self.find_interactive()
        return {
            "timestamp": self.timestamp,
            "active_window": self.active_window_title,
            "process": self.active_window_process,
            "interactive_elements": [e.to_compact_dict() for e in interactive[:50]],
            "total_elements": self.element_count,
        }
