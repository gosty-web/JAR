"""Skill Sandbox for executing generalized LLM-generated Python scripts."""

import logging
from typing import Dict, Any, Callable
from core.memory.long_term import LongTermMemoryClient

logger = logging.getLogger(__name__)

class SkillSandbox:
    """Executes skills fetched from Supabase in a restricted globals() environment."""

    def __init__(self, ltm_client: LongTermMemoryClient, allowed_actions: Dict[str, Callable] = None):
        """Initialize the sandbox.
        
        Args:
            ltm_client: The Supabase long-term memory client.
            allowed_actions: A dictionary mapping action names to safe functions 
                             (e.g., {"mouse_click": browser.click}).
        """
        self.ltm_client = ltm_client
        self.allowed_actions = allowed_actions or {}

    async def execute_skill(self, skill_name: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """Fetch and execute a skill by name.
        
        Args:
            skill_name: The name of the skill to fetch from Supabase.
            args: Runtime arguments to pass to the skill.
        """
        args = args or {}
        skill_data = await self.ltm_client.get_skill(skill_name)
        if not skill_data:
            return {"status": "error", "message": f"Skill '{skill_name}' not found in Supabase."}

        script = skill_data.get("script_content", "")
        if not script:
            return {"status": "error", "message": f"Skill '{skill_name}' has empty script content."}

        # Restrict the environment
        # We explicitly inject allowed actions into the global namespace
        # and prevent access to __builtins__ except for basic types/functions.
        safe_builtins = {
            "print": print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "list": list,
            "Exception": Exception
        }
        
        exec_globals = {
            "__builtins__": safe_builtins,
            "args": args
        }
        # Inject allowed action primitives
        exec_globals.update(self.allowed_actions)
        
        # Local state to capture outputs defined in the script
        exec_locals = {}

        try:
            logger.info(f"Executing skill '{skill_name}' version {skill_data.get('version', 1)}...")
            # Run the python script. It is expected to define a 'result' variable.
            exec(script, exec_globals, exec_locals)
            
            result = exec_locals.get("result", {})
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error executing skill '{skill_name}': {e}")
            return {"status": "error", "message": str(e)}
