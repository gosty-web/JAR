"""Unit tests for core.perception.models.

Tests the OS-agnostic data models that all perception backends produce.
These tests do NOT require UIAutomation or any OS-specific library -
they test pure data logic.
"""

import pytest

from core.perception.models import BoundingBox, ControlType, ScreenState, UIElement


class TestBoundingBox:
    """Tests for BoundingBox geometry calculations."""

    def test_basic_properties(self) -> None:
        bbox = BoundingBox(left=100, top=200, width=300, height=150)
        assert bbox.right == 400
        assert bbox.bottom == 350
        assert bbox.center_x == 250
        assert bbox.center_y == 275

    def test_contains_point_inside(self) -> None:
        bbox = BoundingBox(left=10, top=10, width=100, height=100)
        assert bbox.contains_point(50, 50) is True

    def test_contains_point_on_edge(self) -> None:
        bbox = BoundingBox(left=10, top=10, width=100, height=100)
        assert bbox.contains_point(10, 10) is True  # top-left corner
        assert bbox.contains_point(110, 110) is True  # bottom-right corner

    def test_contains_point_outside(self) -> None:
        bbox = BoundingBox(left=10, top=10, width=100, height=100)
        assert bbox.contains_point(0, 0) is False
        assert bbox.contains_point(200, 200) is False

    def test_to_dict(self) -> None:
        bbox = BoundingBox(left=10, top=20, width=30, height=40)
        d = bbox.to_dict()
        assert d == {"left": 10, "top": 20, "width": 30, "height": 40}


class TestUIElement:
    """Tests for UIElement data model and search methods."""

    def _make_element(
        self,
        element_id: int = 1,
        control_type: ControlType = ControlType.BUTTON,
        name: str = "Test",
        **kwargs,
    ) -> UIElement:
        return UIElement(
            element_id=element_id,
            control_type=control_type,
            name=name,
            **kwargs,
        )

    def test_is_interactive_button(self) -> None:
        btn = self._make_element(control_type=ControlType.BUTTON, is_enabled=True)
        assert btn.is_interactive is True

    def test_is_interactive_disabled(self) -> None:
        btn = self._make_element(
            control_type=ControlType.BUTTON,
            is_enabled=False,
        )
        assert btn.is_interactive is False

    def test_is_interactive_static_text(self) -> None:
        txt = self._make_element(control_type=ControlType.TEXT)
        assert txt.is_interactive is False

    def test_display_text_prefers_name(self) -> None:
        e = self._make_element(name="Submit", value="some_value")
        assert e.display_text == "Submit"

    def test_display_text_falls_back_to_value(self) -> None:
        e = self._make_element(name="", value="Hello World")
        assert e.display_text == "Hello World"

    def test_display_text_falls_back_to_class(self) -> None:
        e = self._make_element(name="", value="", class_name="Button")
        assert e.display_text == "Button"

    def test_display_text_unnamed_fallback(self) -> None:
        e = self._make_element(name="", value="", class_name="")
        assert e.display_text == "unnamed"

    def test_find_by_name_exact(self) -> None:
        root = self._make_element(element_id=1, name="Root")
        child = self._make_element(element_id=2, name="Submit")
        root.children.append(child)

        results = root.find_by_name("Submit")
        assert len(results) == 1
        assert results[0].element_id == 2

    def test_find_by_name_partial(self) -> None:
        root = self._make_element(element_id=1, name="Root")
        child = self._make_element(element_id=2, name="Submit Form")
        root.children.append(child)

        results = root.find_by_name("submit", partial=True)
        assert len(results) == 1

    def test_find_by_name_no_match(self) -> None:
        root = self._make_element(element_id=1, name="Root")
        results = root.find_by_name("NonExistent")
        assert len(results) == 0

    def test_find_by_type(self) -> None:
        root = self._make_element(
            element_id=1,
            control_type=ControlType.WINDOW,
            name="Window",
        )
        btn = self._make_element(element_id=2, control_type=ControlType.BUTTON, name="OK")
        txt = self._make_element(element_id=3, control_type=ControlType.TEXT, name="Label")
        root.children.extend([btn, txt])

        buttons = root.find_by_type(ControlType.BUTTON)
        assert len(buttons) == 1
        assert buttons[0].name == "OK"

    def test_find_interactive(self) -> None:
        root = self._make_element(
            element_id=1,
            control_type=ControlType.WINDOW,
            name="Window",
        )
        btn = self._make_element(element_id=2, control_type=ControlType.BUTTON, name="OK")
        txt = self._make_element(element_id=3, control_type=ControlType.TEXT, name="Label")
        edit = self._make_element(element_id=4, control_type=ControlType.EDIT, name="Input")
        root.children.extend([btn, txt, edit])

        interactive = root.find_interactive()
        assert len(interactive) == 2
        names = {e.name for e in interactive}
        assert names == {"OK", "Input"}

    def test_flatten(self) -> None:
        root = self._make_element(element_id=1, name="Root")
        child1 = self._make_element(element_id=2, name="Child1")
        child2 = self._make_element(element_id=3, name="Child2")
        grandchild = self._make_element(element_id=4, name="Grandchild")
        child1.children.append(grandchild)
        root.children.extend([child1, child2])

        flat = root.flatten()
        assert len(flat) == 4
        assert [e.element_id for e in flat] == [1, 2, 4, 3]

    def test_to_compact_dict_minimal(self) -> None:
        e = self._make_element(element_id=5, name="OK", control_type=ControlType.BUTTON)
        d = e.to_compact_dict()
        assert d["id"] == 5
        assert d["type"] == "button"
        assert d["name"] == "OK"
        assert "disabled" not in d  # enabled by default

    def test_to_compact_dict_disabled(self) -> None:
        e = self._make_element(
            element_id=1,
            name="Submit",
            control_type=ControlType.BUTTON,
            is_enabled=False,
        )
        d = e.to_compact_dict()
        assert d.get("disabled") is True

    def test_to_compact_dict_truncates_long_values(self) -> None:
        e = self._make_element(
            element_id=1,
            name="Input",
            control_type=ControlType.EDIT,
            value="x" * 500,
        )
        d = e.to_compact_dict()
        assert len(d["value"]) == 200


class TestScreenState:
    """Tests for ScreenState aggregation and search."""

    def _make_screen_state(self) -> ScreenState:
        btn = UIElement(
            element_id=1,
            control_type=ControlType.BUTTON,
            name="Submit",
        )
        edit = UIElement(
            element_id=2,
            control_type=ControlType.EDIT,
            name="Email",
            value="test@example.com",
        )
        label = UIElement(
            element_id=3,
            control_type=ControlType.TEXT,
            name="Enter your email:",
        )
        return ScreenState(
            timestamp=1234567890.0,
            active_window_title="Test Window",
            active_window_process="test.exe",
            elements=[btn, edit, label],
            element_count=3,
        )

    def test_find_by_name(self) -> None:
        state = self._make_screen_state()
        results = state.find_by_name("Submit")
        assert len(results) == 1

    def test_find_interactive(self) -> None:
        state = self._make_screen_state()
        interactive = state.find_interactive()
        assert len(interactive) == 2  # Button + Edit, not Text
        names = {e.name for e in interactive}
        assert names == {"Submit", "Email"}

    def test_to_compact_dict(self) -> None:
        state = self._make_screen_state()
        d = state.to_compact_dict()
        assert d["active_window"] == "Test Window"
        assert d["process"] == "test.exe"
        assert d["total_elements"] == 3
        # Only interactive elements in the compact view
        assert len(d["interactive_elements"]) == 2
