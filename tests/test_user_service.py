"""Unit tests for UserService using an in-memory SQLite database."""

import sys
import sqlite3
import unittest

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parents[1] / 'src'))

from werkzeug.security import generate_password_hash

from kanban.repositories.user import UserRepository
from kanban.services.user import UserService

SCHEMA_PATH = '/root/projects/kanban/src/kanban/schema.sql'


def make_db() -> sqlite3.Connection:
    """Create and initialise an in-memory SQLite database from schema.sql."""
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    with open(SCHEMA_PATH) as fh:
        db.executescript(fh.read())
    return db


class TestUserServiceCreate(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.repo = UserRepository(self.db)
        self.svc = UserService(self.repo)

    def tearDown(self):
        self.db.close()

    def test_create_returns_success(self):
        result = self.svc.create(email='alice@example.com', display_name='Alice')
        self.assertTrue(result.success)

    def test_create_generates_token(self):
        result = self.svc.create(email='alice@example.com', display_name='Alice')
        self.assertIsNotNone(result.data)
        self.assertIn('token', result.data)
        self.assertTrue(len(result.data['token']) > 10)

    def test_create_stores_user_with_unusable_password(self):
        """The stored password hash should not match any trivial plain text."""
        result = self.svc.create(email='bob@example.com', display_name='Bob')
        user = self.repo.find_by_id(result.data['user_id'])
        # Must have a password hash; it should NOT be an empty string or None.
        self.assertTrue(user['password_hash'])
        # And it should not equal the raw token (i.e., it is hashed).
        self.assertNotEqual(user['password_hash'], result.data['token'])

    def test_create_sets_must_change_password(self):
        result = self.svc.create(email='carol@example.com', display_name='Carol')
        user = self.repo.find_by_id(result.data['user_id'])
        self.assertEqual(user['must_change_password'], 1)

    def test_create_duplicate_email_fails(self):
        self.svc.create(email='dup@example.com', display_name='First')
        result2 = self.svc.create(email='dup@example.com', display_name='Second')
        self.assertFalse(result2.success)

    def test_create_returns_user_id(self):
        result = self.svc.create(email='dave@example.com', display_name='Dave')
        self.assertIn('user_id', result.data)
        self.assertIsInstance(result.data['user_id'], int)


class TestUserServiceAuthenticate(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.repo = UserRepository(self.db)
        self.svc = UserService(self.repo)
        # Seed a known active user with a known password.
        self.password = 'Secret1!'
        self.repo.create(
            email='user@example.com',
            display_name='Test User',
            password_hash=generate_password_hash(self.password),
            role='user',
            is_active=1,
        )
        # Seed an inactive user.
        self.repo.create(
            email='inactive@example.com',
            display_name='Inactive User',
            password_hash=generate_password_hash(self.password),
            role='user',
            is_active=0,
        )

    def tearDown(self):
        self.db.close()

    def test_valid_credentials_return_user(self):
        user = self.svc.authenticate('user@example.com', self.password)
        self.assertIsNotNone(user)
        self.assertEqual(user['email'], 'user@example.com')

    def test_wrong_password_returns_none(self):
        result = self.svc.authenticate('user@example.com', 'WrongPass1!')
        self.assertIsNone(result)

    def test_unknown_email_returns_none(self):
        result = self.svc.authenticate('nobody@example.com', self.password)
        self.assertIsNone(result)

    def test_inactive_user_returns_none(self):
        result = self.svc.authenticate('inactive@example.com', self.password)
        self.assertIsNone(result)

    def test_email_case_insensitive(self):
        user = self.svc.authenticate('USER@EXAMPLE.COM', self.password)
        self.assertIsNotNone(user)


class TestUserServiceSetPassword(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.repo = UserRepository(self.db)
        self.svc = UserService(self.repo)
        uid = self.repo.create(
            email='pw@example.com',
            display_name='PW User',
            password_hash=generate_password_hash('OldPass1!'),
            role='user',
            is_active=1,
        )
        self.user_id = uid

    def tearDown(self):
        self.db.close()

    def test_valid_password_succeeds(self):
        result = self.svc.set_password(self.user_id, 'NewPass1!')
        self.assertTrue(result.success)

    def test_too_short_fails(self):
        result = self.svc.set_password(self.user_id, 'Ab1!')
        self.assertFalse(result.success)

    def test_no_lowercase_fails(self):
        result = self.svc.set_password(self.user_id, 'NOLOW1!!')
        self.assertFalse(result.success)

    def test_no_uppercase_fails(self):
        result = self.svc.set_password(self.user_id, 'noup1per!!')
        self.assertFalse(result.success)

    def test_no_digit_fails(self):
        result = self.svc.set_password(self.user_id, 'NoDigitsHere!')
        self.assertFalse(result.success)

    def test_new_password_can_authenticate(self):
        self.svc.set_password(self.user_id, 'NewPass1!')
        user = self.svc.authenticate('pw@example.com', 'NewPass1!')
        self.assertIsNotNone(user)


class TestUserServiceActivateWithToken(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.repo = UserRepository(self.db)
        self.svc = UserService(self.repo)
        # Create a user via svc so a reset token is set.
        result = self.svc.create(email='tok@example.com', display_name='Tok')
        self.token = result.data['token']
        self.user_id = result.data['user_id']

    def tearDown(self):
        self.db.close()

    def test_valid_token_succeeds(self):
        result = self.svc.activate_with_token(self.token, 'ValidPass1!')
        self.assertTrue(result.success)

    def test_valid_token_clears_token(self):
        self.svc.activate_with_token(self.token, 'ValidPass1!')
        user = self.repo.find_by_id(self.user_id)
        self.assertIsNone(user['password_reset_token'])

    def test_invalid_token_fails(self):
        result = self.svc.activate_with_token('not-a-real-token', 'ValidPass1!')
        self.assertFalse(result.success)

    def test_used_token_fails(self):
        self.svc.activate_with_token(self.token, 'ValidPass1!')
        # Try to use the same token a second time.
        result = self.svc.activate_with_token(self.token, 'AnotherPass2!')
        self.assertFalse(result.success)

    def test_weak_password_with_valid_token_fails(self):
        result = self.svc.activate_with_token(self.token, 'weak')
        self.assertFalse(result.success)


class TestUserServiceUpdateLastAdminGuard(unittest.TestCase):

    def setUp(self):
        self.db = make_db()
        self.repo = UserRepository(self.db)
        self.svc = UserService(self.repo)
        self.admin_id = self.repo.create(
            email='admin@example.com',
            display_name='Admin',
            password_hash=generate_password_hash('Admin1234!'),
            role='admin',
            is_active=1,
        )

    def tearDown(self):
        self.db.close()

    def test_cannot_demote_last_admin(self):
        result = self.svc.update(
            self.admin_id,
            email='admin@example.com',
            display_name='Admin',
            role='user',
            is_active=1,
        )
        self.assertFalse(result.success)

    def test_cannot_deactivate_last_admin(self):
        result = self.svc.update(
            self.admin_id,
            email='admin@example.com',
            display_name='Admin',
            role='admin',
            is_active=0,
        )
        self.assertFalse(result.success)

    def test_can_update_last_admin_keeping_role_and_active(self):
        result = self.svc.update(
            self.admin_id,
            email='admin_new@example.com',
            display_name='Admin Renamed',
            role='admin',
            is_active=1,
        )
        self.assertTrue(result.success)

    def test_can_demote_if_another_admin_exists(self):
        # Add a second admin.
        self.repo.create(
            email='admin2@example.com',
            display_name='Admin2',
            password_hash=generate_password_hash('Admin1234!'),
            role='admin',
            is_active=1,
        )
        result = self.svc.update(
            self.admin_id,
            email='admin@example.com',
            display_name='Admin',
            role='user',
            is_active=1,
        )
        self.assertTrue(result.success)


if __name__ == '__main__':
    unittest.main()
