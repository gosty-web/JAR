# Perception Layer
# Responsible for reading the OS accessibility tree and providing structured
# screen-state data to the reasoning layer.
#
# Architecture note (ARCHITECTURE.md §1): This is the primary perception source.
# Vision/OCR is a fallback only, invoked when the accessibility tree comes back
# empty or incomplete for the current region of interest.

from core.perception.models import UIElement, ScreenState, ControlType  # noqa: F401
from core.perception.screen_reader import ScreenReader  # noqa: F401
