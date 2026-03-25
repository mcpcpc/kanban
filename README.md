# Kanban

A lightweight, production-grade kanban management system for physical inventory tracking. Built for manufacturing environments using barcode scanners, physical bins, and Toyota-style kanban cards.

## Features

- **Barcode Scanning** — Zebra DataWedge integration with auto-focus and auto-submit
- **Toyota-Style Cards** — Printable kanban cards with Code128 barcodes
- **Event Tracking** — Signal, restock, stockout, and adjustment events
- **Health Monitoring** — Dashboard with kanban health scores and cycle time analytics
- **Parts & Bins** — Full CRUD for parts inventory and bin locations
- **Reports** — Performance metrics, consumption trends, and CSV export
- **Mobile-First UI** — Responsive design with light/dark theme support

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

For Zebra scanner integration:

1. Set output mode to **Keystroke**
2. Configure suffix as **Carriage Return** (Enter)
3. Disable prefix or configure in app settings

The scan interface auto-focuses and auto-submits on barcode input.

## Workflow

1. **Create Parts** — Add parts with MPN, manufacturer, and lead times
2. **Create Bins** — Define physical bin locations
3. **Create Kanbans** — Link parts to bins with quantities and reorder points
4. **Print Cards** — Generate Toyota-style kanban cards with barcodes
5. **Scan Events** — Signal replenishment, track restocks, log adjustments
6. **Monitor Health** — Review dashboard for cycle times and stockout alerts

## License

See [LICENSE](LICENSE) for details.
