from locust import HttpUser, task, between


class MyUser(HttpUser):
    wait_time = between(0.1, 0.1)  # simulate a fixed time of 0.1 seconds between tasks
    @task
    def my_task(self):
        self.client.get("/")