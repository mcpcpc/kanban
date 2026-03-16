# Production Kanban Management System - PRD

## Overview

A lightweight, production-grade kanban management system designed for physical inventory tracking using barcode scanners (Zebra DataWedge), physical bins, and kanban cards. The system prioritizes ease of use for 1-2 operators while providing comprehensive performance analytics.

---

## Problem Statement

Production environments need a simple, reliable way to:
- Track physical kanban card movements via barcode scanning
- Monitor inventory health across multiple bin locations
- Analyze kanban cycle times and replenishment performance
- Operate seamlessly across mobile scanners and desktop workstations

---

## Success Metrics

| Metric | Target |
|--------|--------|
| **Ease of Use** | Single-scan operations for common tasks; < 3 clicks for any action |
| **DataWedge Integration** | Seamless keyboard-wedge barcode input with auto-focus and auto-submit |
| **Analytics** | Track cycle times, stockout frequency, and kanban health scores |

---

## Technical Constraints

- **Framework**: Quart (async Python web framework)
- **Database**: SQLite3 (already implemented)
- **Dependencies**: No external libraries beyond Quart
- **Package Management**: PIP via pyproject.toml
- **Python Version**: 3.12+

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
- Fields: location code, description
- Visual bin status indicator (healthy/warning/critical)

#### FR-1.3: Kanban Management
- CRUD operations for kanban cards
- Fields: part, bin, kanban quantity, reorder point, max quantity, number of cards, active status
- Generate printable kanban cards with barcodes

#### FR-1.4: Units of Measure
- Pre-seeded list (already in schema)
- Read-only display; admin can add new units

### FR-2: Barcode Scanning & DataWedge Integration

#### FR-2.1: Scan Input Handling
- Auto-focus on scan input field when page loads
- Accept keyboard-wedge input (DataWedge sends keystrokes)
- Auto-submit on carriage return (configurable suffix)
- Support configurable prefix/suffix stripping

#### FR-2.2: Scan Actions
- **Signal Scan**: Record kanban card pull (replenishment signal)
- **Restock Start**: Begin restocking process
- **Restock Complete**: Complete restocking with quantity entry
- **Quick Scan Mode**: Dedicated scanning page with large input field

#### FR-2.3: Barcode Generation
- Generate Code128 barcodes for kanban cards (pure Python implementation)
- Printable card templates with part info, bin location, barcode

### FR-3: Event Tracking

#### FR-3.1: Event Types (already in schema)
- `signal` - Replenishment triggered
- `restock_start` - Restocking begun
- `restock_complete` - Restocking finished (with quantity)
- `stockout` - Inventory depleted
- `adjustment` - Manual correction

#### FR-3.2: Event Recording
- Automatic timestamp on all events
- Optional notes field for context
- Quantity field for restock/adjustment events

#### FR-3.3: Event History
- View event timeline per kanban
- Filter by event type, date range
- Export capability (CSV)

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
- Dual-tone SVG icons (embedded inline)
- No emoji usage
- Consistent icon set throughout

#### FR-5.5: Accessibility
- ARIA labels on interactive elements
- Keyboard navigation support
- High contrast mode compatibility

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

### NFR-4: Maintainability
- Clean separation of routes, templates, static assets
- Documented API endpoints
- Schema migrations via init-db command

---

## Architecture

### Existing Components (Implemented)
```
src/kanban/
├── __init__.py      # App factory, configuration
├── db.py            # Database connection, CLI commands
└── schema.sql       # SQLite schema with seed data
```

### Proposed Structure
```
src/kanban/
├── __init__.py           # App factory (enhanced)
├── db.py                 # Database utilities
├── schema.sql            # Database schema
├── routes/
│   ├── __init__.py       # Blueprint registration
│   ├── dashboard.py      # Dashboard views
│   ├── parts.py          # Parts CRUD
│   ├── bins.py           # Bins CRUD
│   ├── kanbans.py        # Kanban CRUD
│   ├── events.py         # Event recording & history
│   ├── scan.py           # Barcode scanning handlers
│   └── api.py            # JSON API endpoints
├── templates/
│   ├── base.html         # Base layout with embedded CSS and theme support
│   ├── components/       # Reusable template partials
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   ├── icons.html    # SVG icon definitions
│   │   ├── forms.html    # Form macros
│   │   └── cards.html    # Card components
│   ├── dashboard/
│   │   └── index.html
│   ├── parts/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── form.html
│   ├── bins/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── form.html
│   ├── kanbans/
│   │   ├── list.html
│   │   ├── detail.html
│   │   ├── form.html
│   │   └── card_print.html
│   ├── events/
│   │   ├── history.html
│   │   └── timeline.html
│   ├── scan/
│   │   └── quick.html    # Quick scan interface
│   └── reports/
│       └── index.html
├── static/
│   └── js/
│       ├── main.js       # Core functionality
│       ├── scan.js       # DataWedge handling
│       └── theme.js      # Theme switching
└── utils/
    ├── __init__.py
    ├── barcode.py        # Code128 barcode generation
    └── health.py         # Kanban health calculations
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
| GET | `/bins` | Bins list |
| GET | `/bins/<id>` | Bin detail |
| GET | `/bins/new` | New bin form |
| GET | `/kanbans` | Kanbans list |
| GET | `/kanbans/<id>` | Kanban detail |
| GET | `/kanbans/new` | New kanban form |
| GET | `/kanbans/<id>/print` | Printable kanban card |
| GET | `/events` | Event history |
| GET | `/scan` | Quick scan interface |
| GET | `/reports` | Reports dashboard |

### Actions (Form POST)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/parts` | Create part |
| POST | `/parts/<id>` | Update part |
| POST | `/parts/<id>/delete` | Delete part |
| POST | `/bins` | Create bin |
| POST | `/bins/<id>` | Update bin |
| POST | `/bins/<id>/delete` | Delete bin |
| POST | `/kanbans` | Create kanban |
| POST | `/kanbans/<id>` | Update kanban |
| POST | `/kanbans/<id>/delete` | Delete kanban |
| POST | `/scan` | Process scan action |

### JSON API
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/kanbans` | List kanbans with status |
| GET | `/api/kanbans/<id>` | Kanban detail with events |
| POST | `/api/events` | Record event |
| GET | `/api/health` | System health summary |
| GET | `/api/metrics` | Performance metrics |

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Fix schema.sql syntax errors
- [ ] Create base template with embedded CSS and theme support
- [ ] Implement SVG icon system
- [ ] Set up routes blueprint structure

### Phase 2: Core CRUD
- [ ] Parts management (list, create, edit, delete)
- [ ] Bins management (list, create, edit, delete)
- [ ] Kanbans management (list, create, edit, delete)
- [ ] Units of measure display

### Phase 3: Scanning & Events
- [ ] Quick scan interface with DataWedge support
- [ ] Event recording (signal, restock, stockout, adjustment)
- [ ] Event history and timeline views
- [ ] Barcode generation utility

### Phase 4: Analytics
- [ ] Dashboard with health overview
- [ ] Kanban health score calculation
- [ ] Performance metrics
- [ ] Reports and exports

### Phase 5: Polish
- [ ] Print styles for kanban cards
- [ ] CSV export functionality
- [ ] Error handling and validation
- [ ] Documentation

---

## DataWedge Configuration Notes

For Zebra DataWedge integration, the scanner should be configured with:
- **Output**: Keystroke output enabled
- **Suffix**: Carriage return (Enter key)
- **Prefix**: None (or configurable in app settings)

The application will:
1. Auto-focus the scan input field on page load
2. Listen for rapid keystroke input (barcode pattern)
3. Auto-submit on carriage return
4. Provide immediate visual/audio feedback

---

## Design Decisions

1. **Authentication**: Not required - trusted network deployment
2. **Barcode Format**: Code128 (pure Python implementation)
3. **Alerts/Notifications**: Not in scope for initial release
4. **Offline Capability**: Not required
5. **CSS Embedding**: All CSS embedded in base.html `<style>` tags to avoid browser cache issues on updates

---

## Appendix: Schema Fixes Required

The current `schema.sql` has the following issues to address:
1. Line 42: Trailing comma after last column in `part` table
2. Line 57: References `component(id)` but should be `part(id)`
3. Line 80: Missing closing parenthesis and semicolon on `kanban_event_type` INSERT

---

*PRD Version: 1.0*
*Created: 2026-03-14*
