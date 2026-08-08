# Project Structure

```text
JAR/
├── docs/                   # Persistent context and planning documents
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── TECH_STACK.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   └── BUGS_AND_FIXES.md
│
├── core/                   # Python Backend - The Brain & OS integration
│   ├── main.py             # FastAPI entrypoint (WebSocket server)
│   ├── perception/         # UIA/AX API parsers, Vision fallback
│   ├── action/             # PyAutoGUI wrappers, Playwright automation
│   ├── voice/              # openWakeWord, Whisper, Kokoro TTS integration
│   ├── reasoning/          # LLM API calls, Critic pass, Hypothesis gen
│   ├── memory/             # Supabase clients, SQLite World-State tracker
│   └── skills/             # Sandboxed skill execution, MCP client
│
├── frontend/               # Electron + React Visual Overlay
│   ├── package.json
│   ├── electron/
│   │   └── main.ts         # Window management (alwaysOnTop, transparency)
│   └── src/
│       ├── components/     # Orb, Floating Cards, Screen Glow
│       ├── hooks/          # WebSocket hooks for Core communication
│       └── styles/         # Tailwind CSS, Glassmorphism utilities
│
├── supabase/               # Database schemas and edge functions
│   └── migrations/         # SQL files for memory and skills tables
│
├── assets/                 # Shared media
│   ├── icons/
│   ├── animations/
│   └── ASSETS_README.md
│
└── .github/
    └── workflows/          # CI/CD pipelines
```
