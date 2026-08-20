import os

from database_clients.db_config import CLOUDANT, NEON, POSTGRES  # noqa: F401

TRANSPORT_ID = 1

FUNCTION_URL_POSTGRES = os.getenv(
    "FUNCTION_URL_POSTGRES",
    "https://hixavovpmato33sqqyxh6omv540acpnn.lambda-url.us-east-1.on.aws/"
)
FUNCTION_URL_NEON = os.getenv(
    "FUNCTION_URL_NEON",
    "https://npefkdvgfzdxr6adqh43khhhuq0legzg.lambda-url.us-east-1.on.aws/"
)
FUNCTION_URL_IBM_SQL = os.getenv(
    "FUNCTION_URL_IBM_SQL",
    "https://3ekiips2t3l6lveodt2hvsaq4m0sgyjr.lambda-url.us-east-1.on.aws/"
)
FUNCTION_URL_CLOUDANT = os.getenv(
    "FUNCTION_URL_CLOUDANT",
    "https://vniwxhyrzfp5pndmer4grjdjey0hexwq.lambda-url.us-east-1.on.aws/"
)
FUNCTION_URL_MONGO = os.getenv(
    "FUNCTION_URL_MONGO",
    "https://w7th34c5pmhicjw2uauiz476ie0ovtkl.lambda-url.us-east-1.on.aws/"
)
FUNCTION_URL_DYNAMODB = os.getenv(
    "FUNCTION_URL_DYNAMODB",
    "https://squjzm5bmxt2ajq2ncxgoldjuq0kqmid.lambda-url.us-east-1.on.aws/"
)

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
CONCURRENCY_LEVELS = [16,64,128,256,512,1024]
COOLDOWN_SECS = 0
SPAWN_RATE = 20
RUN_TIME = "2m30s"
RESULTS_DIR = "results"

COLD_START_IDLE_SECS = 480
COLD_START_SAMPLES = 5
COLD_START_WARM_REPS = 10
