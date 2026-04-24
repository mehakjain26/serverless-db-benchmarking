import time

from locust import HttpUser, User, between, events, task

import globals as G
from req_gen import RequestType, build


class BenchmarkTasks:
    catalog: list = []
    wait_time = between(G.WAIT_MIN, G.WAIT_MAX)

    def run_op(self, rtype: RequestType) -> None:
        raise NotImplementedError

    @task(G.TASK_WEIGHTS["point_read"])
    def t_point_read(self):
        self.run_op(RequestType.POINT_READ)

    @task(G.TASK_WEIGHTS["next_departures"])
    def t_next_departures(self):
        self.run_op(RequestType.NEXT_DEPARTURES)

    @task(G.TASK_WEIGHTS["large_scan"])
    def t_large_scan(self):
        self.run_op(RequestType.LARGE_SCAN)

    @task(G.TASK_WEIGHTS["trips_per_route"])
    def t_trips_per_route(self):
        self.run_op(RequestType.TRIPS_PER_ROUTE)

    @task(G.TASK_WEIGHTS["bulk_update_departures"])
    def t_bulk_update(self):
        self.run_op(RequestType.BULK_UPDATE_DEPARTURES)

    # Pre-expanded so UserMeta applies weights correctly
    tasks = (
        [t_point_read] * G.TASK_WEIGHTS["point_read"]
        + [t_next_departures] * G.TASK_WEIGHTS["next_departures"]
        + [t_large_scan] * G.TASK_WEIGHTS["large_scan"]
        + [t_trips_per_route] * G.TASK_WEIGHTS["trips_per_route"]
        + [t_bulk_update] * G.TASK_WEIGHTS["bulk_update_departures"]
    )


class BenchmarkUser(BenchmarkTasks, User):
    abstract = True

    def execute_op(self, req) -> "tuple[list, float]":
        raise NotImplementedError

    def on_start(self) -> None:
        raise NotImplementedError

    def run_op(self, rtype: RequestType) -> None:
        req = build(rtype, self.catalog)
        t0 = time.perf_counter()
        exc = None
        rows = []
        try:
            rows, _ = self.execute_op(req)
        except Exception as e:
            exc = e
        events.request.fire(
            request_type="DB",
            name=rtype.value,
            response_time=(time.perf_counter() - t0) * 1000,
            response_length=len(rows),
            exception=exc,
        )


class BenchmarkHttpUser(BenchmarkTasks, HttpUser):
    abstract = True

    def on_start(self) -> None:
        raise NotImplementedError

    def run_op(self, rtype: RequestType) -> None:
        req = build(rtype, self.catalog)
        try:
            self.client.get(
                "/",
                params={"op": req.type.value, **req.params},
                name=rtype.value,
            )
        except Exception:
            pass
