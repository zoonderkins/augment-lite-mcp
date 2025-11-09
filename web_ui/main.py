#!/usr/bin/env python3
"""
FastAPI Web UI for augment-lite MCP Server
Features: Real-time logs, configuration management, search testing
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import yaml

# Add parent directory to path to import augment-lite modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from utils.project_utils import get_project_status
    from memory.longterm import list_mem
except ImportError as e:
    print(f"Warning: Could not import augment-lite modules: {e}")
    print("Make sure you're running from the augment-lite-mcp root directory")
    # Provide fallback functions
    def get_project_status(project_name):
        return {"error": "Module not available"}
    def list_mem(project="auto"):
        return []

app = FastAPI(
    title="augment-lite Web UI",
    description="Real-time logs, configuration management, and search testing",
    version="0.7.0"
)

# Static files and templates
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# WebSocket connection manager for real-time logs
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass  # Client disconnected

manager = ConnectionManager()

# Log buffer for recent logs
log_buffer: List[dict] = []
MAX_LOG_BUFFER = 1000

def add_log(level: str, message: str, metadata: dict = None):
    """Add log entry and broadcast to WebSocket clients"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "metadata": metadata or {}
    }

    log_buffer.append(log_entry)
    if len(log_buffer) > MAX_LOG_BUFFER:
        log_buffer.pop(0)

    # Broadcast to all connected WebSocket clients
    asyncio.create_task(manager.broadcast(log_entry))

# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/projects")
async def list_projects():
    """List all indexed projects"""
    try:
        # Load projects.json directly
        projects_file = Path(__file__).parents[1] / "data" / "projects.json"

        if not projects_file.exists():
            return {"ok": True, "projects": [], "message": "No projects registered yet"}

        import json
        with open(projects_file, 'r') as f:
            projects = json.load(f)

        # Enrich with chunk counts
        result = []
        for name, info in projects.items():
            chunks_file = Path(__file__).parents[1] / "data" / f"chunks_{name}.jsonl"
            chunks_count = 0
            if chunks_file.exists():
                with open(chunks_file) as f:
                    chunks_count = sum(1 for _ in f)

            result.append({
                "name": name,
                "root": info.get("root", ""),
                "chunks": chunks_count,
                "created_at": info.get("created_at", "")
            })

        return {"ok": True, "projects": result}
    except Exception as e:
        import traceback
        print(f"Error in /api/projects: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

@app.get("/api/projects/{project_name}/status")
async def project_status(project_name: str):
    """Get detailed project status"""
    try:
        status = get_project_status(project_name)
        return {"ok": True, "status": status}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

@app.get("/api/memory")
async def get_memory():
    """Get all memory entries"""
    try:
        items = list_mem(project="auto")
        result = [{"key": k, "value": v, "updated_at": updated_at} for k, v, updated_at in items]
        return {"ok": True, "items": result, "count": len(result)}
    except Exception as e:
        import traceback
        print(f"Error in /api/memory: {e}")
        print(traceback.format_exc())
        return {"ok": True, "items": [], "count": 0, "error": str(e)}

@app.post("/api/search")
async def search_code(request: Request):
    """Test search functionality"""
    query = ""
    try:
        body = await request.json()
        query = body.get("query", "")
        k = body.get("k", 8)
        use_subagent = body.get("use_subagent", True)
        use_iterative = body.get("use_iterative", False)

        add_log("INFO", f"Search requested: {query}", {"k": k, "use_subagent": use_subagent})

        # Import search functions
        from retrieval.search import hybrid_search
        from retrieval.subagent_filter import hybrid_search_with_subagent
        from retrieval.iterative_search import iterative_search

        # Execute search
        if use_iterative:
            hits = iterative_search(query, k_per_iteration=k, use_subagent=use_subagent, project="auto")
        elif use_subagent:
            hits = hybrid_search_with_subagent(query, k=k, use_subagent=True, project="auto")
        else:
            hits = hybrid_search(query, k=k, project="auto")

        add_log("SUCCESS", f"Search completed: {len(hits)} results", {"query": query})

        return {"ok": True, "hits": hits, "count": len(hits)}
    except Exception as e:
        import traceback
        print(f"Error in /api/search: {e}")
        print(traceback.format_exc())
        add_log("ERROR", f"Search failed: {str(e)}", {"query": query})
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)}
        )

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    try:
        config_dir = Path(__file__).parents[1] / "config"

        # Load models.yaml
        models_config = {}
        if (config_dir / "models.yaml").exists():
            with open(config_dir / "models.yaml") as f:
                models_config = yaml.safe_load(f)

        # Load system_prompts.yaml
        prompts_config = {}
        if (config_dir / "system_prompts.yaml").exists():
            with open(config_dir / "system_prompts.yaml") as f:
                prompts_config = yaml.safe_load(f)

        return {
            "ok": True,
            "config": {
                "models": models_config,
                "system_prompts": prompts_config
            }
        }
    except Exception as e:
        import traceback
        print(f"Error in /api/config: {e}")
        print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e), "config": {"models": {}, "system_prompts": {}}}
        )

@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get recent logs"""
    return {
        "ok": True,
        "logs": log_buffer[-limit:],
        "count": len(log_buffer)
    }

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming"""
    await manager.connect(websocket)

    try:
        # Send initial batch of recent logs
        await websocket.send_json({
            "type": "history",
            "logs": log_buffer[-100:]
        })

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        add_log("INFO", "WebSocket client disconnected")

@app.on_event("startup")
async def startup_event():
    """Log server startup"""
    add_log("INFO", "augment-lite Web UI started", {
        "version": "0.7.0",
        "port": 8080
    })

@app.on_event("shutdown")
async def shutdown_event():
    """Log server shutdown"""
    add_log("INFO", "augment-lite Web UI shutting down")

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting augment-lite Web UI on http://localhost:8080")
    print("📊 Dashboard: http://localhost:8080")
    print("🔍 API Docs: http://localhost:8080/docs")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        reload=True  # Enable auto-reload for development
    )
