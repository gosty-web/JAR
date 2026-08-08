"""World-State Tracker using a local SQLite database.

This module provides an ephemeral database to track the current execution state,
pending approvals, and recent failures, allowing the reasoning loop to maintain
context across long-running tasks without blooming the LLM prompt.
"""

import aiosqlite
import logging
import os
import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

from datetime import datetime

if TYPE_CHECKING:
    from core.memory.long_term import LongTermMemoryClient
    from core.reasoning.llm import ReasoningEngine

logger = logging.getLogger(__name__)


class WorldStateTracker:
    """Tracks JAR's execution state and history in a local SQLite DB."""

    def __init__(self, db_path: str = ".jar_world_state.db", ltm_client: Optional['LongTermMemoryClient'] = None):
        """Initialize the World-State Tracker.
        
        Args:
            db_path: Path to the SQLite database file.
            ltm_client: Optional LongTermMemoryClient for flushing long-term facts.
        """
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self.ltm_client = ltm_client

    async def initialize(self) -> None:
        """Connect to the database and ensure schemas exist."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        # Create tables
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS action_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP,
                action_type TEXT,
                details TEXT,
                status TEXT,
                error_message TEXT
            );
        """)
        await self._conn.commit()
        logger.info(f"WorldStateTracker initialized at {self.db_path}")

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("WorldStateTracker closed")

    async def set_state(self, key: str, value: Any) -> None:
        """Store a generic state value (JSON serialized)."""
        if not self._conn:
            raise RuntimeError("WorldStateTracker not initialized")

        value_str = json.dumps(value)
        now = datetime.utcnow().isoformat()
        
        await self._conn.execute(
            """
            INSERT INTO state (key, value, updated_at) 
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET 
                value = excluded.value, 
                updated_at = excluded.updated_at
            """,
            (key, value_str, now)
        )
        await self._conn.commit()

    async def get_state(self, key: str, default: Any = None) -> Any:
        """Retrieve a state value by key."""
        if not self._conn:
            raise RuntimeError("WorldStateTracker not initialized")

        async with self._conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return json.loads(row["value"])
            return default

    async def clear_state(self) -> None:
        """Clear all ephemeral state."""
        if not self._conn:
            raise RuntimeError("WorldStateTracker not initialized")
            
        await self._conn.execute("DELETE FROM state")
        await self._conn.execute("DELETE FROM action_log")
        await self._conn.commit()

    async def log_action(self, action_type: str, details: Dict[str, Any], status: str = "pending", error_message: str = "") -> int:
        """Log an action in the execution loop.
        
        Returns:
            The inserted row ID.
        """
        if not self._conn:
            raise RuntimeError("WorldStateTracker not initialized")

        now = datetime.utcnow().isoformat()
        details_str = json.dumps(details)

        async with self._conn.execute(
            """
            INSERT INTO action_log (timestamp, action_type, details, status, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (now, action_type, details_str, status, error_message)
        ) as cursor:
            action_id = cursor.lastrowid
            
        await self._conn.commit()
        return action_id or 0

    async def update_action_status(self, action_id: int, status: str, error_message: str = "", flush_to_ltm: bool = False) -> None:
        """Update the status of a logged action (e.g., success or failure)."""
        if not self._conn:
            raise RuntimeError("WorldStateTracker not initialized")

        await self._conn.execute(
            """
            UPDATE action_log 
            SET status = ?, error_message = ?
            WHERE id = ?
            """,
            (status, error_message, action_id)
        )
        await self._conn.commit()

        if flush_to_ltm and self.ltm_client and status == "success":
            # Retrieve the action details to flush
            async with self._conn.execute("SELECT action_type, details FROM action_log WHERE id = ?", (action_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    content = f"Action: {row['action_type']} | Details: {row['details']}"
                    await self.ltm_client.store_memory(category="task_summary", content=content, relevance_score=0.8)

    async def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the most recent actions logged."""
        if not self._conn:
            raise RuntimeError("WorldStateTracker not initialized")

        async with self._conn.execute(
            """
            SELECT id, timestamp, action_type, details, status, error_message 
            FROM action_log 
            ORDER BY timestamp DESC LIMIT ?
            """,
            (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "action_type": row["action_type"],
                "details": json.loads(row["details"]),
                "status": row["status"],
                "error_message": row["error_message"]
            })
        return results

    async def prune_context(self, llm: 'ReasoningEngine', max_actions: int = 10, retain: int = 5) -> None:
        """Prune the action log to prevent context bloat.
        
        If the number of actions exceeds `max_actions`, it takes the oldest actions 
        (all except the `retain` most recent), summarizes them using the LLM, 
        appends the summary to a rolling context, and deletes them from the DB.
        
        Args:
            llm: The ReasoningEngine to use for summarization.
            max_actions: The maximum number of raw actions to keep before pruning.
            retain: The number of most recent actions to retain untouched.
        """
        if not self._conn:
            raise RuntimeError("WorldStateTracker not initialized")
            
        async with self._conn.execute("SELECT COUNT(*) as count FROM action_log") as cursor:
            row = await cursor.fetchone()
            count = row["count"] if row else 0
            
        if count > max_actions:
            # We need to prune (count - retain) items, which are the oldest ones.
            limit = count - retain
            
            async with self._conn.execute(
                "SELECT * FROM action_log ORDER BY timestamp ASC LIMIT ?", (limit,)
            ) as cursor:
                old_rows = await cursor.fetchall()
                
            if not old_rows:
                return
                
            # Extract basic dicts for summarization
            old_actions = []
            ids_to_delete = []
            for r in old_rows:
                ids_to_delete.append(r["id"])
                old_actions.append({
                    "action_type": r["action_type"],
                    "status": r["status"],
                    "error_message": r["error_message"],
                    "details": json.loads(r["details"])
                })
                
            # Ask LLM to summarize
            logger.info(f"Context pruning: Summarizing {len(old_actions)} oldest actions.")
            summary_piece = await llm.summarize_actions(old_actions)
            
            # Append to rolling summary
            current_summary = await self.get_state("rolling_summary", default="")
            new_summary = f"{current_summary}\n- {summary_piece}".strip()
            await self.set_state("rolling_summary", new_summary)
            
            # Delete old rows
            placeholders = ",".join(["?"] * len(ids_to_delete))
            await self._conn.execute(
                f"DELETE FROM action_log WHERE id IN ({placeholders})", ids_to_delete
            )
            await self._conn.commit()
            logger.info("Context pruning complete.")
