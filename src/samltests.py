#!/usr/bin/env python3
import os
import sys
import base64
import time
import requests

# ——— CONFIGURATION ———
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
XRAY_TOKEN   = os.getenv("XRAY_TOKEN")

if not JIRA_BASE_URL or not XRAY_TOKEN:
    sys.exit("❌ Must set JIRA_BASE_URL and XRAY_TOKEN environment variables")

def fetch_test_run_id(test_exec_key: str, test_key: str) -> int:
    """
    Fetch the test-run ID from Xray for the given execution and test key.
    """
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec/{test_exec_key}/test"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"GET tests failed: {resp.status_code} -> {resp.text}")

    data = resp.json()
    # Xray sometimes returns a list directly, or wraps in {"results": [...]} or {"values": [...]}
    if not isinstance(data, list):
        data = data.get("results") or data.get("values") or []

    for entry in data:
        if entry.get("key") == test_key:
            return entry["id"]

    raise ValueError(f"Test key '{test_key}' not found in execution '{test_exec_key}'")

def upload_evidence(test_run_id: int, filename: str, content_type: str):
    """
    Upload a file or screenshot to the given test-run ID, with retry/back-off on 429.
    """
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Cannot find '{filename}'")

    with open(filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "data":        b64,
        "filename":    os.path.basename(filename),
        "contentType": content_type
    }
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testrun/{test_run_id}/attachment"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        resp = requests.post(url, headers=headers, json=payload)
        if resp.status_code in (200, 201, 204):
            print(f"✅ Uploaded '{filename}' to run {test_run_id} (HTTP {resp.status_code})")
            return

        if resp.status_code == 429:
            # rate-limited: back off
            retry_after = int(resp.headers.get("Retry-After", "5"))
            print(f"⚠️  Rate-limited (attempt {attempt}/{max_retries}), sleeping {retry_after}s…")
            time.sleep(retry_after)
            continue

        # any other error: bail out
        resp.raise_for_status()

    # if we get here, all retries failed
    raise RuntimeError(f"Upload failed after {max_retries} attempts (last code {resp.status_code})")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python upload_evidence_jira.py <TEST_EXECUTION_KEY>")
        sys.exit(1)

    test_exec_key = sys.argv[1]

    # Map your individual test-keys to the files you want to upload:
    mapping = {
        "HPCSVC-2003": {
            "file":         "filtered_settings/saml_settings_ansible_core.json",
            "content_type": "application/json",
        },
        "HPCSVC-2001": {
            "file":         "screenshots/screenshot.png",
            "content_type": "image/png",
        },
        # add more test-keys here as needed
    }

    for test_key, details in mapping.items():
        try:
            run_id = fetch_test_run_id(test_exec_key, test_key)
            print(f"Found run_id: {run_id} for test_key: {test_key}")
            upload_evidence(run_id, details["file"], details["content_type"])
        except Exception as e:
            print(f"ERROR processing test_key '{test_key}': {e}")

