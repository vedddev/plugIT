import os
import tempfile
import unittest
import gc
from datetime import timedelta

from errors.exceptions import AuthenticationError
from key_management.store import APIKeyStore, utcnow


class KeyManagementTests(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.store = APIKeyStore(self.path, pepper="test-pepper")

    def tearDown(self):
        gc.collect()
        os.unlink(self.path)

    def test_create_authenticate_and_safe_metadata(self):
        record, key = self.store.create("client")
        self.assertTrue(key.startswith("sk-smartllm-"))
        self.assertEqual(self.store.authenticate(key)["id"], record["id"])
        listed = self.store.list()[0]
        self.assertNotIn("key", listed)
        self.assertNotIn("key_hash", listed)
        self.assertIsNotNone(self.store.get(record["id"])["last_used_at"])

    def test_revoke_rotate_and_expiration(self):
        record, old_key = self.store.create("client")
        self.store.revoke(record["id"])
        with self.assertRaises(AuthenticationError):
            self.store.authenticate(old_key)
        rotated, new_key = self.store.rotate(record["id"])
        with self.assertRaises(AuthenticationError):
            self.store.authenticate(old_key)
        self.assertEqual(self.store.authenticate(new_key)["id"], record["id"])
        _, expired = self.store.create("expired", utcnow() - timedelta(seconds=1))
        with self.assertRaises(AuthenticationError):
            self.store.authenticate(expired)

    def test_owner_scoped_key_operations_prevent_idor(self):
        alice, _ = self.store.create("alice", user_id="user-a")
        bob, _ = self.store.create("bob", user_id="user-b")
        self.assertEqual([item["id"] for item in self.store.list("user-a")], [alice["id"]])
        self.assertIsNone(self.store.get(bob["id"], "user-a"))
        self.assertIsNone(self.store.revoke(bob["id"], "user-a"))
        self.assertTrue(self.store.get(bob["id"], "user-b")["is_active"])


if __name__ == "__main__":
    unittest.main()
