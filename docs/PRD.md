# Product Requirements Document (PRD): JAR

## 1. Vision & Goals
JAR is a local-first, voice-activated, fully agentic desktop assistant — a personal Jarvis. It has a persistent visual presence, root-level access to the computer, and the ability to see the screen, hear the user, and act on the computer with human-level fluency. 

The core goal is to build an assistant that feels genuinely alive and smart through architecture (verification loops, state tracking, confidence signaling), rather than just relying on a smart LLM.

## 2. User Stories
- **The Handoff:** "Take over what I'm doing while I grab coffee." JAR understands the active task from screen context and continues it.
- **End-to-End Workflows:** "Create a YouTube video for my channel and post it." JAR handles the entire pipeline, from script to voiceover to uploading.
- **Secure Voice Wake:** "Jar." The assistant wakes *only* to the user's voice, ignoring others.
- **Fast Mode:** "Full access." JAR stops asking for permission and executes autonomously for speed.

## 3. Functional Requirements
- **Perception:** Read OS accessibility trees (UIAutomation/AX API) natively. Fallback to Vision/OCR.
- **Voice Gate:** Wake-word detection followed by a one-time speaker verification check.
- **Action Execution:** Programmatic mouse/keyboard control with human-paced simulated typing.
- **Browser Automation:** Managed Playwright instances that can hand off to user sessions.
- **Verification Loop:** Every action must be verified (State A -> Action -> State B) before proceeding.
- **World-State Tracker:** A persistent local record of current screen state, open apps, and task checkpoints.
- **Visual Overlay:** Always-on-top, transparent, click-through UI featuring an animated Orb, screen glow, and floating glass cards.
- **Memory & Skills:** Tiered memory (short-term, working, long-term). Ability to learn skills via demonstration ("teach me").

## 4. Non-Functional Requirements
- **Footprint:** Must run efficiently on a local laptop. Use free-tier cloud services for heavy inference (Speaker Verification, heavy LLMs) to avoid eating local storage/compute.
- **Latency:** Real-time voice interaction requires <500ms time-to-first-audio (TTFA).
- **Reliability:** Must have a verification-gated execution loop. No blind multi-step execution.
- **Extensibility:** Use Model Context Protocol (MCP) for 3rd-party tools.

## 5. Out of Scope
- Solving CAPTCHAs programmatically (JAR will pause and hand off to the user).
- Impersonating the user to third parties without disclosure.
- Continuous, always-on microphone transcription (listens only for wake-word).
