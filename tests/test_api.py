import copy
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import fastserver


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.original_users = copy.deepcopy(fastserver.users_db)
        fastserver.data.update(server_status="정상", ready_status="준비 완료")
        self.client = TestClient(fastserver.app)

    def tearDown(self):
        fastserver.users_db[:] = self.original_users
        fastserver.data.update(server_status="정상", ready_status="준비 완료")
        self.client.close()

    def test_home_and_version_identify_running_release(self):
        self.assertIn("sk210 Final API", self.client.get("/").text)
        with patch.dict(os.environ, {"APP_VERSION": "build-7", "SOURCE_REVISION": "abc123"}):
            result = self.client.get("/api/version")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {
            "application": "sk210-final-api",
            "message": "capstone v2",
            "version": "build-7",
            "source_revision": "abc123",
        })

    def test_users_create_update_delete_and_missing_user(self):
        created = self.client.post("/api/users", json={
            "name": "capstone", "email": "capstone@example.com"
        })
        self.assertEqual(created.status_code, 201)
        user_id = created.json()["id"]
        self.assertEqual(self.client.get(f"/api/users/{user_id}").json()["name"], "capstone")
        updated = self.client.put(f"/api/users/{user_id}", json={"name": "updated"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "updated")
        self.assertEqual(self.client.delete(f"/api/users/{user_id}").status_code, 204)
        self.assertEqual(self.client.get(f"/api/users/{user_id}").status_code, 404)

    def test_invalid_email_rejected(self):
        self.assertEqual(self.client.post("/api/users", json={
            "name": "invalid", "email": "not-an-email"
        }).status_code, 422)

    def test_readiness_failure_does_not_change_liveness(self):
        self.assertEqual(self.client.get("/python/health/readiness").status_code, 200)
        changed = self.client.post("/", data={
            "server_status": "정상", "ready_status": "준비중"
        })
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get("/python/health/readiness").status_code, 503)
        self.assertEqual(self.client.get("/python/health/liveness").status_code, 200)

    def test_liveness_failure_is_detected(self):
        self.client.post("/", data={"server_status": "장애", "ready_status": "준비 완료"})
        self.assertEqual(self.client.get("/python/health/liveness").status_code, 400)

    def test_metrics_and_openapi_remain_available(self):
        self.client.get("/api/users")
        metrics = self.client.get("/python/prometheus")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn("http_server_requests_seconds", metrics.text)
        self.assertIn("/api/version", self.client.get("/swagger/openapi.json").json()["paths"])


if __name__ == "__main__":
    unittest.main()
