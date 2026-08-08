import asyncio
import logging
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from core.perception.screen_reader import ScreenReader
from core.action.executor import ActionService
from core.memory.world_state import WorldStateTracker
from core.reasoning.llm import ReasoningEngine
from core.reasoning.loop import ExecutionLoop

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("JAR_MAIN")

app = FastAPI(title="JAR Core System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
tracker: WorldStateTracker = None
reader: ScreenReader = None
action: ActionService = None
llm: ReasoningEngine = None
loop: ExecutionLoop = None

connected_websockets = []

@app.on_event("startup")
async def startup_event():
    global tracker, reader, action, llm, loop
    logger.info("Initializing JAR Core components...")
    
    tracker = WorldStateTracker(db_path="jar_world_state.db")
    await tracker.initialize()
    
    reader = ScreenReader()
    action = ActionService()
    llm = ReasoningEngine()
    
    loop = ExecutionLoop(
        reader=reader,
        action=action,
        tracker=tracker,
        llm=llm
    )
    
    logger.info("JAR Core initialized. Ready for connections.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down JAR Core...")
    if tracker:
        await tracker.close()

async def broadcast_state():
    """Continuously broadcast world state to all connected frontends."""
    while True:
        if connected_websockets and tracker:
            # Gather state
            handoff = await tracker.get_state("handoff_status")
            status = await tracker.get_state("goal_status")
            
            # Map backend states to frontend Orb states
            orb_state = "idle"
            if handoff == "waiting":
                orb_state = "blocked"
            elif status == "running":
                orb_state = "working"
            
            # We can also fetch the most recent pending or running action for thought/confidence
            recent_actions = await tracker.get_recent_actions(1)
            thought = ""
            confidence = 0
            if recent_actions:
                last_action = recent_actions[0]
                details = last_action.get("details", {})
                thought = details.get("hypothesis", "") or details.get("reasoning", "")
                confidence = details.get("confidence_score", 0)
                
                # If we are currently "acting", orb is working
                if last_action["status"] == "pending":
                    orb_state = "working"

            payload = {
                "orbState": orb_state,
                "thought": thought,
                "confidence": confidence,
                "fullAccess": False # To be synced with frontend toggles later
            }
            
            disconnected = []
            for ws in connected_websockets:
                try:
                    await ws.send_json(payload)
                except Exception:
                    disconnected.append(ws)
            
            for ws in disconnected:
                connected_websockets.remove(ws)
                
        await asyncio.sleep(0.5) # 2 FPS updates to UI

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_websockets.append(websocket)
    
    # Start the broadcast task if it's the first connection
    if len(connected_websockets) == 1:
        asyncio.create_task(broadcast_state())
        
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # Handle commands from the frontend
            cmd = payload.get("command")
            if cmd == "start_task":
                goal = payload.get("goal", "Do something useful.")
                logger.info(f"Received start_task command: {goal}")
                await tracker.set_state("goal_status", "running")
                # Fire and forget the loop task
                asyncio.create_task(loop.run_until_complete(goal, max_steps=20))
                
            elif cmd == "resolve_handoff":
                logger.info("User resolved handoff via UI.")
                await tracker.set_state("handoff_status", "resolved")
                
    except WebSocketDisconnect:
        connected_websockets.remove(websocket)
        
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("JAR_WS_PORT", 8000))
    logger.info(f"Starting API server on port {port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
