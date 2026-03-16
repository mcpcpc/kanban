-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS unit_of_measure;
DROP TABLE IF EXISTS part;
DROP TABLE IF EXISTS bin;
DROP TABLE IF EXISTS kanban;
DROP TABLE IF EXISTS kanban_event_type;
DROP TABLE IF EXISTS kanban_event;
DROP TABLE IF EXISTS inventory;

-- Units of Measure: How parts should be quantified
CREATE TABLE unit_of_measure (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    abbreviation TEXT UNIQUE NOT NULL
);

INSERT INTO unit_of_measure (name, abbreviation) VALUES
    ('Each', 'ea'),
    ('Kilograms', 'kg'),
    ('Grams', 'g'),
    ('Meters', 'm'),
    ('Centimeters', 'cm'),
    ('Millimeters', 'mm'),
    ('Liters', 'L'),
    ('Milliliters', 'mL'),
    ('Feet', 'ft'),
    ('Inches', 'in');

-- Parts: Items being tracked in inventory
CREATE TABLE part (
    id INTEGER PRIMARY KEY,
    part_number TEXT UNIQUE NOT NULL,
    manufacturer TEXT NOT NULL,
    description TEXT,
    category TEXT,
    datasheet TEXT,
    unit_of_measure_id INTEGER NOT NULL REFERENCES unit_of_measure(id),
    reorder_lead_time_days REAL DEFAULT 7.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Bins: Physical locations holding inventory
CREATE TABLE bin (
    id INTEGER PRIMARY KEY,
    location TEXT NOT NULL,
    description TEXT,
    color TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Kanbans: Links components to bins with reorder parameters
CREATE TABLE kanban (
    id INTEGER PRIMARY KEY,
    part_id INTEGER NOT NULL REFERENCES part(id),
    bin_id INTEGER NOT NULL REFERENCES bin(id),
    kanban_quantity INTEGER NOT NULL DEFAULT 100,
    safety_stock INTEGER NOT NULL DEFAULT 0,
    estimated_daily_demand REAL NOT NULL DEFAULT 0,
    number_of_cards INTEGER NOT NULL DEFAULT 2,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- KanbanEventType: The possible kanban states
CREATE TABLE kanban_event_type (
    id INTEGER PRIMARY KEY,
    type TEXT UNIQUE NOT NULL,
    description TEXT UNIQUE NOT NULL
);

INSERT INTO kanban_event_type (type, description) VALUES
    ('signal', 'Indicates a replenishment signal was triggered (i.e. kanban card was pulled)'),
    ('restock_start', 'Marks that restocking is in progress'),
    ('restock_complete', 'Indicates restocking has been completed (includes quantity)'),
    ('adjustment', 'Manual inventory adjustment (includes quantity)');

-- KanbanEvents: Records all kanban lifecycle events
CREATE TABLE kanban_event (
    id INTEGER PRIMARY KEY,
    kanban_id INTEGER NOT NULL REFERENCES kanban(id),
    kanban_event_type INTEGER NOT NULL REFERENCES kanban_event_type(id),
    quantity INTEGER,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Inventory: Tracks current stock levels per part
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY,
    part_id INTEGER NOT NULL UNIQUE REFERENCES part(id),
    quantity_on_hand REAL NOT NULL DEFAULT 0,
    last_count_date TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
