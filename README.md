# Kanban

A lightweight, production-grade kanban management system for physical inventory tracking. Built for manufacturing environments using barcode scanners, physical locations, and Toyota-style kanban cards.

## Features

- **Barcode Scanning** — Zebra DataWedge integration via TCP socket and web keyboard-wedge
- **Toyota-Style Cards** — Printable kanban labels with QR codes via ZPL to networked Zebra printers
- **Event Tracking** — Signal, restock, and adjustment events with full history
- **Health Monitoring** — Dashboard with kanban health scores and cycle time analytics
- **Parts & Locations** — Full CRUD for parts inventory and storage locations
- **Inventory Management** — Stock level tracking, adjustments, and demand calculations
- **Reports** — Performance metrics, consumption trends, and CSV export
- **Mobile-First UI** — Responsive design with light/dark theme support

## Architecture

The codebase follows a layered architecture aligned with SOLID design principles:

```
Routes (thin controllers) → Services (business logic) → Repositories (data access)
```

- **Repositories** encapsulate all SQL — one per domain entity (kanban, event, part, location, inventory, setting)
- **Services** orchestrate business logic (scan processing, kanban lifecycle, inventory, dashboard, reports)
- **Routes** are thin HTTP handlers that delegate to services
- **Dependency injection** via request-scoped factories in `deps.py` using Quart's `g` object
- **Enums** (`EventType`, `InventoryStatus`) eliminate magic strings
- **Protocols** enable testable abstractions (e.g. `Printer` protocol for Zebra integration)

## Requirements

- Python 3.12+
- SQLite3

## Quick Start

```bash
# Clone and enter directory
git clone <repo-url>
cd kanban

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -e .

# Initialize database
quart --app kanban init-db

# Run development server
quart --app kanban run
```

The app will be available at `http://localhost:5000`.

## Production Deployment

### Using Uvicorn

```bash
pip install -e ".[prod]"
uvicorn --factory kanban:create_app --host 0.0.0.0 --port 8080
```

### Using Docker

```bash
docker build -t kanban .
docker run -p 8080:8080 -v kanban-data:/app/instance kanban
```

## Configuration

Create `instance/config.py` to override defaults:

```python
from secrets import token_hex

SECRET_KEY = f"{token_hex()}"
DATABASE = "/path/to/kanban.db"
```

## DataWedge Setup

The system supports two scanning modes:

### TCP Server (Recommended)
Configure DataWedge with **IP Output** pointing to the app host on port `58627`. The TCP server auto-starts on launch and processes scans server-side. Start/stop controls are available at `/settings`.

### Web Keyboard Wedge (Fallback)
Configure DataWedge with **Keystroke Output** and a carriage return suffix. The `/scan` page auto-focuses the input field and auto-submits on Enter.

## Workflow

1. **Create Parts** — Add parts with MPN, manufacturer, and lead times
2. **Create Locations** — Define physical storage locations
3. **Create Kanbans** — Link parts to locations with quantities and reorder points
4. **Print Cards** — Generate kanban labels with QR codes to Zebra printers
5. **Scan Events** — Signal replenishment, track restocks, log adjustments
6. **Monitor Health** — Review dashboard for cycle times and stockout alerts

## Project Structure

```
src/kanban/
├── __init__.py           # App factory
├── db.py                 # Database management
├── deps.py               # Dependency injection
├── enums.py              # EventType, InventoryStatus
├── protocols.py          # Printer protocol
├── datawedge.py          # DataWedge TCP server
├── zebra.py              # Zebra printer client
├── schema.sql            # SQLite schema
├── repositories/         # Data access layer (SQL)
├── services/             # Business logic layer
├── routes/               # HTTP route handlers
├── templates/            # Jinja2 HTML templates
└── utils/                # Pure helper functions & ZPL labels
```

## License

See [LICENSE](LICENSE) for details.
