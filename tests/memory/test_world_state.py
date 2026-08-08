import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.memory.world_state import WorldStateTracker

async def test_world_state():
    print("============================================================")
    print("JAR World-State Tracker - Integration Test")
    print("============================================================")

    db_path = ".test_jar_world_state.db"
    tracker = WorldStateTracker(db_path=db_path)
    
    print("\n[1/4] Initializing WorldStateTracker...")
    await tracker.initialize()
    print("  [OK] Initialized schema.")

    try:
        print("\n[2/4] Testing Key-Value State CRUD...")
        await tracker.set_state("active_window", {"title": "Google Chrome", "handle": 12345})
        state = await tracker.get_state("active_window")
        assert state["title"] == "Google Chrome", f"Expected 'Google Chrome', got {state.get('title')}"
        print("  [OK] State set and retrieved successfully.")

        print("\n[3/4] Testing Action Logging...")
        action_id = await tracker.log_action("click", {"x": 100, "y": 200}, status="pending")
        assert action_id > 0, "Action ID should be > 0"
        
        await tracker.update_action_status(action_id, status="success")
        
        recent = await tracker.get_recent_actions(limit=5)
        assert len(recent) == 1, "Should have 1 recent action"
        assert recent[0]["status"] == "success", "Status should have been updated to success"
        print("  [OK] Action logged and updated successfully.")

        print("\n[4/4] Testing State Clearance...")
        await tracker.clear_state()
        state = await tracker.get_state("active_window")
        assert state is None, "State should be None after clearing"
        
        recent = await tracker.get_recent_actions()
        assert len(recent) == 0, "Action log should be empty after clearing"
        print("  [OK] State cleared successfully.")

        print("\nRESULT: [PASS] - World-State Tracker tests completed.")

    except Exception as e:
        print(f"\nRESULT: [FAIL] - Exception during test: {e}")
        
    finally:
        await tracker.close()
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(test_world_state())
