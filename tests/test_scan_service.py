"""Unit tests for ScanService.process_scan using an in-memory SQLite database."""

import sys
import sqlite3
import unittest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parents[1] / 'src'))

from kanban.repositories.kanban import KanbanRepository
from kanban.repositories.event import EventRepository
from kanban.repositories.inventory import InventoryRepository
from kanban.services.scan import ScanService

SCHEMA_PATH = str(__import__('pathlib').Path(__file__).parents[1] / 'src' / 'kanban' / 'schema.sql')


def make_db() -> sqlite3.Connection:
    """Create and initialise an in-memory SQLite database from schema.sql."""
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    with open(SCHEMA_PATH) as fh:
        db.executescript(fh.read())
    return db


def seed_fixtures(db: sqlite3.Connection) -> dict:
    """
    Insert the minimum set of rows needed by ScanService.

    Returns a dict with the primary-key IDs of seeded entities:
      part_id, location_id, kanban_id, inactive_kanban_id
    """
    # unit_of_measure row 1 ('Each') is already seeded by schema.sql
    # Insert a part
    cur = db.execute(
        """INSERT INTO part (part_number, manufacturer, description,
                             unit_of_measure_id, reorder_lead_time_days)
           VALUES (?, ?, ?, ?, ?)""",
        ['PART-001', 'ACME', 'Test Part', 1, 7.0],
    )
    part_id = cur.lastrowid

    # Insert a location
    cur = db.execute(
        "INSERT INTO location (location, description) VALUES (?, ?)",
        ['Shelf A', 'Main shelf'],
    )
    location_id = cur.lastrowid

    # Insert an ACTIVE kanban with number_of_cards = 2
    cur = db.execute(
        """INSERT INTO kanban
               (part_id, location_id, kanban_quantity, safety_lead_time_days,
                estimated_daily_demand, number_of_cards, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [part_id, location_id, 100, 0.0, 0.0, 2, 1],
    )
    kanban_id = cur.lastrowid

    # Insert an INACTIVE kanban
    cur = db.execute(
        """INSERT INTO kanban
               (part_id, location_id, kanban_quantity, safety_lead_time_days,
                estimated_daily_demand, number_of_cards, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [part_id, location_id, 100, 0.0, 0.0, 2, 0],
    )
    inactive_kanban_id = cur.lastrowid

    # Seed inventory with 200 units so decrease tests have something to work with.
    db.execute(
        "INSERT INTO inventory (part_id, quantity_on_hand) VALUES (?, ?)",
        [part_id, 200.0],
    )

    db.commit()

    return {
        'part_id': part_id,
        'location_id': location_id,
        'kanban_id': kanban_id,
        'inactive_kanban_id': inactive_kanban_id,
    }


def make_service(db: sqlite3.Connection) -> ScanService:
    kanban_repo = KanbanRepository(db)
    event_repo = EventRepository(db)
    inventory_repo = InventoryRepository(db)
    return ScanService(kanban_repo, event_repo, inventory_repo)


class TestScanServiceMissingAndInvalidBarcode(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        seed_fixtures(self.db)
        self.svc = make_service(self.db)

    def tearDown(self):
        self.db.close()

    def test_missing_barcode_fails(self):
        result = self.svc.process_scan('')
        self.assertFalse(result.success)
        self.assertIn('No barcode', result.message)

    def test_invalid_barcode_format_fails(self):
        result = self.svc.process_scan('INVALID_BARCODE')
        self.assertFalse(result.success)
        self.assertIn('Invalid barcode', result.message)


class TestScanServiceKanbanLookup(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.ids = seed_fixtures(self.db)
        self.svc = make_service(self.db)

    def tearDown(self):
        self.db.close()

    def test_kanban_not_found_fails(self):
        result = self.svc.process_scan('K999999')
        self.assertFalse(result.success)
        self.assertIn('not found', result.message)

    def test_inactive_kanban_fails(self):
        barcode = f"K{self.ids['inactive_kanban_id']:06d}"
        result = self.svc.process_scan(barcode, action='signal')
        self.assertFalse(result.success)
        self.assertIn('inactive', result.message.lower())


class TestScanServiceSignal(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.ids = seed_fixtures(self.db)
        self.svc = make_service(self.db)
        self.barcode = f"K{self.ids['kanban_id']:06d}"

    def tearDown(self):
        self.db.close()

    def test_signal_success(self):
        result = self.svc.process_scan(self.barcode, action='signal')
        self.assertTrue(result.success)

    def test_signal_decreases_inventory(self):
        before = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.ids['part_id']],
        ).fetchone()['quantity_on_hand']

        self.svc.process_scan(self.barcode, action='signal')

        after = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.ids['part_id']],
        ).fetchone()['quantity_on_hand']

        self.assertLess(after, before)
        # kanban_quantity is 100, so inventory should drop by exactly 100.
        self.assertEqual(before - after, 100.0)

    def test_signal_exceeds_number_of_cards_fails(self):
        """number_of_cards is 2; a third signal must be rejected."""
        self.svc.process_scan(self.barcode, action='signal')
        self.svc.process_scan(self.barcode, action='signal')
        result = self.svc.process_scan(self.barcode, action='signal')
        self.assertFalse(result.success)
        self.assertIn('already signaled', result.message)


class TestScanServiceRestockComplete(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.ids = seed_fixtures(self.db)
        self.svc = make_service(self.db)
        self.barcode = f"K{self.ids['kanban_id']:06d}"
        # First create an open signal to allow restock.
        self.svc.process_scan(self.barcode, action='signal')

    def tearDown(self):
        self.db.close()

    def test_restock_complete_success(self):
        result = self.svc.process_scan(self.barcode, action='restock_complete')
        self.assertTrue(result.success)

    def test_restock_complete_increases_inventory(self):
        before = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.ids['part_id']],
        ).fetchone()['quantity_on_hand']

        self.svc.process_scan(self.barcode, action='restock_complete')

        after = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.ids['part_id']],
        ).fetchone()['quantity_on_hand']

        self.assertGreater(after, before)

    def test_restock_complete_uses_explicit_quantity(self):
        before = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.ids['part_id']],
        ).fetchone()['quantity_on_hand']

        self.svc.process_scan(self.barcode, action='restock_complete', quantity='50')

        after = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.ids['part_id']],
        ).fetchone()['quantity_on_hand']

        self.assertEqual(after - before, 50.0)

    def test_restock_with_no_open_signal_fails(self):
        """Complete the open signal first, then attempt another restock."""
        self.svc.process_scan(self.barcode, action='restock_complete')
        # Now no open signals remain — next restock must fail.
        result = self.svc.process_scan(self.barcode, action='restock_complete')
        self.assertFalse(result.success)
        self.assertIn('no open signal', result.message)


if __name__ == '__main__':
    unittest.main()
