#!/usr/bin/env python3
import os
import sys
import time
import random
import base64
import requests

# ──────────────── Configuration ────────────────
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
XRAY_TOKEN    = os.getenv("XRAY_TOKEN")

if not JIRA_BASE_URL or not XRAY_TOKEN:
    print("❌ Missing one of JIRA_BASE_URL or XRAY_TOKEN environment variables")
    sys.exit(1)


def sleep_after(attempt: int, retry_after_header: str | None) -> float:
    """
    Returns how many seconds to sleep based on:
      - an explicit Retry-After header (if present & integer), or
      - exponential back-off 1, 2, 4, 8… + 0–1s jitter
    """
    if retry_after_header:
        try:
            return int(retry_after_header)
        except ValueError:
            pass
    base = 2 ** (attempt - 1)
    return base + random.random()


def fetch_test_run_id(test_exec_key: str, test_key: str) -> int:
    """
    Fetch the numeric test-run ID for a given execution key + test key.
    Retries on HTTP 429.
    """
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec/{test_exec_key}/test"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json",
    }
    max_retries = 5

    for attempt in range(1, max_retries + 1):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            results = (
                data
                if isinstance(data, list)
                else data.get("results", []) or data.get("values", [])
            )
            for entry in results:
                if entry.get("key") == test_key:
                    return entry["id"]
            raise ValueError(f"Test key '{test_key}' not found in execution '{test_exec_key}'")

        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            wait = sleep_after(attempt, ra)
            print(f"⚠️ GET rate-limited (attempt {attempt}/{max_retries}), "
                  f"Retry-After={ra!r}, sleeping {wait:.1f}s…")
            time.sleep(wait)
            continue

        # any other error: bail out
        resp.raise_for_status()

    raise RuntimeError(f"Failed to fetch run ID after {max_retries} retries (last code {resp.status_code})")


def upload_evidence(test_run_id: int, filename: str, content_type: str) -> None:
    """
    Upload a file or screenshot (base64‐encoded) to the given test run ID.
    Retries on HTTP 429.
    """
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Cannot find '{filename}'")

    with open(filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "data":        b64,
        "filename":    os.path.basename(filename),
        "contentType": content_type,
    }
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testrun/{test_run_id}/attachment"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json",
    }

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201, 204):
            print(f"✅ Uploaded {filename!r} to run {test_run_id} (HTTP {resp.status_code})")
            return

        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            wait = sleep_after(attempt, ra)
            print(f"⚠️ POST rate-limited (attempt {attempt}/{max_retries}), "
                  f"Retry-After={ra!r}, sleeping {wait:.1f}s…")
            time.sleep(wait)
            continue

        # any other error: bail out
        resp.raise_for_status()

    raise RuntimeError(f"Upload failed after {max_retries} retries (last code {resp.status_code})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <JIRA_TEST_EXEC_KEY>")
        sys.exit(1)

    test_execution_key = sys.argv[1]

    # ─── Map each XRAY test key to its file + content type ───
    mapping = {
        "HPCSVC-2003": {
            "file":         "filtered_settings/saml_settings_ansible_core.json",
            "content_type": "application/json",
        },
        "HPCSVC-2001": {
            "file":         "screenshots/screenshot.png",
            "content_type": "image/png",
        },
        # add more entries here …
    }

    for test_key, details in mapping.items():
        try:
            run_id = fetch_test_run_id(test_execution_key, test_key)
            print(f"🔍 Found run_id: {run_id} for test_key: {test_key}")
            upload_evidence(run_id, details["file"], details["content_type"])
        except Exception as e:
            print(f"❌ ERROR processing test_key '{test_key}': {e}")