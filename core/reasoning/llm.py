"""LLM Reasoning Module.

This module provides the intelligence for the Perception-Gated Action Loop.
It uses `litellm` to allow swapping between models (OpenAI, Anthropic, Groq).
"""

import json
import logging
from typing import Dict, Any, Optional, List
import litellm
import os

from core.perception.models import ScreenState

logger = logging.getLogger(__name__)

# Default model, can be overridden via env var
DEFAULT_MODEL = os.getenv("JAR_LLM_MODEL", "deepseek-v4-flash")
DEFAULT_BASE_URL = os.getenv("JAR_LLM_BASE_URL", None)
DEFAULT_API_KEY = os.getenv("JAR_LLM_API_KEY", None)


class ReasoningEngine:
    """Handles LLM calls for planning, criticizing, and verifying actions."""

    def __init__(self, model: str = DEFAULT_MODEL, use_mock: bool = False):
        """Initialize the reasoning engine.
        
        Args:
            model: The LLM provider/model string (e.g., 'deepseek-v4-flash').
            use_mock: If True, returns deterministic mock responses for testing.
        """
        self.model = model
        self.use_mock = use_mock
        self.api_base = DEFAULT_BASE_URL
        self.api_key = DEFAULT_API_KEY
        # Ensure litellm returns JSON where possible
        litellm.drop_params = True

    async def plan_action(self, goal: str, state: ScreenState, recent_history: str = "", rolling_summary: str = "") -> Dict[str, Any]:
        """Determine the next best action given the goal and current screen state.
        
        Args:
            goal: The user's overarching goal.
            state: The current ScreenState.
            recent_history: Formatted string of recent actions taken.
            rolling_summary: Formatted string of older summarized actions.
            
        Returns:
            A dictionary representing the action to take.
        """
        if self.use_mock:
            return {
                "hypotheses": [
                    {
                        "interpretation": "Mock interpretation 1",
                        "confidence": 0.95,
                        "action": {"type": "write_file", "params": {"filename": "summary.txt", "content": "Mocked screen summary."}}
                    }
                ],
                "selected_hypothesis_index": 0,
                "confidence_score": 0.95,
                "reasoning": "Mock plan generated for testing.",
                "action": {
                    "type": "write_file",
                    "params": {"filename": "summary.txt", "content": "Mocked screen summary."}
                }
            }

        screen_context = json.dumps(state.to_compact_dict(), indent=2)
        
        prompt = f"""You are JAR, an autonomous desktop agent.
Your current goal is: {goal}

# Context Memory
Rolling Summary of Past Actions: {rolling_summary if rolling_summary else "None"}
Recent Immediate Actions:
{recent_history if recent_history else "None"}

# Current Perception
Here is the current screen state (interactive elements):
```json
{screen_context}
```

Based on this, what is the single next action you must take?
Because user goals can be ambiguous, generate 2-3 candidate hypotheses for what the user means.
For each hypothesis, provide an interpretation, a confidence score (0.0 to 1.0), and the action you would take.
Then, select the highest confidence hypothesis and output its action as the final chosen action.

Available action types:
- "click" (params: {{"x": int, "y": int}})
- "type_text" (params: {{"text": str}})
- "browser_search" (params: {{"query": str}})
- "write_file" (params: {{"filename": str, "content": str}})
- "wait" (params: {{"duration_ms": int}})

Respond ONLY with a valid JSON object matching this schema:
{{
    "hypotheses": [
        {{
            "interpretation": "<what the user means>",
            "confidence": <float between 0.0 and 1.0>,
            "action": {{"type": "<action_type>", "params": {{ ... }}}}
        }}
    ],
    "selected_hypothesis_index": <int>,
    "confidence_score": <float between 0.0 and 1.0>,
    "reasoning": "<short explanation of why this hypothesis was chosen>",
    "action": {{
        "type": "<action_type>",
        "params": {{ ... }}
    }}
}}
"""

        try:
            response = await litellm.acompletion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM Plan failed: {e}")
            # Fallback to wait if LLM fails
            return {
                "hypotheses": [],
                "selected_hypothesis_index": -1,
                "confidence_score": 0.0,
                "reasoning": f"LLM error occurred: {str(e)}",
                "action": {
                    "type": "wait",
                    "params": {"duration_ms": 2000}
                }
            }

    async def criticize_action(self, goal: str, plan: Dict[str, Any]) -> bool:
        """Evaluate a plan for safety, alignment, and confidence before execution.
        
        Args:
            goal: The original goal.
            plan: The proposed plan dict (containing hypotheses, confidence, and action).
            
        Returns:
            True if the action is safe and confidence is sufficient, False otherwise.
        """
        if self.use_mock:
            return True

        prompt = f"""Goal: {goal}
Proposed Plan: {json.dumps(plan)}

Evaluate this plan. Is the selected action safe to execute?
Unsafe actions include formatting drives, deleting system files, or sending unapproved emails.
Additionally, if the action has irreversible side-effects AND the `confidence_score` is low (< 0.6), you must reject it.
Respond ONLY with a JSON object: {{"is_safe": true/false}}"""

        try:
            response = await litellm.acompletion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            return result.get("is_safe", False)
        except Exception as e:
            logger.error(f"LLM Critic failed: {e}")
            # Default to safe if critic fails, depending on strictness
            return False

    async def verify_action(self, goal: str, action: Dict[str, Any], new_state: ScreenState) -> bool:
        """Verify if the executed action achieved the expected outcome.
        
        Args:
            goal: The overall goal.
            action: The action that was just taken.
            new_state: The screen state AFTER the action was executed.
            
        Returns:
            True if the action succeeded, False if it failed or got stuck.
        """
        if self.use_mock:
            return True

        screen_context = json.dumps(new_state.to_compact_dict(), indent=2)
        
        prompt = f"""Goal: {goal}
Action Just Executed: {json.dumps(action)}

New Screen State:
```json
{screen_context}
```

Did the action succeed in advancing the goal? For example, if the action was a click, did the screen change expectedly? If it was 'write_file', you can assume success unless there's an error on screen.
Respond ONLY with a JSON object: {{"success": true/false}}"""

        try:
            response = await litellm.acompletion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            result = json.loads(content)
            return result.get("success", False)
        except Exception as e:
            logger.error(f"LLM Verify failed: {e}")
            return False

    async def synthesize_skill(self, name: str, desc: str, trace: List[Dict[str, Any]]) -> str:
        """Synthesize a sequence of recorded actions into a generalized Python script.
        
        Args:
            name: The name of the skill.
            desc: The description of the skill.
            trace: The list of recorded actions and their context.
            
        Returns:
            The raw python script content.
        """
        if self.use_mock:
            return f"# Mock skill synthesized for {name}\nresult = {{'success': True}}"

        trace_json = json.dumps(trace, indent=2)
        
        prompt = f"""You are an expert Python automation developer. You have just observed a human performing a series of actions on a UI to accomplish a task.
Your goal is to synthesize these raw recorded actions into a generalized, reusable Python script that can be executed in the SkillSandbox.

Skill Name: {name}
Description: {desc}

Action Trace:
{trace_json}

Rules for the script:
1. The script will run in an environment where basic primitives (e.g., click, type_text, write_file) are exposed via globals.
2. The script must accept runtime arguments via the `args` dictionary.
3. The script must set a variable named `result` with a dictionary containing the output (e.g., result = {{"success": True}}).
4. Output raw Python code only. Do not include markdown blocks or backticks.
"""
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.choices[0].message.content
            # Clean up markdown formatting if the LLM includes it
            if content.startswith("```python"):
                content = content[9:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            return content.strip()
        except Exception as e:
            logger.error(f"LLM Synthesize Skill failed: {e}")
            return f"# Error synthesizing skill: {str(e)}\nresult = {{'success': False}}"

    async def summarize_actions(self, actions: list) -> str:
        """Create a compact summary of a list of past actions for the rolling context.
        
        Args:
            actions: List of action dictionary logs.
            
        Returns:
            A short string summarizing the actions.
        """
        if self.use_mock:
            return "Mock summary of past actions."
            
        actions_str = json.dumps(actions, indent=2)
        prompt = f"""Summarize the following sequence of actions into a single, concise paragraph. Focus on what was attempted and whether it succeeded.
        
        Actions:
        {actions_str}
        
        Provide only the summary string."""
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                api_base=self.api_base,
                api_key=self.api_key,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM Summarize Actions failed: {e}")
            return "Failed to summarize past actions."

