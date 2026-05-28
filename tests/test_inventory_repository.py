"""Unit tests for InventoryRepository using an in-memory SQLite database."""

import sys
import sqlite3
import unittest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parents[1] / 'src'))

from kanban.repositories.inventory import InventoryRepository

SCHEMA_PATH = '/root/projects/kanban/src/kanban/schema.sql'


def make_db() -> sqlite3.Connection:
    """Create and initialise an in-memory SQLite database from schema.sql."""
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    with open(SCHEMA_PATH) as fh:
        db.executescript(fh.read())
    return db


def insert_part(db: sqlite3.Connection, part_number: str = 'P-001') -> int:
    """Insert a minimal part row and return its id."""
    cur = db.execute(
        """INSERT INTO part (part_number, manufacturer, unit_of_measure_id,
                             reorder_lead_time_days)
           VALUES (?, ?, ?, ?)""",
        [part_number, 'ACME', 1, 7.0],
    )
    db.commit()
    return cur.lastrowid


class TestInventoryRepositoryDecreaseQuantity(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.repo = InventoryRepository(self.db)
        self.part_id = insert_part(self.db)
        # Seed inventory with 100 units.
        self.db.execute(
            "INSERT INTO inventory (part_id, quantity_on_hand) VALUES (?, ?)",
            [self.part_id, 100.0],
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _get_qty(self) -> float:
        return self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.part_id],
        ).fetchone()['quantity_on_hand']

    def test_decrease_reduces_quantity(self):
        self.repo.decrease_quantity(self.part_id, 30.0)
        self.db.commit()
        self.assertEqual(self._get_qty(), 70.0)

    def test_decrease_floors_at_zero(self):
        """Decreasing by more than the current quantity must not go below 0."""
        self.repo.decrease_quantity(self.part_id, 200.0)
        self.db.commit()
        self.assertEqual(self._get_qty(), 0.0)

    def test_decrease_exact_amount_reaches_zero(self):
        self.repo.decrease_quantity(self.part_id, 100.0)
        self.db.commit()
        self.assertEqual(self._get_qty(), 0.0)

    def test_decrease_by_zero_is_noop(self):
        self.repo.decrease_quantity(self.part_id, 0.0)
        self.db.commit()
        self.assertEqual(self._get_qty(), 100.0)


class TestInventoryRepositoryIncreaseQuantity(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.repo = InventoryRepository(self.db)
        self.part_id = insert_part(self.db)

    def tearDown(self):
        self.db.close()

    def _get_qty(self) -> float | None:
        row = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [self.part_id],
        ).fetchone()
        return row['quantity_on_hand'] if row else None

    def test_increase_inserts_when_no_row_exists(self):
        """increase_quantity must upsert — create a row if none exists."""
        self.repo.increase_quantity(self.part_id, 50.0)
        self.db.commit()
        self.assertEqual(self._get_qty(), 50.0)

    def test_increase_adds_to_existing_quantity(self):
        """increase_quantity must add to an existing row."""
        self.db.execute(
            "INSERT INTO inventory (part_id, quantity_on_hand) VALUES (?, ?)",
            [self.part_id, 40.0],
        )
        self.db.commit()
        self.repo.increase_quantity(self.part_id, 25.0)
        self.db.commit()
        self.assertEqual(self._get_qty(), 65.0)

    def test_increase_multiple_times_accumulates(self):
        self.repo.increase_quantity(self.part_id, 10.0)
        self.db.commit()
        self.repo.increase_quantity(self.part_id, 20.0)
        self.db.commit()
        self.assertEqual(self._get_qty(), 30.0)

    def test_increase_different_parts_are_independent(self):
        """Increasing one part must not affect another part's inventory."""
        part_id_2 = insert_part(self.db, 'P-002')
        self.db.execute(
            "INSERT INTO inventory (part_id, quantity_on_hand) VALUES (?, ?)",
            [self.part_id, 100.0],
        )
        self.db.commit()
        self.repo.increase_quantity(part_id_2, 50.0)
        self.db.commit()
        # Part 1 should be unchanged.
        self.assertEqual(self._get_qty(), 100.0)
        qty_2 = self.db.execute(
            "SELECT quantity_on_hand FROM inventory WHERE part_id = ?",
            [part_id_2],
        ).fetchone()['quantity_on_hand']
        self.assertEqual(qty_2, 50.0)


if __name__ == '__main__':
    unittest.main()
