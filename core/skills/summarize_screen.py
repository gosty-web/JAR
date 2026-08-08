"""End-to-End Skill: Summarize Screen and Save to File."""

import asyncio
import sys
import os
import logging

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.perception.screen_reader import ScreenReader
from core.action.executor import ActionService
from core.memory.world_state import WorldStateTracker
from core.reasoning.loop import ExecutionLoop
from core.reasoning.llm import ReasoningEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_summarize_skill(use_mock_llm: bool = True):
    """Run the summarize screen skill.
    
    Args:
        use_mock_llm: If True, bypasses actual LLM API calls for testing.
    """
    logger.info("Starting Summarize Screen Skill...")
    
    db_path = ".jar_world_state.db"
    tracker = WorldStateTracker(db_path=db_path)
    
    reader = ScreenReader()
    action = ActionService(headless_browser=True)
    llm = ReasoningEngine(use_mock=use_mock_llm)
    
    loop = ExecutionLoop(reader, action, tracker, llm)
    
    await tracker.initialize()
    
    goal = "Read the current screen state, summarize what is visible, and save the summary to 'screen_summary.txt'."
    
    try:
        success = await loop.run_until_complete(goal, max_steps=5)
        if success:
            logger.info("Skill executed successfully!")
        else:
            logger.warning("Skill failed or timed out.")
    finally:
        await tracker.close()

if __name__ == "__main__":
    # By default, use the mock LLM so it runs cleanly without API keys.
    # To run with a real LLM, pass False or configure env vars.
    asyncio.run(run_summarize_skill(use_mock_llm=True))
