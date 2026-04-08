# Production Kanban Management System - PRD

## Overview

A lightweight, production-grade kanban management system designed for physical inventory tracking using Zebra barcode scanners (via DataWedge TCP and web-based scanning), physical bins, and kanban cards. The system prioritizes ease of use for 1-2 operators while providing comprehensive performance analytics and direct Zebra label printer integration.

---

## Problem Statement

Production environments need a simple, reliable way to:
- Track physical kanban card movements via barcode scanning
- Monitor inventory health across multiple bin locations
- Analyze kanban cycle times and replenishment performance
- Operate seamlessly across mobile scanners and desktop workstations
- Print kanban labels directly to Zebra label printers

---

## Success Metrics

| Metric | Target |
|--------|--------|
| **Ease of Use** | Single-scan operations for common tasks; < 3 clicks for any action |
| **DataWedge Integration** | Dual-mode: TCP server for direct scanner input + web UI keyboard-wedge scanning |
| **Analytics** | Track cycle times, stockout frequency, and kanban health scores |
| **Label Printing** | Direct ZPL output to networked Zebra printers with QR codes |

---

## Technical Constraints

- **Framework**: Quart (async Python web framework)
- **Database**: SQLite3
- **Dependencies**: No external libraries beyond Quart (uvicorn optional for production)
- **Package Management**: PIP via pyproject.toml
- **Python Version**: 3.12+
- **Label Format**: Zebra ZPL (sent via TCP to Zebra printers)
- **DataWedge Protocol**: TCP socket server on port 58627

---

## User Personas

### Operator (Primary)
- Uses handheld Zebra scanner with DataWedge
- Needs fast, one-scan workflows
- Works on mobile device or fixed terminal

### Supervisor (Secondary)
- Reviews kanban health and performance dashboards
- Manages parts, bins, and kanban configurations
- Works primarily on desktop

---

## Functional Requirements

### FR-1: Core Entities Management

#### FR-1.1: Parts Management
- Create, read, update, delete (CRUD) parts
- Fields: part number (MPN), manufacturer, description, category, datasheet URL, unit of measure, reorder lead time
- Search and filter by part number, manufacturer, category

#### FR-1.2: Bins Management
- CRUD operations for physical bin locations
- Fields: location code, description, color
- Visual bin status indicator (healthy/warning/critical)

#### FR-1.3: Kanban Management
- CRUD operations for kanban cards
- Fields: part, bin, kanban quantity, safety lead time days, estimated daily demand, number of cards, active status
- Reorder point calculated dynamically from `safety_lead_time_days × estimated_daily_demand`
- Print kanban labels with QR codes directly to Zebra printers via ZPL

#### FR-1.4: Units of Measure
- Pre-seeded list (each, kg, g, m, cm, mm, L, mL, ft, in)
- Read-only display; admin can add new units

#### FR-1.5: Inventory Management
- Track current stock levels per part (quantity on hand)
- Inventory adjustment with notes
- Demand calculation and reporting
- CSV export of inventory data

#### FR-1.6: Settings Management
- Zebra printer configuration (hostname, port, timeout)
- DataWedge TCP server start/stop controls
- Application-level configuration persistence

### FR-2: Barcode Scanning & DataWedge Integration

#### FR-2.1: TCP Server Mode (DataWedge Direct)
- Async TCP server listening on configurable host/port (default `0.0.0.0:58627`)
- Auto-starts on application launch
- Receives barcode data as newline-terminated strings over TCP
- Parses kanban IDs from barcodes (supports `K<id>` prefix or plain numeric)
- Records signal events and adjusts inventory automatically
- Start/stop controls via settings page

#### FR-2.2: Web Scan Mode
- Quick scan interface with auto-focus input field
- Accept keyboard-wedge input (DataWedge keystroke output)
- Auto-submit on carriage return
- Dedicated scanning page with large input field at `/scan`

#### FR-2.3: Scan Actions
- **Signal Scan**: Record kanban card pull (replenishment signal) and decrement inventory
- **Restock Start**: Begin restocking process
- **Restock Complete**: Complete restocking with quantity entry
- **Quick Scan Mode**: Dedicated scanning page at `/scan`

#### FR-2.4: Label Generation & Printing
- ZPL-based label templates for Zebra label printers
- QR code (BQN) encoding kanban ID as `K<id>` format
- Labels include: QR code, kanban ID, bin location, part number, manufacturer, description, quantity, reorder point, card number
- Direct TCP printing to networked Zebra printers via `utils/zebra.py`

### FR-3: Event Tracking

#### FR-3.1: Event Types
- `signal` - Replenishment triggered
- `restock_start` - Restocking begun
- `restock_complete` - Restocking finished (with quantity)
- `adjustment` - Manual inventory adjustment (with quantity)

#### FR-3.2: Event Recording
- Automatic timestamp on all events
- Optional notes field for context
- Quantity field for restock/adjustment events

#### FR-3.3: Event History
- View event history with filtering
- Filter by event type, date range
- CSV export capability

### FR-4: Analytics & Health Monitoring

#### FR-4.1: Dashboard
- System health overview (total kanbans, active signals, pending restocks)
- Recent activity feed
- Health distribution chart (healthy/warning/critical)

#### FR-4.2: Kanban Health Score
- Based on: cycle time consistency, stockout frequency, reorder compliance
- Visual indicators: green (healthy), yellow (warning), red (critical)

#### FR-4.3: Performance Metrics
- Average cycle time (signal to restock complete)
- Stockout rate per kanban
- Reorder point accuracy
- Trend analysis over configurable time periods
- Suggested reorder point calculation via API

#### FR-4.4: Reports
- Kanban performance summary
- Part consumption trends
- Bin utilization analysis

### FR-5: User Interface

#### FR-5.1: Responsive Design
- Mobile-first approach
- Fluid grid layout adapting from 320px to 1920px+
- Touch-friendly controls (min 44px tap targets)

#### FR-5.2: Theme Support
- Light and dark themes
- User preference persisted in localStorage
- System preference detection (prefers-color-scheme)

#### FR-5.3: Navigation
- Hamburger menu on mobile
- Sidebar navigation on desktop
- Breadcrumb trail for deep pages

#### FR-5.4: Icons
- Dual-tone SVG icons (embedded inline in base template)
- No emoji usage
- Consistent icon set throughout

#### FR-5.5: Accessibility
- ARIA labels on interactive elements
- Keyboard navigation support
- High contrast mode compatibility

#### FR-5.6: Help Page
- In-app documentation and user guide at `/help`

---

## Non-Functional Requirements

### NFR-1: Performance
- Page load < 500ms on local network
- Scan-to-action feedback < 100ms
- Support 10,000+ kanban events without degradation

### NFR-2: Reliability
- Graceful degradation on network issues
- Transaction safety for all database writes
- Data validation on all inputs

### NFR-3: Security
- CSRF protection on all forms
- Input sanitization
- No sensitive data in URLs
- SECRET_KEY should be overridden from default via instance config in production

### NFR-4: Maintainability
- Clean separation of routes, templates, utilities
- Documented API endpoints
- Schema migrations via `init-db` CLI command

---

## Architecture

```
src/kanban/
├── __init__.py           # App factory, version, configuration
├── datawedge.py          # DataWedge TCP server (async socket handler)
├── db.py                 # Database connection management, CLI commands
├── schema.sql            # SQLite schema with seed data
├── routes/
│   ├── __init__.py       # Blueprint registration
│   ├── api.py            # JSON API endpoints (/api)
│   ├── locations.py      # Locations CRUD (/locations)
│   ├── dashboard.py      # Dashboard views (/)
│   ├── events.py         # Event history & export (/events)
│   ├── help.py           # Help/documentation page (/help)
│   ├── inventory.py      # Inventory tracking & adjustment (/inventory)
│   ├── kanbans.py        # Kanban CRUD & label printing (/kanbans)
│   ├── parts.py          # Parts CRUD (/parts)
│   ├── reports.py        # Reports dashboard (/reports)
│   ├── scan.py           # Quick scan interface (/scan)
│   └── settings.py       # App settings & printer config (/settings)
├── templates/
│   ├── base.html         # Base layout with embedded CSS, JS, and theme support
│   ├── locations/
│   │   ├── detail.html
│   │   ├── form.html
│   │   └── list.html
│   ├── dashboard/
│   │   └── index.html
│   ├── events/
│   │   └── history.html
│   ├── help/
│   │   └── index.html
│   ├── inventory/
│   │   ├── adjust.html
│   │   └── index.html
│   ├── kanbans/
│   │   ├── detail.html
│   │   ├── form.html
│   │   └── list.html
│   ├── parts/
│   │   ├── detail.html
│   │   ├── form.html
│   │   └── list.html
│   ├── reports/
│   │   └── index.html
│   ├── scan/
│   │   └── quick.html
│   └── settings/
│       └── index.html
└── utils/
    ├── __init__.py
    ├── label.py          # ZPL label templates (KanbanLabelTemplate)
    └── zebra.py          # Zebra printer TCP client (ZebraPrinter)
```

---

## API Endpoints

### Pages (HTML)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Dashboard |
| GET | `/parts` | Parts list |
| GET | `/parts/<id>` | Part detail |
| GET | `/parts/new` | New part form |
| GET | `/parts/<id>/edit` | Edit part form |
| GET | `/locations` | Locations list |
| GET | `/locations/<id>` | Location detail |
| GET | `/locations/new` | New location form |
| GET | `/locations/<id>/edit` | Edit location form |
| GET | `/kanbans` | Kanbans list |
| GET | `/kanbans/<id>` | Kanban detail |
| GET | `/kanbans/new` | New kanban form |
| GET | `/kanbans/<id>/edit` | Edit kanban form |
| GET | `/kanbans/<id>/print` | Print kanban label to Zebra printer |
| GET | `/events` | Event history |
| GET | `/events/export` | Export events as CSV |
| GET | `/scan` | Quick scan interface |
| GET | `/reports` | Reports dashboard |
| GET | `/inventory` | Inventory overview |
| GET | `/inventory/<part_id>/adjust` | Inventory adjustment form |
| GET | `/inventory/export` | Export inventory as CSV |
| GET | `/help` | Help and documentation |
| GET | `/settings` | Application settings |

### Actions (Form POST)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/parts` | Create part |
| POST | `/parts/<id>` | Update part |
| POST | `/parts/<id>/delete` | Delete part |
| POST | `/locations` | Create location |
| POST | `/locations/<id>` | Update location |
| POST | `/locations/<id>/delete` | Delete location |
| POST | `/kanbans` | Create kanban |
| POST | `/kanbans/<id>` | Update kanban |
| POST | `/kanbans/<id>/delete` | Delete kanban |
| POST | `/scan` | Process scan action |
| POST | `/inventory/<part_id>/adjust` | Submit inventory adjustment |
| POST | `/settings/save` | Save settings |
| GET | `/settings/datawedge/start` | Start DataWedge TCP server |
| GET | `/settings/datawedge/stop` | Stop DataWedge TCP server |

### JSON API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/kanbans` | List kanbans with status |
| GET | `/api/kanbans/<id>` | Kanban detail with events |
| GET | `/api/kanbans/<id>/suggest-reorder-point` | Suggested reorder point |
| POST | `/api/events` | Record event |
| GET | `/api/health` | System health summary |
| GET | `/api/metrics` | Performance metrics |

---

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `unit_of_measure` | Pre-seeded measurement units (ea, kg, g, m, cm, mm, L, mL, ft, in) |
| `part` | Items tracked in inventory (part number, manufacturer, category, etc.) |
| `bin` | Physical storage locations (location code, description, color) |
| `kanban` | Links parts to bins with reorder parameters (quantity, safety lead time, demand) |
| `kanban_event_type` | Enumerated event types (signal, restock_start, restock_complete, adjustment) |
| `kanban_event` | Records all kanban lifecycle events with timestamps |
| `inventory` | Tracks current stock levels per part (quantity on hand) |
| `setting` | Application configuration (printer hostname, port, timeout) |

---

## DataWedge Configuration Notes

The system supports two scanning modes:

### Mode 1: TCP Server (Recommended for production)
- DataWedge configured with **IP Output** plugin pointing to the application host on port 58627
- Barcodes are sent as newline-terminated strings over TCP
- The application auto-starts the TCP server on launch and processes scans server-side
- Start/stop controls available at `/settings`

### Mode 2: Web Keyboard Wedge (Fallback)
- DataWedge configured with **Keystroke Output** enabled
- Suffix set to carriage return (Enter key)
- The `/scan` page auto-focuses the input field and auto-submits on Enter

---

## Design Decisions

1. **Authentication**: Not required — trusted network deployment
2. **Label Format**: Zebra ZPL with QR codes (sent via TCP to networked Zebra printers)
3. **Alerts/Notifications**: Not in scope for initial release
4. **Offline Capability**: Not required
5. **CSS/JS Embedding**: All CSS and JS embedded in `base.html` `<style>` and `<script>` tags — no separate static asset files — to avoid browser cache issues on updates
6. **Template Organization**: Flat per-module template directories (no shared components directory); reusable markup is inline in `base.html`
7. **Reorder Point**: Calculated dynamically from `safety_lead_time_days × estimated_daily_demand` rather than stored as a static field
8. **DataWedge Integration**: TCP socket server (not just keyboard-wedge) for reliable headless scanning

---

*PRD Version: 2.0*
*Created: 2026-03-14*
*Updated: 2026-04-08*
