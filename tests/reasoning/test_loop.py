import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.perception.screen_reader import ScreenReader
from core.action.executor import ActionService
from core.memory.world_state import WorldStateTracker
from core.reasoning.loop import ExecutionLoop

logging.basicConfig(level=logging.INFO)

async def test_execution_loop():
    print("============================================================")
    print("JAR Verification-Gated Action Loop - Integration Test")
    print("============================================================")

    db_path = ".test_jar_loop_state.db"
    
    reader = ScreenReader()
    action = ActionService(headless_browser=True)
    tracker = WorldStateTracker(db_path=db_path)
    
    loop = ExecutionLoop(reader, action, tracker)

    try:
        print("\n[1/3] Initializing subsystems...")
        await tracker.initialize()
        # Ensure browser is ready if needed, though 'wait' doesn't need it.
        print("  [OK] Subsystems ready.")

        print("\n[2/3] Running Execution Loop for goal 'Test Goal'...")
        # Should execute one step (a stubbed 'wait' action) and return True
        success = await loop.run_until_complete("Test Goal", max_steps=2)
        assert success is True, "Loop run should have returned True"
        
        # Verify World State was updated
        recent_actions = await tracker.get_recent_actions()
        assert len(recent_actions) == 1, "Should have 1 logged action"
        assert recent_actions[0]["action_type"] == "write_file", "Action should be 'write_file'"
        assert recent_actions[0]["status"] == "success", "Status should be success"
        
        goal_status = await tracker.get_state("goal_status")
        assert goal_status == "completed", "Goal status should be completed"
        print("  [OK] Loop executed and World-State updated.")

        print("\n[3/3] Cleaning up...")
        await tracker.close()
        print("  [OK] DB closed.")
        
        print("\nRESULT: [PASS] - Execution Loop tests completed.")

    except Exception as e:
        print(f"\nRESULT: [FAIL] - Exception during test: {e}")
        
    finally:
        await tracker.close()
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(test_execution_loop())
