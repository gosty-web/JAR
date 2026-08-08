# Architecture Decision Records (ADRs)

## ADR 1: Electron vs. Tauri vs. Native UI for Visual Layer
- **Decided**: Electron
- **Considered**: Tauri, Native (Swift/WPF)
- **Why**: Electron is the only mature cross-platform framework that flawlessly supports frameless, transparent windows with dynamic `setIgnoreMouseEvents` (click-through) behavior, crucial for an unobtrusive desktop overlay. Tauri's transparent window support is spotty on Windows/Linux, and native UIs require writing the overlay twice.

## ADR 2: OS Accessibility APIs (UIA) vs. Pure Vision Models
- **Decided**: OS Accessibility APIs (UIAutomation on Windows, AX API on macOS) with Vision fallback.
- **Considered**: Pure Vision models (like OmniParser/GPT-4V on every frame).
- **Why**: UIA is practically free computationally, instantaneous, and provides exact semantic bounding boxes. Vision models on every frame would cripple laptop performance or drain api budgets instantly. Vision is strictly a fallback.

## ADR 3: Local TTS vs. Cloud TTS
- **Decided**: Local Kokoro v1.0 TTS.
- **Considered**: ElevenLabs, OpenAI TTS, Piper.
- **Why**: Kokoro v1.0 has 82M parameters, making it blazing fast on edge hardware/CPUs with very low latency (Time-to-first-audio), whilst maintaining a high quality voice. Free and local fits the spec perfectly.

## ADR 4: Cloud Speaker Verification vs. Local
- **Decided**: Cloud-hosted SpeechBrain (ECAPA-TDNN) via GCP/Azure Free Tier.
- **Considered**: Local SpeechBrain.
- **Why**: The user specified wanting to avoid consuming significant local laptop storage/compute for heavy inference. While speaker verification *can* run locally, moving it to a free-tier cloud container keeps the laptop footprint lightweight and battery-friendly, only firing a small audio snippet on wake.

## ADR 5: Supabase vs. Local SQLite for Memory
- **Decided**: Both (Hybrid). Local SQLite for World-State, Supabase for Long-Term Memory.
- **Why**: World-State (active windows, current step) needs 0ms latency and is ephemeral; SQLite is perfect. Long-term memory (logs, skill library) grows infinitely; pushing this to Supabase keeps the laptop lightweight and allows for future cross-device syncing.

## ADR 6: MCP Integration Security (Updated by ADR 8)
- **Decided**: All third-party MCP servers are sandboxed and require explicit whitelist approval before first run in **default mode**.
- **Why**: MCP servers run locally. A poisoned tool description or malicious server could exfiltrate tokens or run arbitrary code.
- **Update (ADR 8)**: In YOLO/Full-Access mode, MCP servers that have been previously approved OR that are in the user's configured MCP registry do NOT require re-approval. Only truly new, never-seen-before MCP servers still prompt. This was changed per user directive - they want YOLO mode to mean zero friction.

## ADR 7: STT via Groq API (not local Whisper)
- **Decided**: Use Groq API for Speech-to-Text.
- **Considered**: Local `faster-whisper`, OpenAI Whisper API.
- **Why**: User explicitly requested Groq API for STT. Groq provides extremely fast inference (sub-200ms) for Whisper models via their cloud API, with a generous free tier. This avoids local compute cost for STT entirely. The `faster-whisper` dependency is removed from requirements.

## ADR 8: YOLO Mode MCP Behavior
- **Decided**: In YOLO/Full-Access mode, previously-approved MCP servers execute without user confirmation. Only new, never-registered MCP servers prompt for first-time approval.
- **Considered**: Always requiring MCP approval regardless of mode (original ADR 6).
- **Why**: User explicitly stated "when jar is in YOLO mode even MCPs will not need my approval." The security boundary is moved to first-registration only - once a server is in the registry, YOLO mode trusts it.

### ADR 9: Background Verification
**Context:** Verification currently requires window focus, disrupting user flow.
**Decision:** `ScreenReader` must provide a `read_window(title)` method to read accessibility trees in the background. If a window is obscured, UIA usually still has tree access.
**Consequences:** Less intrusive for the user, but some apps (like browsers) pause rendering when fully occluded.

### ADR 10: Vision/OCR Fallback Implementation
**Context:** When the accessibility tree fails or is empty, we need a reliable fallback.
**Decision:** Implement native Windows `winrt` OCR (`winrt.windows.media.ocr`) directly in `core/perception/vision_reader.py`. Text bounding boxes are created by aggregating word bounding boxes, and elements are returned as `ControlType.TEXT` but marked as interactive via a `source="vision_ocr"` property.
**Consequences:** Avoids external API calls and latency, keeps privacy on-device, but requires `winrt` dependencies which are Windows-specific. Cross-platform support will need a similar native macOS approach or a Tesseract/cloud fallback.

## ADR 11: Background Execution (Non-Focus-Stealing)
- **Decided**: JAR must be able to execute tasks in the background while the user works on something else, without stealing focus or disrupting the user's active window.
- **Considered**: Sequential execution (agent takes over, user waits).
- **Why**: User explicitly wants to be doing something while JAR works on a separate task. This means: (1) Playwright browser instances run in a separate, non-focused window or headless mode. (2) Mouse/keyboard actions that would steal focus from the user's active app must be deferred or routed through accessibility API invocations rather than raw input simulation. (3) The World-State Tracker must distinguish between "user-active-window" and "agent-active-window."

### ADR 12: Hybrid Action Layer Design (ADR 11 Compliance)
**Context:** Per ADR 11, the agent should not steal the user's physical mouse cursor if possible.
**Decision:** The Action Layer (`ActionService`) uses a hybrid approach on Windows. It accepts semantic elements for clicks (`click_element`). If an element is passed, it attempts a fast background lookup via `uiautomation` and triggers `InvokePattern.Invoke()` natively without moving the mouse. If that fails or raw coordinates are passed (e.g. from Vision/OCR), it falls back to `pyautogui` which physically moves the cursor.
**Consequences:** Keeps background tasks unobtrusive for UIA-compliant apps, but accepts that Vision-based tasks must temporarily steal the mouse.

## ADR 13: Search Provider for Automated Problem Solving
- **Date**: 2026-08-08
- **Context**: DuckDuckGo's HTML endpoint blocks automated traffic regardless of User-Agent. Google requires an API key. 
- **Decision**: Use Wikipedia's search endpoint (`https://en.wikipedia.org/w/index.php?search=...`) for background factual searches.
- **Consequences**: Fast, free, unblocked knowledge graph access. Cannot search for dynamic live info (like current weather), which will require a fallback tool later.

## ADR 14: Persistent Browser Profile for Action Layer
- **Date**: 2026-08-08
- **Context**: The user wants JAR to perform actions on their behalf in logged-in applications. However, attempting to use the user's active Chrome/Edge profile throws a strict file lock error if the browser is already open.
- **Decision**: Playwright uses `launch_persistent_context` pointing to a dedicated local directory (`.jar_profile`) with `headless=False` (visible window).
- **Consequences**: JAR will have its own dedicated browser window. The user must log in to their apps within JAR's window once. After that, the session is preserved. This completely avoids file lock collisions with the user's main browser while allowing simultaneous work.

## ADR 15: Ephemeral SQLite World-State
- **Date**: 2026-08-08
- **Context**: The LLM needs strict context of where it is in a long-running execution loop without blowing up the context window.
- **Decision**: Implemented `aiosqlite` local database in `core/memory/world_state.py`. Tracks generic state (Key-Value) and an append-only `action_log`.
- **Consequences**: Fast local tracking. State can be wiped cleanly on startup to prevent stale context.

## ADR 11: AWS for Hosting and Management
- **Decided**: AWS is available for auto-hosting and managing services (speaker verification, other microservices) via the user's existing AWS tooling.
- **Considered**: Google Cloud Run only (original plan).
- **Why**: User has AWS tools configured and wants JAR to be able to use them for hosting without manual intervention. This supplements (and may replace) the GCP Cloud Run plan from ADR 4.

## ADR 16: Abstracted Reasoning with LiteLLM
- **Date**: 2026-08-08
- **Context**: We need a way to run the reasoning loop against various models (user prefers Groq, but might want OpenAI/Anthropic later) and also mock it completely for rapid stress tests.
- **Decision**: Use `litellm` inside `ReasoningEngine` (`core/reasoning/llm.py`). Provide a `use_mock=True` flag for deterministic, fast stress testing of the framework logic.
- **Consequences**: Standardized API interface, easy mocking for CI/stress tests, and simple switching between model providers using environment variables.
