# augment-lite Web UI

**Real-time logs, configuration management, and search testing interface**

## Features

- **Real-time Log Streaming**: WebSocket-based live log viewer with automatic reconnection
- **Search Testing**: Interactive search interface with subagent filtering and iterative search options
- **Project Management**: View all indexed projects and their statistics
- **Memory Inspection**: Browse stored long-term memory entries
- **Configuration Viewer**: Inspect current models and system prompts configuration

## Installation

```bash
cd web_ui

# Install dependencies (locked versions)
uv pip install -e .

# For development dependencies
uv pip install -e ".[dev]"
```

## Running the Web UI

```bash
# From web_ui directory
python main.py

# Or use uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

The Web UI will be available at:
- **Dashboard**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs
- **API ReDoc**: http://localhost:8080/redoc

## API Endpoints

### Projects
- `GET /api/projects` - List all indexed projects
- `GET /api/projects/{name}/status` - Get detailed project status

### Search
- `POST /api/search` - Test search functionality
  ```json
  {
    "query": "authentication code",
    "k": 8,
    "use_subagent": true,
    "use_iterative": false
  }
  ```

### Memory
- `GET /api/memory` - Get all memory entries

### Configuration
- `GET /api/config` - Get current configuration (models + prompts)

### Logs
- `GET /api/logs?limit=100` - Get recent logs
- `WebSocket /ws/logs` - Real-time log streaming

## WebSocket Log Streaming

Connect to `ws://localhost:8080/ws/logs` for real-time logs:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/logs');

ws.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(`[${log.timestamp}] ${log.level}: ${log.message}`);
};
```

The WebSocket connection includes:
- Automatic reconnection with exponential backoff (1s → 30s)
- Initial log history (last 100 entries)
- Heartbeat to keep connection alive

## Development

### Project Structure

```
web_ui/
├── main.py              # FastAPI application
├── pyproject.toml       # Locked dependencies (uv)
├── routers/             # API route modules (future)
├── static/              # Static files (CSS, JS)
├── templates/           # Jinja2 HTML templates
│   └── dashboard.html
└── README.md
```

### Dependencies (Locked Versions)

- **FastAPI 0.121.1** - Latest as of 2025-11-09
- **Uvicorn 0.34.0** - ASGI server with WebSocket support
- **WebSockets 14.1** - WebSocket implementation
- **Jinja2 3.1.5** - Template engine
- **PyYAML 6.0.2** - Configuration parsing
- **Aiofiles 24.1.0** - Async file operations

### Testing

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Test with httpx
python -c "import httpx; print(httpx.get('http://localhost:8080/api/projects').json())"
```

## Integration with augment-lite MCP

The Web UI automatically imports augment-lite modules:

```python
from utils.project_utils import get_all_projects, get_project_status
from memory.longterm import list_mem
from retrieval.search import hybrid_search
from retrieval.subagent_filter import hybrid_search_with_subagent
from retrieval.iterative_search import iterative_search
```

Ensure the MCP server environment is properly configured before starting the Web UI.

## Comparison with acemcp Web UI

| Feature | acemcp | augment-lite | Status |
|---------|--------|--------------|--------|
| Real-time logs | ✅ WebSocket | ✅ WebSocket | ✅ Equal |
| Search testing | ✅ | ✅ | ✅ Equal |
| Auto-reconnect | ✅ 1-30s backoff | ✅ 1-30s backoff | ✅ Equal |
| Configuration UI | ✅ TOML editor | 🔄 View-only | 🚧 Planned |
| Index management | ✅ Web UI | ❌ CLI only | 🚧 Planned |
| Project switching | ✅ | ✅ | ✅ Equal |

## Future Enhancements

- [ ] Configuration editing (modify models.yaml via UI)
- [ ] Index rebuild trigger from UI
- [ ] Task management interface
- [ ] Memory CRUD operations
- [ ] Dark/Light theme toggle
- [ ] Export logs to file
- [ ] Search result visualization

## Version History

- **v0.7.0** (2025-11-09): Initial release with real-time logs and search testing
