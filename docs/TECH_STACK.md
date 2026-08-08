# Technology Stack

This stack was chosen for a production-grade local-first agent, heavily prioritizing open-source, local efficiency, and free-tier cloud offloading where necessary.

## 1. Visual Overlay Layer (Frontend)
- **Framework**: Electron + React + TypeScript + Tailwind CSS.
- **Why**: Electron is the only mature cross-platform framework that flawlessly supports frameless, transparent windows with dynamic `setIgnoreMouseEvents` (click-through) behavior, crucial for an unobtrusive desktop overlay.
- **Docs**: [Electron](https://www.electronjs.org/docs)

## 2. Core Orchestration & Automation (Backend)
- **Language**: Python (FastAPI for WebSocket communication).
- **Why**: Python is the lingua franca of AI, accessibility APIs, and OS automation.
- **Screen Perception**:
  - Windows: `uiautomation` / `pywinauto`.
  - macOS: `pyobjc-framework-ApplicationServices` (AX API).
  - **Why**: Accessibility APIs provide cheap, instantaneous, semantic DOMs of the OS without the massive token cost of Vision models.
- **Browser Automation**: Playwright.

## 3. Voice Layer
- **Wake Word**: openWakeWord.
  - **Why**: Lightweight, fully local, CPU-friendly, no cloud dependency.
- **Speaker Verification**: SpeechBrain (ECAPA-TDNN).
  - **Why**: State-of-the-art open-source speaker recognition. 
  - **Hosting**: Deployed on **Google Cloud Run (Free Tier)** as a microservice. Keeps the heavy embedding model off the local laptop's memory.
- **Speech-to-Text (STT)**: Groq API (Whisper via Groq's ultra-fast inference).
  - **Why**: User explicitly requested Groq. Sub-200ms latency, generous free tier, eliminates local compute cost for STT. See ADR 7.
- **Text-to-Speech (TTS)**: Kokoro v1.0.
  - **Why**: Best-in-class for 2025/2026 local real-time TTS. Only 82M parameters, blazing fast on CPU, permissive license.

## 4. Memory & State
- **Long-Term Memory & Skills**: Supabase (PostgreSQL).
  - **Why**: Generous free tier. Keeps the local SQLite database from bloating over time. Enables cross-device syncing of preferences and skills later on.
- **World-State Tracker**: Local SQLite (`aiosqlite`).
  - **Why**: Zero latency. Perfect for ephemeral, high-frequency state tracking (active windows, cursor positions, task breadcrumbs).

## 5. Extensibility
- **Tools Protocol**: Model Context Protocol (MCP).
  - **Why**: The emerging standard for agent tools. Allows JAR to plug into hundreds of community tools safely.
