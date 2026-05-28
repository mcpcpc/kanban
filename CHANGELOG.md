# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- One-time setup links for new users — admins no longer set temporary passwords;
  a secure token URL is displayed once after account creation and can be
  regenerated from the edit page
- "Generate Setup Link" button on the user edit page for resending activation links
- `must_change_password` and `password_reset_token` columns on the `user` table
- Role-based access control (admin / manager / user) with session-based auth
  and 8-hour inactivity timeout
- DataWedge TCP integration for physical barcode scanners
- Zebra label printer support with a configurable ZPL template editor
- Dashboard with 4 stat cards and a 30-day signal activity bar chart
- Pending signals list and recent activity feed on the dashboard
- Kanban CRUD with auto-calculated reorder points and number-of-cards
- Scan workflow: signal → restock_start → restock_complete with poka-yoke
  validation; inventory adjusted automatically on signal and restock_complete
- Inventory quantity tracking with cycle-count upsert and per-part adjust page
- Parts, Locations, and Events management with search, pagination, and CSV export
- Reports page: event counts by type, most active kanbans, avg cycle time
- Settings page: Zebra printer configuration and ZPL label template editor
- `create-admin` CLI command for bootstrapping the first administrator account

### Changed
- Redesigned UI: zinc-neutral color system, blue primary (`#2563EB`), ghost
  breadcrumb, pill-style nav active states, narrowed sidebar
- Dashboard sparklines replaced with a pure-CSS flexbox bar chart
- Refactored to SOLID architecture: repositories → services → routes with
  unified dependency injection via `deps.py`
- Renamed `bin`/`bins` to `location`/`locations` throughout
- `restock_complete` now restores `quantity_on_hand`; uses the operator-entered
  quantity or falls back to `kanban_quantity`

### Fixed
- Inventory drift: `restock_complete` events now correctly increase
  `quantity_on_hand`
- Kanban edit page internal server error caused by missing `lead_time_days`
  alias in `get_with_lead_time` query
- `KanbanLabelTemplate` parameter names aligned with query column aliases;
  ZPL template placeholders now accept both `{manufacturer}` /
  `{part_manufacturer}` and `{uom_abbr}` / `{unit_of_measure_abbreviation}`
- Reports stat cards displayed oversized SVG icons due to missing CSS classes
- `create-admin` CLI command broken after password field was removed from
  `UserService.create()`

### Removed
- `/api` JSON endpoints and associated dead code
- Unused 30-day creation-trend queries for kanbans, parts, and locations
- OAuth integration (removed pending future implementation)
- Card print view (replaced by Zebra label printing)
