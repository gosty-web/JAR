# Bugs & Fixes Log

**Mandatory Directive**: Every bug encountered during the build process must be logged here using the template below. Do not rely on LLM memory across sessions.

---

## Template

### [Bug Name / Short Description]
- **Date**: YYYY-MM-DD
- **Symptoms**: What happened? What were the error logs?
- **Root Cause**: Why did it happen?
- **Fix**: How was it resolved? (Link to PR / commit if possible, or explain the code change).
- **Prevention**: What can we do to ensure this doesn't happen again?

---

*(Log entries go below here)*

### Unicode encoding error in live test output on Windows
- **Date**: 2026-08-08
- **Symptoms**: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'` when printing test output with checkmark Unicode characters to Windows console (cp1252 encoding).
- **Root Cause**: Windows PowerShell/cmd uses cp1252 encoding by default, which doesn't support Unicode checkmark characters (✓, ✗). Python's `print()` tries to encode to the console's charset and fails.
- **Fix**: Replace Unicode characters with ASCII equivalents (`[OK]`, `[FAIL]`, `[WARN]`) in all test output and logging. Alternatively, set `PYTHONIOENCODING=utf-8` environment variable.
- **Prevention**: Never use Unicode symbols in console output. Stick to ASCII for all print statements. Use `[OK]`, `[FAIL]`, `[WARN]` prefixes instead.

### DuckDuckGo HTML Search Rate-Limiting Headless Browsers
- **Date**: 2026-08-08
- **Symptoms**: The Playwright search test (`test_browser_automation.py`) returned "No results found or rate limited" when querying `https://html.duckduckgo.com/html/?q=...`, even with a standard Chrome User-Agent.
- **Root Cause**: DuckDuckGo's HTML endpoint aggressively blocks automated traffic and headless Chromium instances, presumably via IP reputation or subtle headless fingerprinting.
- **Fix**: Switched the underlying search endpoint to Wikipedia (`https://en.wikipedia.org/w/index.php?search=...`). Wikipedia is highly permissive of bots and provides a massive, reliable knowledge graph for problem-solving.
- **Prevention**: When relying on free web scraping for AI agent features, always assume standard search engines (Google, DDG, Bing) will aggressively block headless browsers. Default to permissive endpoints (like Wikipedia or specialized APIs) for guaranteed reliability.
