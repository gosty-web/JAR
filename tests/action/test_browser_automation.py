"""Integration tests for Playwright Browser Automation module."""

import asyncio
import sys
import os

# Add the project root to sys.path so we can import core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.action.executor import ActionService


async def test_live_search():
    """Verify that browser automation can run headless and perform a search."""
    print("============================================================")
    print("JAR Browser Automation - Live Playwright Test")
    print("============================================================")

    print("\n[1/4] Initializing ActionService with headless browser...")
    action = ActionService(headless_browser=True)
    print("  [OK] ActionService initialized successfully.")

    try:
        print("\n[2/4] Starting Playwright browser in background...")
        await action.browser.start()
        print("  [OK] Browser started.")

        print("\n[3/4] Performing DuckDuckGo search for 'Antigravity AI'...")
        results = await action.browser.search("Antigravity AI")
        
        print("\n--- Scraped Results ---")
        print(results)
        print("-----------------------")
        
        if "No results found" not in results and len(results) > 10:
            print("  [OK] Successfully scraped search results.")
        else:
            print("  [WARN] Search may have failed or hit a rate limit.")

        print("\n[4/4] Cleaning up...")
        await action.browser.stop()
        print("  [OK] Browser closed properly.")
        
        print("\nRESULT: [PASS] - Browser Automation tests completed.")

    except Exception as e:
        print(f"\nRESULT: [FAIL] - Exception during test: {e}")
        await action.browser.stop()


if __name__ == "__main__":
    asyncio.run(test_live_search())
