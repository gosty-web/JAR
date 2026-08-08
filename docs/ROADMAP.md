# Build Roadmap

Order strictly follows the project spec priorities: Reliability first, Visuals second. 
**Do not check an item off until it is verified working.**

## Phase 1: Core Perception & Automation
- [x] Implement `uiautomation` / `ApplicationServices` wrapper to extract accessibility trees.
- [x] Implement Vision/OCR fallback layer (native Windows `winrt` OCR for minimal latency).
- [x] Build basic programmatic mouse/keyboard control.
- [x] Build basic Playwright browser automation module.

## Phase 2: Verification-Gated Action Loop & World-State
- [x] Set up local SQLite World-State Tracker.
- [x] Implement the execution loop (Perceive -> Plan -> Critic -> Act -> Verify).
- [x] Ensure World-State correctly logs step success/failures.

### Phase 3: The First Reliable Skill
- [x] Integrate `litellm` into `core/reasoning/llm.py` to support OpenAI, Anthropic, and Groq endpoints.
- [x] Wire `ExecutionLoop` to query the LLM for `Plan`, `Critic`, and `Verify` steps.
- [x] Extend `ActionService` with a `write_file` capability for summary outputs.
- [x] Build the first end-to-end skill: "Summarize the current screen and save to a file."
- [x] **Verification**: Stress-test this skill 50 times in a row using a mocked or lightweight local model. It must hit a 99% reliability threshold before moving to Phase 4.

### Phase 4: Voice Layer
- [x] Integrate `openWakeWord` (local, always-listening).
- [x] Integrate `SpeechBrain` ECAPA-TDNN (free-tier cloud microservice) for Speaker Verification.
- [x] Integrate STT (`Whisper`) and TTS (`Kokoro v1.0`).
- [x] Hook Voice Layer into the WebSocket event bus.

## Phase 5: The Orb & Minimum Visual States
- [x] Scaffold Electron app with transparent, click-through, frameless window.
- [x] Build the Orb React component (Idle, Listening, Speaking, Working, Blocked).
- [x] Connect Orb states to the WebSocket event bus.

## Phase 6: Reasoning Refinements
- [x] Implement Hypothesis Generation (2-3 candidate interpretations for ambiguous commands).
- [x] Implement explicit Confidence Scoring.
- [x] Refine Critic Pass logic.

## Phase 7: Memory & Skills
- [x] Set up Supabase Postgres instance.
- [x] Implement Long-Term and Working memory tiers.
- [x] Implement Skill Library versioning and sandboxed execution.
- [x] Implement "Teach Me" capture mode (demo to skill).

## Phase 8: Visual Polish
- [ ] Anticipatory micro-motion on cursor/orb.
- [ ] Mouse-dot trail effects.
- [ ] Screen Glow edge effects.
- [ ] Constellation view in Control Panel.
- [ ] Sound design (chimes, notifications).

## Phase 9: Permissions & Edge Cases
- [ ] "Full Access" voice toggle.
- [ ] CAPTCHA / Email Verification handoff pattern (pause task, wait for user, resume).
