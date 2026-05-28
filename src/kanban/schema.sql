-- Initialize the database.
-- Drop any existing data and create empty tables.

DROP TABLE IF EXISTS unit_of_measure;
DROP TABLE IF EXISTS part;
DROP TABLE IF EXISTS location;
DROP TABLE IF EXISTS kanban;
DROP TABLE IF EXISTS kanban_event_type;
DROP TABLE IF EXISTS kanban_event;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS setting;
DROP TABLE IF EXISTS user;

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

-- Locations: Physical locations holding inventory
CREATE TABLE location (
    id INTEGER PRIMARY KEY,
    location TEXT NOT NULL,
    description TEXT,
    color TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Kanbans: Links components to locations with reorder parameters
CREATE TABLE kanban (
    id INTEGER PRIMARY KEY,
    part_id INTEGER NOT NULL REFERENCES part(id),
    location_id INTEGER NOT NULL REFERENCES location(id),
    kanban_quantity INTEGER NOT NULL DEFAULT 100,
    safety_lead_time_days REAL NOT NULL DEFAULT 0,
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
    user_id INTEGER REFERENCES user(id),
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

-- Users: Application accounts with role-based access
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'manager', 'user')),
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Setting: Stores application configuration
CREATE TABLE setting (
    id INTEGER PRIMARY KEY,
    printer_hostname TEXT NOT NULL,
    printer_port INTEGER NOT NULL,
    printer_timeout_seconds REAL NOT NULL,
    label_template TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO setting (printer_hostname, printer_port, printer_timeout_seconds, label_template) VALUES
    ('localhost', 9100, 10.0,
'^XA
^PW532
^MNY
^LL329
^LH0,0
^LT10
^LS-50
^MD15
^PR1
^PON
^FO16,12
^BQN,2,6,H
^FDQA,K{id:06d}^FS
^FO162,18
^A0N,32,32
^FDK{id:06d}^FS
^FO392,18
^A0N,32,32
^FD{location_name}^FS
^FO162,55
^A0N,28,28
^FD{part_number}^FS
^FO162,99
^A0N,28,28
^FD{manufacturer}^FS
^FO162,130
^A0N,20,20
^TBN,345,96
^FD{part_description}^FS
^FO162,254
^A0N,26,26
^FDQty: {kanban_quantity}^FS
^FO270,254
^A0N,26,26
^FDROP: {reorder_point}^FS
^FO392,254
^A0N,26,26
^FD{card_number} of {number_of_cards}^FS
^PQ1
^XZ');
