"""Long-Term Memory and Skills Client backed by Supabase."""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
try:
    from supabase import create_client, Client
except ImportError:
    Client = Any

logger = logging.getLogger(__name__)

class LongTermMemoryClient:
    """Interacts with Supabase for persistent memory and skills."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """Initialize the Supabase client."""
        self.url = url or os.environ.get("SUPABASE_URL")
        self.key = key or os.environ.get("SUPABASE_KEY")
        
        self.client: Optional[Client] = None
        if self.url and self.key:
            try:
                # Type ignores because the import might fail dynamically
                self.client = create_client(self.url, self.key) # type: ignore
                logger.info("LongTermMemoryClient initialized with Supabase")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
        else:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not found. LongTermMemoryClient running in degraded/mock mode.")

    async def store_memory(self, category: str, content: str, relevance_score: float = 1.0) -> bool:
        """Store a generic memory or fact in long-term storage."""
        if not self.client:
            logger.warning(f"Mock storing memory [{category}]: {content}")
            return False
        
        try:
            data = {
                "category": category,
                "content": content,
                "relevance_score": relevance_score,
                "created_at": datetime.utcnow().isoformat()
            }
            response = self.client.table("long_term_memory").insert(data).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return False

    async def retrieve_memories(self, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent memories, optionally filtered by category."""
        if not self.client:
            return []
            
        try:
            query = self.client.table("long_term_memory").select("*")
            if category:
                query = query.eq("category", category)
            
            response = query.order("created_at", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []

    async def save_skill(self, name: str, description: str, script_content: str, version: int = 1) -> bool:
        """Save a new Python skill into the Supabase skill library."""
        if not self.client:
            logger.warning(f"Mock saving skill [{name}]")
            return False
            
        try:
            data = {
                "name": name,
                "description": description,
                "script_content": script_content,
                "version": version,
                "created_at": datetime.utcnow().isoformat()
            }
            # Upsert by name if conflict
            response = self.client.table("skills").upsert(data, on_conflict="name").execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error saving skill {name}: {e}")
            return False

    async def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Fetch a skill from Supabase by its unique name."""
        if not self.client:
            return None
            
        try:
            response = self.client.table("skills").select("*").eq("name", name).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error retrieving skill {name}: {e}")
            return None
