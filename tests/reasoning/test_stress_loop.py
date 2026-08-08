"""Stress test for the Verification-Gated Action Loop.

This script runs the core reasoning loop 50 times using the mock LLM
and a stubbed ScreenReader. It verifies that the loop logic is 99% reliable
at executing the full Perceive -> Plan -> Critic -> Act -> Verify sequence
without structural crashes or state desyncs.
"""

import asyncio
import sys
import os
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.perception.models import ScreenState, UIElement, ControlType
from core.reasoning.loop import ExecutionLoop
from core.reasoning.llm import ReasoningEngine
from core.memory.world_state import WorldStateTracker

logging.basicConfig(level=logging.WARNING)

class MockScreenReader:
    def read_or_fallback(self, *args, **kwargs):
        # Return a static fake screen state
        el = UIElement(
            element_id=1, 
            control_type=ControlType.DOCUMENT, 
            name="Test Document", 
            value="Some text here"
        )
        return ScreenState(
            timestamp=0.0,
            active_window_title="Test Window",
            elements=[el],
            element_count=1
        )

class MockActionService:
    def __init__(self):
        self.browser = self
    
    async def search(self, query):
        pass
        
    def write_file(self, filename, content):
        pass
        
    def click(self, x, y):
        pass

async def run_stress_test(iterations: int = 50):
    print("============================================================")
    print(f"JAR Action Loop Stress Test - {iterations} Iterations")
    print("============================================================")
    
    reader = MockScreenReader()
    action = MockActionService()
    llm = ReasoningEngine(use_mock=True)
    
    success_count = 0
    failure_count = 0
    
    for i in range(iterations):
        db_path = f".test_stress_{i}.db"
        tracker = WorldStateTracker(db_path=db_path)
        await tracker.initialize()
        
        loop = ExecutionLoop(reader, action, tracker, llm)
        goal = "Write a summary file."
        
        try:
            # We expect the mock LLM to immediately return a 'write_file' action,
            # which the loop executes, and then verify passes.
            # This should complete in 1 step.
            success = await loop.run_until_complete(goal, max_steps=2)
            if success:
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            print(f"Iteration {i+1} crashed: {e}")
            failure_count += 1
        finally:
            await tracker.close()
            if os.path.exists(db_path):
                os.remove(db_path)
                
        if (i + 1) % 10 == 0:
            print(f"Completed {i+1}/{iterations} iterations...")
            
    print("\n--- Stress Test Results ---")
    print(f"Total Runs: {iterations}")
    print(f"Successes:  {success_count}")
    print(f"Failures:   {failure_count}")
    
    reliability = (success_count / iterations) * 100
    print(f"Reliability: {reliability:.1f}%")
    
    if reliability >= 99.0:
        print("\nRESULT: [PASS] - 99% Reliability achieved!")
    else:
        print("\nRESULT: [FAIL] - Did not meet 99% reliability threshold.")

if __name__ == "__main__":
    asyncio.run(run_stress_test(50))
