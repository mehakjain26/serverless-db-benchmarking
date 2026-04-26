from locust import LoadTestShape

# Compressed transit day. Durations are in seconds.
# Locust smoothly ramps users to the target at spawn_rate between stages.
STAGES = [
    {"duration": 330, "users": 20, "spawn_rate": 1, "label": "morning_rush"},
    {"duration": 330, "users": 0, "spawn_rate": 3, "label": "midday"},
    {"duration": 330, "users": 20, "spawn_rate": 1, "label": "evening_rush"},
    # {"duration": 90, "users": 0, "spawn_rate": 20, "label": "night"},
]


class DiurnalShape(LoadTestShape):
    def tick(self):
        run_time = self.get_run_time()
        elapsed = 0
        for stage in STAGES:
            elapsed += stage["duration"]
            if run_time < elapsed:
                return stage["users"], stage["spawn_rate"]
        return None
