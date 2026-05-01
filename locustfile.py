from locust import HttpUser, task, between
import random

UNIQUE_QUERIES = [
    "is malpass library open late tonight",
    "can i borrow books from another university",
    "how long can i keep a library book",
    "do i need my student id to use the library",
    "can i study in the library overnight",
    "how do i get a library card",
    "where are the library printers located",
    "can i reserve a group study room online",
    "how do i access journals from my apartment",
    "what databases does wiu library have",
    "can i request a book the library doesnt have",
    "how do i cite library sources",
    "is there a librarian available to help me",
    "how do i print from my laptop in the library",
    "what is the library phone number",
]


class LibraryChatUserUncached(HttpUser):
    wait_time = between(1, 3)

    @task
    def ask_unique_question(self):
        query = random.choice(UNIQUE_QUERIES)
        self.client.post("/api/chat", json={"message": query})
