import unittest
from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)


class TestTaskManagerAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Create test user 1
        res1 = client.post("/users", json={"email": "user1@example.com", "name": "User One"})
        assert res1.status_code in [201, 400]
        if res1.status_code == 201:
            cls.user1_id = res1.json()["id"]
        else:
            cls.user1_id = client.get("/users").json()[0]["id"]

        # Create test user 2
        res2 = client.post("/users", json={"email": "user2@example.com", "name": "User Two"})
        assert res2.status_code in [201, 400]
        if res2.status_code == 201:
            cls.user2_id = res2.json()["id"]
        else:
            cls.user2_id = client.get("/users").json()[-1]["id"]

        # Create Project 1 owned by User 1
        p1 = client.post("/projects", json={"name": "Project Alpha", "owner_id": cls.user1_id})
        assert p1.status_code == 201
        cls.project1_id = p1.json()["id"]

        # Create Project 2 owned by User 1
        p2 = client.post("/projects", json={"name": "Project Beta", "owner_id": cls.user1_id})
        assert p2.status_code == 201
        cls.project2_id = p2.json()["id"]

    def test_01_user_and_project_crud(self):
        # List users (200 OK)
        res = client.get("/users")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 2)

        # List projects (200 OK)
        res = client.get("/projects")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.json()), 2)

        # Non-existent user -> 404
        res = client.post("/projects", json={"name": "Invalid Project", "owner_id": 999999})
        self.assertEqual(res.status_code, 404)

    def test_02_task_creation_and_validation(self):
        # Valid task creation (201 Created)
        t1 = client.post("/tasks", json={
            "title": "Build FastAPI backend",
            "project_id": self.project1_id,
            "priority": "high",
            "due_date": "next friday",
            "status": "pending"
        })
        self.assertEqual(t1.status_code, 201)
        task1_data = t1.json()
        self.assertEqual(task1_data["title"], "Build FastAPI backend")
        self.assertEqual(task1_data["priority"], "high")
        self.assertEqual(task1_data["due_date"], "next friday")

        # Create task in Project 1
        t2 = client.post("/tasks", json={
            "title": "Design Database Schema",
            "project_id": self.project1_id,
            "priority": "medium",
            "due_date": "2026-08-20",
            "status": "completed"
        })
        self.assertEqual(t2.status_code, 201)

        # Create task in Project 2
        t3 = client.post("/tasks", json={
            "title": "Write Frontend UI",
            "project_id": self.project2_id,
            "priority": "low",
            "due_date": "tomorrow",
            "status": "pending"
        })
        self.assertEqual(t3.status_code, 201)

        # Invalid blank title -> 422 Unprocessable Entity
        t_blank = client.post("/tasks", json={
            "title": "   ",
            "project_id": self.project1_id,
            "priority": "medium"
        })
        self.assertEqual(t_blank.status_code, 422)

        # Invalid priority -> 422 Unprocessable Entity
        t_bad_priority = client.post("/tasks", json={
            "title": "Invalid Priority Task",
            "project_id": self.project1_id,
            "priority": "super_high"
        })
        self.assertEqual(t_bad_priority.status_code, 422)

    def test_03_task_read_update_delete(self):
        # Create task to update & delete
        res = client.post("/tasks", json={
            "title": "Temporary Task",
            "project_id": self.project1_id,
            "priority": "low"
        })
        task_id = res.json()["id"]

        # GET /tasks/{id} (200 OK)
        res_get = client.get(f"/tasks/{task_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["title"], "Temporary Task")

        # GET /tasks/{id} with unknown ID -> 404 Not Found
        res_404 = client.get("/tasks/999999")
        self.assertEqual(res_404.status_code, 404)

        # PUT /tasks/{id} (200 OK)
        res_put = client.put(f"/tasks/{task_id}", json={
            "title": "Updated Task Title",
            "priority": "high",
            "status": "completed"
        })
        self.assertEqual(res_put.status_code, 200)
        self.assertEqual(res_put.json()["title"], "Updated Task Title")
        self.assertEqual(res_put.json()["priority"], "high")

        # DELETE /tasks/{id} (200 OK)
        res_del = client.delete(f"/tasks/{task_id}")
        self.assertEqual(res_del.status_code, 200)

        # Verify deletion -> 404 Not Found
        res_after = client.get(f"/tasks/{task_id}")
        self.assertEqual(res_after.status_code, 404)

    def test_04_project_stats_aggregate(self):
        # GET /projects/{id}/stats (200 OK)
        res1 = client.get(f"/projects/{self.project1_id}/stats")
        self.assertEqual(res1.status_code, 200)
        stats1 = res1.json()
        self.assertEqual(stats1["project_id"], self.project1_id)
        self.assertGreaterEqual(stats1["total_tasks"], 2)
        self.assertIn("priority_counts", stats1)
        self.assertIn("status_counts", stats1)

        # Stats for Project 2
        res2 = client.get(f"/projects/{self.project2_id}/stats")
        self.assertEqual(res2.status_code, 200)
        stats2 = res2.json()
        self.assertEqual(stats2["project_id"], self.project2_id)
        self.assertGreaterEqual(stats2["total_tasks"], 1)

        # Stats for unknown project -> 404 Not Found
        res_404 = client.get("/projects/999999/stats")
        self.assertEqual(res_404.status_code, 404)


if __name__ == "__main__":
    unittest.main()
