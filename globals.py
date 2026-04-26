from server.db_config import CLOUDANT, NEON, POSTGRES  # noqa: F401

TRANSPORT_ID = 1

FUNCTION_URL_POSTGRES = (
    "https://hixavovpmato33sqqyxh6omv540acpnn.lambda-url.us-east-1.on.aws/"
)
FUNCTION_URL_CLOUDANT = ""

DEPARTURE_AFTER = 0
WRITE_SHIFT_SECS = 0
LARGE_SCAN_LIMIT = 5000

WAIT_MIN = 0.3
WAIT_MAX = 0.5
FAILURE_BACKOFF_SECS = 1.0

TASK_WEIGHTS = {
    "point_read": 10,
    "next_departures": 8,
    "large_scan": 2,
    "trips_per_route": 1,
    "bulk_update_departures": 1,
}

POOL_MAX_CONN = 50
CATALOG_POOL_SIZE = 200
CONCURRENCY_LEVELS = [1, 5, 35, 90]
COOLDOWN_SECS = 0
SPAWN_RATE = 20
RUN_TIME = "2m30s"
RESULTS_DIR = "results"

COLD_START_IDLE_SECS = 420
COLD_START_SAMPLES = 5
COLD_START_WARM_REPS = 10
