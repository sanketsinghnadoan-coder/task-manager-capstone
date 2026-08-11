import unittest

from fastapi.testclient import TestClient

from main import app
from task_parser import parse_task_description

client = TestClient(app)


class TestTaskParser(unittest.TestCase):
    """Unit tests for the Quick-Add free-text parser (deterministic rules)."""

    def test_canonical_example(self):
        result = parse_task_description("Finish the report next Friday, it's urgent")
        self.assertEqual(result["title"], "Finish the report")
        self.assertEqual(result["priority"], "high")
        self.assertEqual(result["due_date_hint"], "next friday")

    def test_asap_high_priority(self):
        result = parse_task_description("Deploy hotfix ASAP")
        self.assertEqual(result["priority"], "high")
        self.assertIn("Deploy hotfix", result["title"])

    def test_low_priority_whenever(self):
        result = parse_task_description("Clean desk whenever")
        self.assertEqual(result["priority"], "low")
        self.assertEqual(result["due_date_hint"], None)

    def test_low_priority_phrase(self):
        result = parse_task_description("Organize files low priority")
        self.assertEqual(result["priority"], "low")

    def test_high_wins_over_low(self):
        result = parse_task_description("Do this whenever but urgent")
        self.assertEqual(result["priority"], "high")

    def test_default_medium(self):
        result = parse_task_description("Write unit tests")
        self.assertEqual(result["priority"], "medium")
        self.assertEqual(result["title"], "Write unit tests")
        self.assertIsNone(result["due_date_hint"])

    def test_relative_dates_precedence(self):
        self.assertEqual(
            parse_task_description("Ship today")["due_date_hint"], "today"
        )
        self.assertEqual(
            parse_task_description("Ship tomorrow")["due_date_hint"], "tomorrow"
        )
        self.assertEqual(
            parse_task_description("Plan next week")["due_date_hint"], "next week"
        )

    def test_next_weekday_before_bare(self):
        result = parse_task_description("Meet next monday about roadmap")
        self.assertEqual(result["due_date_hint"], "next monday")

    def test_bare_weekday(self):
        result = parse_task_description("Call client friday")
        self.assertEqual(result["due_date_hint"], "friday")

    def test_empty_after_cleanup(self):
        result = parse_task_description("urgent")
        self.assertEqual(result["title"], "Untitled task")
        self.assertEqual(result["priority"], "high")


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

        # Malformed email is rejected before a database write.
        res = client.post("/users", json={"email": "not-an-email"})
        self.assertEqual(res.status_code, 422)

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

    def test_05_quick_add_parse_endpoint(self):
        res = client.post("/tasks/parse", json={
            "description": "Finish the report next Friday, it's urgent"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["title"], "Finish the report")
        self.assertEqual(data["priority"], "high")
        self.assertEqual(data["due_date_hint"], "next friday")

        # Blank description -> 422
        blank = client.post("/tasks/parse", json={"description": "   "})
        self.assertEqual(blank.status_code, 422)

    def test_06_quick_add_create_endpoint(self):
        res = client.post("/tasks/quick-add", json={
            "description": "Finish the report next Friday, it's urgent",
            "project_id": self.project1_id,
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["title"], "Finish the report")
        self.assertEqual(data["priority"], "high")
        self.assertEqual(data["due_date"], "next friday")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["project_id"], self.project1_id)

        # Unknown project -> 404
        bad = client.post("/tasks/quick-add", json={
            "description": "Something tomorrow",
            "project_id": 999999,
        })
        self.assertEqual(bad.status_code, 404)

    def test_07_frontend_served(self):
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers.get("content-type", ""))
        self.assertIn(b"TaskFlow", res.content)
        self.assertIn(b"Quick-Add", res.content)

        css = client.get("/static/styles.css")
        self.assertEqual(css.status_code, 200)

        js = client.get("/static/app.js")
        self.assertEqual(js.status_code, 200)

        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
