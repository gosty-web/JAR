# JAR — Personal Desktop AI Agent
## Full Specification v1

---

## 0. Project Overview

JAR is a full-blown personal AI operating layer for the user's own laptop — a real, working version of the "Jarvis" concept, in the spirit of tools like Warmwind's AIOS. It is not a chatbot with some automation bolted on; it is meant to be an always-present, always-aware assistant that lives on the desktop, watches the screen, listens for its own name in the user's voice specifically, and can genuinely operate the computer on the user's behalf — opening and using applications, controlling the browser, editing video, writing and sending things, filling out forms, and carrying out full multi-step workflows end to end.

The user wants to be able to say "Jar" and have it respond only to their voice, not anyone else's. They want to hand it a task mid-stream — "take over what I'm doing while I grab coffee" — and have it look at the screen, understand what they were already working on, and continue it. They want it to have real memory, a growing library of skills, the ability to use tools and MCPs, and even the ability to write basic new capabilities for itself over time, so it genuinely improves the longer it's used. It should be able to find things intelligently — e.g., locate a file by its actual content even if it wasn't given an obvious name — rather than relying on exact filenames.

Visually, the user wants JAR to have a persistent, small, animated presence on screen — an orb in the top-right corner that morphs and reacts while listening or speaking, similar to the reference behavior shown in the screenshots provided (a stale/idle state versus an actively-moving state). When JAR is operating the computer, the user wants visible, glassy, macOS-style feedback: the edges of the screen glowing to show it's active, a visible "mouse" of its own (a dot that presses, stretches while scrolling, and turns into a cursor while typing), and floating glass-style cards that can show a countdown timer, a generated diagram, or a task board, all of which the user can move around or ask JAR to move. Typing should look like real human typing — streamed, not pasted instantly.

The user also wants it to be capable of full, real workflows — for example, being told "create a YouTube video for my channel and post it" and having JAR carry out the entire pipeline using the tools and process the user already relies on, including recording its own voiceover audio. It should be able to handle everyday obstacles like signups and email verification codes. It should have root-level access to the computer to make all of this possible.

On permissions, the user does not want heavy friction by default — they want the option to say something like "full access" and have JAR drop into a mode where it just acts, without stopping to ask permission for each step.

On voice, the user wants speaker verification to run only once, at the moment the wake word is spoken — not continuously throughout a conversation — so that a stranger saying "Jar" is ignored, but once JAR has confirmed it's the user's voice, it doesn't keep re-checking.

The user wants this built using free tools wherever possible, and tools that don't consume significant local laptop storage — favoring free-tier cloud hosting (e.g., Google Cloud, Azure) for anything heavier, such as the voice/speaker-verification model, rather than running large models locally.

Overall, the goal is something that feels genuinely futuristic and alive — smart, aware, capable of long and accurate computer use, visually striking, and trustworthy enough to hand real responsibility to.

---

## 1. Vision & Goals

JAR is a local-first, voice-activated, fully agentic desktop assistant — a personal Jarvis. It has:

- Persistent visual presence on screen (an ambient orb)
- Root-level access to the user's computer
- The ability to see the screen, hear the user, use the camera, and act on the computer (click, type, scroll, open apps, use the browser) with human-level fluency
- Voice-gated wake behavior tied to the owner's voice specifically
- Long-term memory, a growing skill library, tool/MCP access, and the ability to write new skills for itself
- A visual language that makes its state (idle, listening, thinking, working, blocked) legible at a glance
- The ability to take over active tasks mid-stream ("take over my task while I get coffee") using context from recent screen activity
- A default permission-tiered safety model, with a voice-toggled "full access" mode that suspends confirmation prompts entirely when the user wants speed over caution

The core design principle across every layer: **feel alive and smart through architecture, not just model intelligence.** A better LLM helps, but the actual feeling of "this thing is sharp" comes from structural choices — verification loops, state tracking, confidence signaling, anticipatory motion — that no single model call provides on its own.

**Guiding constraint on scope:** everything in this spec is buildable with free or generous-free-tier tools, runs primarily local (voice/vision inference can be cloud-hosted on a free tier to avoid eating laptop storage/compute), and avoids anything that requires bypassing platform security measures (real CAPTCHA solving is explicitly out of scope — see §7).

**Explicit non-goal:** JAR does not impersonate the user to other people without their knowledge (e.g., answering interview questions or running a live demo while a counterpart believes they're interacting with the user unassisted, undisclosed). Meeting-copilot features are scoped as private-to-the-user overlays only (§6.9) — suggestions visible to the user while they do their own talking, not the agent acting as the user toward someone who doesn't know an agent is involved.

---

## 2. System Architecture Overview

JAR is composed of six subsystems that communicate over a local event bus / shared state store:

1. **Perception Layer** — screen understanding, accessibility tree parsing, OCR/vision fallback, audio input
2. **Action Layer** — mouse/keyboard control, browser automation, app control
3. **Reasoning & Orchestration Layer** — planning, hypothesis generation, confidence scoring, critic pass, tool/skill routing
4. **Memory & Skill System** — tiered memory, skill library with versioning, MCP/tool registry
5. **Visual Overlay Layer** — the orb, screen glow, mouse-dot, floating glass cards, memory/skills panel
6. **Voice Layer** — wake-word detection, speaker verification, TTS/STT, voice-mode conversation

A **World-State Tracker** sits at the center — a persistent, explicit record of "what is currently true" (open apps, active window, pending approvals, last-known task, last failure) that every subsystem reads from and writes to, rather than each layer re-deriving state from scratch on every step. This is the single most important architectural decision for making long tasks feel coherent rather than repeatedly "waking up confused."

---

## 3. Perception Layer

### 3.1 Screen Understanding
- **Primary source:** OS accessibility APIs — UIAutomation (Windows) / AX API (macOS). These expose a tree of on-screen elements with bounding boxes, roles, and labels essentially for free, with no vision-model cost. This should cover the large majority of standard app UI.
- **Fallback source:** vision-model + OCR pass for anything the accessibility tree doesn't expose — canvas-rendered apps, video, games, custom-drawn UI. Only invoked when the accessibility tree comes back empty or clearly incomplete for the current region of interest, to control cost.
- **Element marking:** every interactive element the agent can act on gets a precise marker (following the user's original "mark every visible part of the object" instinct) rather than a coarse bounding box — but sourced from the accessibility tree's actual geometry where available, keeping it cheap. This is the desktop analogue of set-of-marks prompting used in browser-use agents, extended to native OS elements.
- **Change detection:** re-scan only on meaningful screen change (window focus change, DOM/tree diff, or periodic low-frequency poll) rather than every single frame, to keep this affordable on free/low compute.

### 3.2 Audio Input
- Continuous low-power listening for the wake word only (see §7.1) — no continuous transcription running in the background, for both privacy and resource reasons.
- Once woken, full STT kicks in for command capture and, if voice-mode conversation is active, stays on for the duration of that exchange.

### 3.3 Camera Input
- Available as an on-demand capability (e.g., "can it see who's calling my name" style checks, if ever needed) — not a continuously-running always-on stream by default, to keep resource usage sane. Explicitly invoked by a skill/task rather than a background process.

---

## 4. Action Layer

### 4.1 Input Control
- Programmatic mouse/keyboard control (e.g., via OS-level automation libraries — `pyautogui`/native equivalents, or accessibility-API-driven invocation where available, which is both more reliable and less visually janky than raw coordinate clicking).
- **Typing behavior:** streamed, human-paced typing into the actual target field for the visual "it's really typing" effect the user wants; for large blocks of content where reliability matters more than the visual effect, clipboard-paste the real content and only simulate the typing animation in the overlay UI, not into the target app (see §6.6 gotcha — some apps drop rapid synthetic keystrokes).

### 4.2 Browser Automation
- A dedicated automation browser instance (Playwright or equivalent) for tasks JAR initiates itself — separate from the user's actively-open browser window, per the original spec ("if I'm using my browser, it opens another window").
- Detection of user's current browser activity (via window/tab awareness) to decide whether to act in a new window or, if explicitly told to use the current one, hand off appropriately.

### 4.3 App Control
- Generalized app-launch and in-app control via the accessibility tree + action layer combination above — not app-specific integrations for every possible target app, so the system generalizes rather than requiring bespoke code per application (this is what makes "it can even use CapCut" plausible without hand-building a CapCut-specific module).

### 4.4 Verification-Gated Execution (core reliability mechanism)

This is the single most important piece of the whole system, and it's structural, not model-dependent. Even top-tier 2026 computer-use models succeed at a minority of genuinely open-ended desktop tasks without this kind of scaffolding — the field's whole 2026 direction has moved from "how do we get a smarter model" to "how do we build reliable verification architecture around any model." Every action in JAR follows this loop:

1. **Perceive** current state (screenshot + accessibility tree snapshot)
2. **Plan** single next action (not a whole multi-step plan executed blind)
3. **Act** (one action)
4. **Verify** — before/after state comparison confirms the expected change happened (window opened, field now contains expected text, etc.) — this can be a cheap deterministic check where possible, not necessarily a full LLM call
5. **On failure:** retry once with an adjusted approach; if that also fails, stop and surface to the user rather than continuing on a possibly-wrong assumption
6. **Checkpoint:** log the step to the task's running breadcrumb trail in the World-State Tracker, so a later failure or a "take over" handoff can resume from a known-good point instead of restarting

---

## 5. Reasoning & Orchestration Layer

This layer is where "feels smart" is built structurally, independent of which underlying model is doing the reasoning.

### 5.1 Tool/Skill Router
A cheap, fast classification step runs first on any new instruction — "this is a browser task / file task / creative task / meeting task" — and hands off to a specialized sub-flow with the right tools and context pre-loaded, rather than one giant general-purpose prompt trying to do everything. Faster, cheaper, and reads as more decisive.

### 5.2 Hypothesis Generation for Ambiguous Instructions
On ambiguous instructions, generate 2–3 candidate interpretations rather than committing to the first linear plan, score them silently against current World-State context (recent activity, known habits, currently open apps), and only surface a question to the user if the top two candidates are close. Sharply reduces confidently-wrong execution on vague commands ("open the file" when multiple files could match).

### 5.3 Critic Pass
After a plan or draft output is produced (an action plan, a drafted email, a file to send), run a second, distinct evaluation step — same or different model, different prompting role — specifically checking for problems before execution: does this plan touch something risky, does this sound like something the user would actually send, is this the file that was actually meant. Actor/critic separation is one of the most reliable ways to raise apparent intelligence without needing a better base model.

### 5.4 Confidence Scoring
Every decision carries an explicit confidence value derived from concrete factors: how many similar past tasks succeeded, how ambiguous the current on-screen state is, whether this matches a known skill versus improvising something new. High confidence → proceed. Low confidence → ask, or (in default mode) request confirmation; in full-access/YOLO mode (§7.2) this still computes but never blocks execution — it only feeds the visual confidence signal (§6.7).

### 5.5 World-State Tracker
A persistent, explicit record — separate from long-term memory — of what's currently true: open apps, active window, in-progress task and its checkpoint, anything pending user approval, the most recent failure and why. Queried before every decision instead of re-deriving from a fresh screenshot each time. This is what allows "wait, didn't I already open this" type coherence across a long task, and what makes the "take over my task" handoff (§8) possible — the agent reads recent World-State history instead of starting cold.

### 5.6 Causal Failure Logging
When a task fails or the user corrects the agent, log *why* — not just "clicking at X,Y failed" but "clicked at X,Y, but the window had moved because a notification appeared" — so future pattern-matching generalizes from causes, not just from memorized specific failures.

### 5.7 Reflection Pass
A periodic (end-of-session or end-of-day) pass, separate from any single task, where the agent reviews what happened — what succeeded, what needed repeated clarification, what failed and why — and updates its own skill library or working preference model accordingly. This is the actual mechanism behind "it grows," architecturally: a dedicated consolidation step, not a claim that the underlying model itself is getting smarter.

---

## 6. Visual Overlay Layer

Built as always-on-top transparent overlay windows (Electron gives glassmorphism/backdrop-blur essentially for free, matching the macOS-glass aesthetic the user wants) layered over the desktop, non-intrusive to normal work.

### 6.1 The Orb
Small, positioned top-right of the screen per the user's reference screenshots. States:

- **Idle:** subtle, slow, slightly asymmetric breathing pulse — deliberately not perfectly still or perfectly symmetric, so it reads as "alive and waiting" rather than "off." (Perfect stillness/symmetry reads as broken UI, not calm.)
- **Listening (post-wake-word):** morphs/reacts to live mic input amplitude (Web Audio API analyser node driving a blob/metaball shape) — matches the two-state reference behavior the user provided (stale vs. actively moving).
- **Speaking:** same morphing behavior, driven by the TTS output stream's amplitude as it plays, not the static audio file — needs to react in real time to what's actually being spoken.
- **Thinking:** a distinct state between listening and acting — denser, more turbulent morph pattern while reasoning is happening, resolving into a clean shape at the exact moment a decision is committed and action begins. Externalizes the reasoning-scratchpad idea (§5) visually.
- **Working (computer-use active):** paired with the screen-glow effect (§6.4).
- **Blocked/needs-you:** a visually distinct state (different color/pulse pattern) — used specifically for CAPTCHA handoffs (§7) and low-confidence pauses in default mode.
- **Confidence texture:** overlaid on any active state — high-confidence actions get a clean, saturated color; lower-confidence ones get a subtly desaturated/textured look, so confidence is readable at a glance without the agent needing to say anything (§5.4).

### 6.2 Anticipatory Micro-Motion
A brief, subtle directional lean/pulse toward where the agent is about to act, a beat before the action itself happens. This single animation principle — anticipation before action — is a large part of why animated characters read as "thinking" rather than "executing," and it's cheap to implement relative to its payoff.

### 6.3 The Mouse-Dot
The agent's own cursor representation, separate from the user's real cursor:
- **Click:** brief scale-pulse, looks like it physically pressed the object.
- **Scroll:** stretches along the scroll axis, then springs back to a dot (critically-damped spring easing) — matches the reference behavior the user described.
- **Typing:** morphs into a cursor/caret shape while streamed typing is happening.
- **Fast multi-action sequences:** a fading trail behind rapid consecutive actions, so a quick sequence reads as one fluid choreographed movement rather than a series of disconnected jumps.
- **Handoff transitions:** when control passes between user and agent ("take over" / user resumes), a visible transition — cursor fades out, dot fades in at the same screen position, with a brief connecting ripple — so the moment of control transfer is legible rather than jarring.

### 6.4 Screen Glow
Edge-of-screen gradient overlay, animated in/out based on agent-active state:
- **Working (normal):** standard glow indicating the agent is actively using the computer.
- **Blocked/needs-you:** distinct color (e.g., amber) — used for the CAPTCHA handoff and any default-mode confirmation pause.

### 6.5 Floating Glass Cards
Reusable card system (glassmorphism styling, draggable, user or agent can reposition) for:
- **Timers** (per the reference: orb morphs into a rectangle showing the countdown)
- **Diagrams** the agent generates
- **Task boards** (To Do / In Progress / Done, as specified)
- **Staging previews** — before executing anything irreversible-adjacent (posting content, sending a batch of messages), show the final artifact in a card for a quick glance/approval before it goes out, even in full-access mode this is worth keeping as a lightweight, non-blocking preview rather than a permission gate.

### 6.6 Control Panel
A dedicated panel (opened on demand) housing:
- Past sessions / conversation history
- Memory browser
- Skill library
- Tool/MCP registry
- Text chat interface (for typing instead of voice)
- **Constellation view:** memories and skills rendered as connected nodes rather than a flat list — nodes light up when actively in use, and new connections visibly form over time as the agent links related experiences (this skill was learned from that correction; this memory informed that decision). Makes "it has memory and learns" tangible rather than abstract, and doubles as a good demo view.

### 6.7 Environmental Reactivity
Small ambient touches that make the overlay feel aware of context, not just of its own task state:
- Dims automatically during screen-share/video calls so it isn't visible/distracting to others.
- Subtle color-temperature shift matching time of day.
- A barely-perceptible "alert" tremor if something urgent arrives while the user is away from keyboard.

### 6.8 Sound Design
A small, distinct set of subtle audio cues — separate tones for wake-word-confirmed, task-complete, needs-you/blocked, and error — so state is legible even when not looking at the screen. Audio is a large part of why JARVIS-style assistants read as "present," not just the visuals.

### 6.9 Meeting Copilot Overlay (scoped — see §1 non-goal)
A floating deck, visible only to the user (not shared in screen-share), that surfaces streamed suggestions/talking points during a live meeting or interview based on context the user has already given it (e.g., meeting prep done beforehand). This is a private aid to the user's own responses — the user is still the one speaking and acting. It does not extend to the agent operating the screen or speaking on the user's behalf while a counterpart believes they're dealing with the user alone; that use case is out of scope per §1.

---

## 7. Voice Layer

### 7.1 Wake Word + Speaker Verification
Two-stage gate, verification running **only at the wake-word moment**, not continuously — per the user's explicit preference:

1. **Wake-word detection** — lightweight, always-listening, low-power keyword spotter (open-source options: openWakeWord; or Picovoice's Porcupine, which has a free tier) detects "Jar" in the audio stream.
2. **Speaker verification** — the instant the wake word fires, the audio segment around it is checked against the user's enrolled voice embedding. If it matches, JAR wakes and proceeds normally; if not, it stays silent. This check happens once, at wake, and is not repeated for the remainder of the interaction — the user does not want ongoing re-verification mid-conversation.

**Recommended tools (free-tier-friendly, low local footprint):**
- **openWakeWord** — fully open-source, runs locally, minimal footprint, good default for the wake-word stage.
- **SpeechBrain (ECAPA-TDNN pretrained model)** for the speaker-embedding/verification stage — open-source, enroll the user with a short sample of natural speech (no fixed passphrase needed), store the resulting embedding, and compare via cosine similarity against new wake-word audio segments going forward.
- Given the "don't eat laptop storage" preference, the speaker-verification model can be hosted as a small inference service on a free-tier cloud instance (Google Cloud Run / Azure free tier both support light containerized inference workloads within their always-free or trial allowances) — the local client sends the short audio snippet at wake-word time and gets a match/no-match response back, keeping the model weights off the laptop entirely. This trades a small amount of latency at wake-time for meaningfully lower local footprint, which fits the stated priorities.
- **Caveat worth knowing and accepting deliberately:** speaker verification of this kind is not robust against deliberate voice-cloning/replay attacks. It's well suited to "don't let someone else casually trigger my assistant," which is the stated goal — not to security-critical gating.

### 7.2 STT / TTS
- STT: open-source Whisper (any size that fits acceptable latency on available compute — smaller model locally, or a free-tier hosted endpoint if local compute is tight) for command and conversation transcription once woken.
- TTS: an open-source or generous-free-tier TTS engine for the agent's spoken responses, driving the orb's speaking-state morph off the live output stream (§6.1).

### 7.3 Voice-Mode Conversation
Once woken and in an active exchange, the user can converse naturally with JAR — including mid-task ("how's that going") — while it continues executing, rather than voice mode blocking task execution.

---

## 8. Permissions & the "Full Access" Mode

### 8.1 Default Mode
A lightweight permission tiering exists by default:
- Low-risk/reversible actions (reading, browsing, checking status) proceed without confirmation.
- Higher-risk/harder-to-reverse actions (deleting files, sending messages, purchases, public posts) prompt for a quick confirmation, or check against a pre-approved allowlist the user has set once ("always fine to reply to known contacts," "never touch anything in Documents").
- Every action is logged to a visible action log with revert capability where technically possible.

### 8.2 Full Access ("YOLO") Mode
A voice command (e.g., "Jar, full access") toggles this off entirely — no confirmation prompts, no allowlist checks, the agent executes autonomously end-to-end until told otherwise (a corresponding voice command returns to default mode). Confidence scoring (§5.4) and the critic pass (§5.3) still run under the hood in this mode — they don't block execution, but they continue to drive the visual confidence signal (§6.1) and get logged, so the user still has a trail to review even when nothing was gated in the moment.

### 8.3 CAPTCHA / Verification Handoff
No CAPTCHA-solving capability is built — this is explicitly out of scope regardless of permission mode, both because it works against the purpose of bot-detection systems and because accounts risk being flagged/banned, which defeats the point for the user's own accounts. Instead:
- Perception layer detects a CAPTCHA (accessibility tree/DOM pattern matching on known CAPTCHA container signatures).
- Orb switches to the blocked/needs-you state (§6.1), screen glow shifts to the blocked color (§6.4), and JAR verbally flags it ("hit a captcha, over to you").
- Execution pauses; the World-State checkpoint (§4.4) holds the task's place.
- Once the user completes the CAPTCHA (detected by the container disappearing, or a verbal "go"/"done"), JAR resumes exactly from the checkpoint.
- The same pattern applies to email-verification-code steps that are simply reading a code from an inbox the user is already authenticated into — that's plain automation, not CAPTCHA-adjacent, and is in scope normally.

---

## 9. Memory & Skill System

### 9.1 Tiered Memory
- **Short-term:** this session only, discarded after.
- **Working:** persists while a project/task is actively in progress.
- **Long-term:** durable — user preferences, recurring contacts, recurring workflows, learned skills.
- Applies the same "pull full context, keep only the useful residue" pattern the user described for file search generally — not just as a one-off file-search behavior but as the general memory-write pattern across the system.

### 9.2 Skill Library
- Skills are small, scoped, sandboxed functions with clear input/output — this is where "the agent writes its own code" lives, kept narrow (new skills, not open-ended edits to its own core reasoning loop, which is a much harder thing to keep debuggable).
- **Versioned:** improving a skill keeps the prior version rather than overwriting, so a regression is a rollback, not a rebuild.
- **Error-recovery skills, not just task skills:** a skill for "post a video" pairs with a skill for "what to do if the upload fails partway" — this is a meaningful chunk of what separates something demo-reliable from something actually trustworthy.
- **"Teach me" capture mode:** the user demonstrates a task once, narrating while JAR watches (screen + voice), and JAR converts the demonstration into a new skill definition — a much lower-friction way to expand capability week to week than writing skills from scratch.

### 9.3 Tool / MCP Registry
- Third-party skills and MCP servers are sandboxed by default rather than trusted automatically — a meaningful share of publicly shared MCP skills in the wild have had real security issues, and compromised OAuth tokens tied to MCP integrations are a genuine "keys to the kingdom" risk given JAR's level of access. Credential storage (email tokens, API keys) is the single highest-value thing to protect in this system and should be treated accordingly even in an otherwise low-friction, full-access-leaning setup.

---

## 10. Ambient / Proactive Behaviors

- **Pattern noticing, suggestion-only:** JAR observes recurring workflows (same files opened each morning, etc.) and proactively suggests turning them into a named routine/skill, rather than acting unprompted — low-risk because it's a suggestion, not an autonomous action.
- **Calendar/inbox ambient awareness:** proactively surfaces relevant context ahead of a known event ("want your notes for the 2pm pulled up") without needing to be asked each time.
- **Task takeover ("take over for me"):** reads recent World-State history (recent app/window activity, in-progress task context) to pick up exactly where the user left off, rather than starting cold — this is the direct payoff of maintaining the World-State Tracker continuously rather than only on-demand.
- **Cross-device status nudge:** if a phone is available, a lightweight notification can surface JAR's status (e.g., "waiting on you for a captcha") so the user isn't tied to watching the laptop screen to know it needs them.

---

## 11. Startup & Runtime

- JAR launches automatically on laptop startup, runs as a persistent background process/service, with the overlay layer mounting on top of the desktop session.
- Given the free-tools/low-footprint priority: keep local compute usage centered on the always-on wake-word listener (lightweight by design) and the overlay UI; push heavier inference (vision-model fallback calls, STT for longer commands, speaker verification) to free-tier cloud endpoints where reasonable, keeping the persistent local footprint small.

---

## 12. Build Priority (Recommended Sequence)

Given everything above, the recommended build order — reliability-first, visuals second, so the impressive parts have something solid to sit on:

1. **Perception layer core:** accessibility-tree reader + vision/OCR fallback.
2. **Verification-gated action loop (§4.4):** the single highest-leverage piece for making anything trustworthy.
3. **World-State Tracker (§5.5):** unlocks coherent long tasks and the "take over" feature.
4. **One real end-to-end skill**, proven reliable across many repeated runs, before adding breadth.
5. **Voice layer:** wake-word + speaker verification + basic STT/TTS.
6. **Orb + core visual states** (idle/listening/speaking/working/blocked) — the minimum visual language.
7. **Reasoning refinements:** hypothesis generation, critic pass, confidence scoring.
8. **Memory tiers + skill library + "teach me" capture.**
9. **Remaining visual polish:** anticipatory motion, mouse-dot trail effects, constellation view, environmental reactivity, sound design.
10. **Permissions/full-access toggle + CAPTCHA handoff pattern** — straightforward to add once the core loop and visual states exist.

---

## 13. Explicit Out-of-Scope

- Solving real CAPTCHAs programmatically.
- Impersonating the user to a third party without that party's knowledge (interview answering, undisclosed demo operation, or speaking/acting as the user in a meeting where the counterpart isn't aware an agent is involved).
- Continuous, always-on camera/microphone transcription running by default (both are on-demand/task-scoped, per §3).
