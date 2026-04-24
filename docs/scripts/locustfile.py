from locust import HttpUser, task, between


class PsycareUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        resp = self.client.post(
            "/api/auth/token/",
            json={"username": "student1", "password": "123456"},
        )
        token = resp.json().get("access")
        if token:
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(3)
    def list_questionnaires(self):
        self.client.get("/api/surveys/questionnaires/")

    @task(2)
    def list_assessments(self):
        self.client.get("/api/assessments/results/")

    @task(1)
    def ai_chat(self):
        self.client.post("/api/chat/conversations/ai/", json={"content": "我最近有点焦虑。"})
