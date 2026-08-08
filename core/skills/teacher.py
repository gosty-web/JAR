"""Teacher Mode for capturing human actions and synthesizing them into reusable skills."""

import logging
from typing import List, Dict, Any, Optional
from core.memory.long_term import LongTermMemoryClient
from core.reasoning.llm import ReasoningEngine

logger = logging.getLogger(__name__)

class SkillTeacher:
    """Listens to manual user UI actions, traces them, and synthesizes Python skills."""

    def __init__(self, llm_engine: ReasoningEngine, ltm_client: LongTermMemoryClient):
        self.llm_engine = llm_engine
        self.ltm_client = ltm_client
        self.is_teaching = False
        self.action_trace: List[Dict[str, Any]] = []

    def start_teaching(self):
        """Begin recording user actions."""
        self.is_teaching = True
        self.action_trace = []
        logger.info("Teach Me mode activated. Recording actions...")

    def record_action(self, action_type: str, details: Dict[str, Any], screen_state: Optional[Dict[str, Any]] = None):
        """Record an action during Teach Me mode."""
        if not self.is_teaching:
            return
            
        self.action_trace.append({
            "action": action_type,
            "details": details,
            "context": screen_state
        })
        logger.info(f"Recorded action: {action_type} - {details}")

    async def finish_teaching_and_save(self, skill_name: str, description: str) -> bool:
        """Synthesize the recorded trace into a skill script and save it to Supabase."""
        if not self.is_teaching:
            logger.warning("Not currently in Teach Me mode.")
            return False

        self.is_teaching = False
        logger.info(f"Finished teaching. Synthesizing skill '{skill_name}'...")

        if not self.action_trace:
            logger.warning("No actions recorded. Aborting skill synthesis.")
            return False

        # Use LLM to convert the trace to a python script
        try:
            script_content = await self.llm_engine.synthesize_skill(skill_name, description, self.action_trace)
            
            logger.info(f"Skill synthesized. Saving to long term memory.")
            success = await self.ltm_client.save_skill(skill_name, description, script_content)
            return success
        except Exception as e:
            logger.error(f"Error synthesizing skill: {e}")
            return False
