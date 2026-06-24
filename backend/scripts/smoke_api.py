from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SMOKE_ENDPOINTS = [
    "/api/projects",
    "/api/users/project-owner-candidates",
    "/api/reagents",
    "/api/experiment-records",
    "/api/daily-reports",
]


def request_json(url: str, *, method: str = "GET", token: str | None = None, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")

    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"{method} {url} returned HTTP {response.status}")
        if data.get("code") != 0:
            raise RuntimeError(f"{method} {url} returned API code {data.get('code')}")
        return data


def run_smoke(base_url: str, username: str, password: str) -> None:
    base_url = base_url.rstrip("/")
    request_json(f"{base_url}/api/health")
    login = request_json(
        f"{base_url}/api/auth/login",
        method="POST",
        payload={"username": username, "password": password},
    )
    token = login["data"]["access_token"]
    for endpoint in SMOKE_ENDPOINTS:
        request_json(f"{base_url}{endpoint}", token=token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a lightweight HTTP smoke test against a running LIMS backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="password123")
    args = parser.parse_args()

    try:
        run_smoke(args.base_url, args.username, args.password)
    except (HTTPError, URLError, RuntimeError, KeyError, ValueError) as exc:
        raise SystemExit(f"Smoke test failed: {exc}") from exc
    print("Smoke test passed: health, login, projects, owner candidates, reagents, experiments, daily reports")


if __name__ == "__main__":
    main()
