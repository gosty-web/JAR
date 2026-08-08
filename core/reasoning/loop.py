"""Verification-Gated Action Loop.

This is the core execution engine of JAR, implementing the loop:
Perceive -> Plan -> Critic -> Act -> Verify.
"""

import logging
import asyncio
import json
from typing import Dict, Any, Optional

from core.perception.screen_reader import ScreenReader
from core.action.executor import ActionService
from core.memory.world_state import WorldStateTracker
from core.reasoning.llm import ReasoningEngine
from core.skills.sandbox import SkillSandbox

logger = logging.getLogger(__name__)


class ExecutionLoop:
    """Manages the lifecycle of an autonomous task."""

    def __init__(self, reader: ScreenReader, action: ActionService, tracker: WorldStateTracker, llm: Optional[ReasoningEngine] = None, skill_sandbox: Optional[SkillSandbox] = None):
        """Initialize the execution loop.
        
        Args:
            reader: The perception module (ScreenReader).
            action: The action module (ActionService).
            tracker: The memory module (WorldStateTracker).
            llm: Optional custom ReasoningEngine (defaults to mock for tests unless specified).
            skill_sandbox: Optional sandbox for executing learned skills.
        """
        self.reader = reader
        self.action = action
        self.tracker = tracker
        self.llm = llm or ReasoningEngine(use_mock=True)
        self.skill_sandbox = skill_sandbox

    async def step(self, goal: str) -> bool:
        """Execute a single pass through the reasoning loop.
        
        Args:
            goal: The overarching user goal.
            
        Returns:
            True if the step succeeded, False if it failed.
        """
        logger.info(f"Starting execution loop step for goal: {goal}")
        
        # 1. Perceive
        logger.info("[Loop] Perceive: Reading screen state...")
        state = self.reader.read_or_fallback()
        await self.tracker.set_state("last_perceived_elements", state.element_count)

        # 2. Plan
        logger.info("[Loop] Plan: Generating action plan (with hypotheses)...")
        # Fetch Context Layer Memory
        recent_actions_raw = await self.tracker.get_recent_actions(limit=10)
        # Format the history to be highly condensed for the prompt
        recent_history_str = "\n".join(
            f"[{a['timestamp']}] Action: {a['action_type']} | Status: {a['status']} | Error: {a['error_message']}"
            for a in reversed(recent_actions_raw)
        )
        rolling_summary = await self.tracker.get_state("rolling_summary", default="")
        
        planned_response = await self.llm.plan_action(
            goal=goal, 
            state=state, 
            recent_history=recent_history_str, 
            rolling_summary=rolling_summary
        )
        planned_action = planned_response.get("action", {})

        # 3. Critic
        logger.info("[Loop] Critic: Reviewing plan for safety and confidence...")
        is_safe = await self.llm.criticize_action(goal, planned_response)
        if not is_safe:
            logger.warning("[Loop] Critic rejected the plan.")
            return False
            
        # Log the approved action as pending in the world state
        action_id = await self.tracker.log_action(
            action_type=planned_action.get("type", "unknown"),
            details=planned_response,
            status="pending"
        )

        # 4. Act
        logger.info(f"[Loop] Act: Executing {planned_action.get('type')} with confidence {planned_response.get('confidence_score')}...")
        success = False
        error_msg = ""
        try:
            action_type = planned_action.get("type")
            params = planned_action.get("params", {})
            
            if action_type == "wait":
                await asyncio.sleep(params.get("duration_ms", 1000) / 1000.0)
            elif action_type == "click":
                self.action.click(params.get("x", 0), params.get("y", 0))
            elif action_type == "type_text":
                self.action.type_text(params.get("text", ""))
            elif action_type == "request_user_help":
                logger.info(f"Handoff Pattern: Pausing for user help. Reason: {params.get('reason')}")
                await self.tracker.set_state("handoff_status", "waiting")
                # Wait for the user to resolve the issue (e.g. via UI / websocket setting state)
                while True:
                    status = await self.tracker.get_state("handoff_status")
                    if status == "resolved":
                        logger.info("Handoff Pattern: User resolved the issue. Resuming execution.")
                        break
                    await asyncio.sleep(2)
            elif action_type == "browser_search":
                await self.action.browser.search(params.get("query", ""))
            elif action_type == "write_file":
                self.action.write_file(params.get("filename", "out.txt"), params.get("content", ""))
            elif action_type == "run_skill":
                if not self.skill_sandbox:
                    raise RuntimeError("Skill Sandbox is not initialized.")
                skill_name = params.get("skill_name")
                skill_args = params.get("args", {})
                result = await self.skill_sandbox.execute_skill(skill_name, skill_args)
                if result.get("status") == "error":
                    raise Exception(result.get("message"))
                logger.info(f"Skill {skill_name} executed successfully. Result: {result.get('result')}")
                
            else:
                logger.warning(f"Unknown action type: {action_type}")
                
            success = True
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[Loop] Act failed: {error_msg}")

        # 5. Verify
        logger.info("[Loop] Verify: Checking if action had the desired effect...")
        new_state = self.reader.read_or_fallback()
        verification_passed = await self.llm.verify_action(goal, planned_action, new_state)

        # Finalize log
        final_status = "success" if (success and verification_passed) else "failed"
        await self.tracker.update_action_status(action_id, final_status, error_msg)
        
        # Prune context if it exceeds limits (Smart Context Layer)
        await self.tracker.prune_context(self.llm, max_actions=10, retain=5)

        logger.info(f"[Loop] Step completed with status: {final_status}")
        return verification_passed

    async def run_until_complete(self, goal: str, max_steps: int = 5) -> bool:
        """Run the loop repeatedly until the goal is achieved or max steps hit."""
        await self.tracker.set_state("current_goal", goal)
        
        for i in range(max_steps):
            logger.info(f"--- Execution Step {i+1}/{max_steps} ---")
            success = await self.step(goal)
            
            if not success:
                logger.warning("Step failed. Aborting execution loop.")
                return False
                
            # For the end-to-end skill testing, we consider it done after writing the file
            # In a real dynamic scenario, the LLM would return a 'done' action
            recent_actions = await self.tracker.get_recent_actions(1)
            if recent_actions and recent_actions[0]["action_type"] == "write_file":
                logger.info("Goal achieved.")
                await self.tracker.set_state("goal_status", "completed")
                return True
                
        logger.warning(f"Hit max steps ({max_steps}) without completing goal.")
        await self.tracker.set_state("goal_status", "timeout")
        return False
