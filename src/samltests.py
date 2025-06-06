import requests
import base64
import os
import json
import sys

JIRA_BASE_URL   = "https://<your-jira-domain>"
XRAY_TOKEN      = "<YOUR_BEARER_TOKEN>"

TEST_EXEC_KEY   = "HPCSVC-2922"
TARGET_TEST_KEY = "HPCSVC-1971"
LOCAL_FILE_NAME = "screenshot.png"
CONTENT_TYPE    = "image/png"

def fetch_test_run_id(test_exec_key, test_key):
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec/{test_exec_key}/test"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"GET tests failed: {resp.status_code} → {resp.text}")

    data = resp.json()
    # data is a list of { "id": 36841107, "key": "HPCSVC-1971", … }
    if not isinstance(data, list):
        data = data.get("results", []) or data.get("values", [])

    for entry in data:
        if entry.get("key") == test_key:
            return entry["id"]

    raise ValueError(f"Test key '{test_key}' not found in execution '{test_exec_key}'.")

def upload_evidence(test_run_id, filename, content_type):
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Cannot find '{filename}'")
    with open(filename, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "data":        b64,
        "filename":    filename,
        "contentType": content_type
    }
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testrun/{test_run_id}/attachment"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"Upload failed: {resp.status_code} → {resp.text}")
    print("Evidence uploaded (HTTP", resp.status_code, ")")

def set_run_status(test_run_id, status_value):
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testrun/{test_run_id}/status"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }
    payload = {"status": status_value}

    resp = requests.put(url, headers=headers, json=payload)
    if resp.status_code != 200:
        raise RuntimeError(f"Status update failed: {resp.status_code} → {resp.text}")

    print(f"Test Run {test_run_id} marked as {status_value} (HTTP 200).")

if __name__ == "__main__":
    try:
        run_id = fetch_test_run_id(TEST_EXEC_KEY, TARGET_TEST_KEY)
        print("Found run_id:", run_id)
    except Exception as e:
        print("ERROR fetching run_id:", e)
        sys.exit(1)

    try:
        upload_evidence(run_id, LOCAL_FILE_NAME, CONTENT_TYPE)
    except Exception as e:
        print("ERROR uploading evidence:", e)
        sys.exit(1)

    # Try either "PASS" or "PASSED" depending on your Xray flavor:
    try:
        set_run_status(run_id, "PASS")
    except Exception as e:
        print("ERROR updating status:", e)
        sys.exit(1)

    print("✅ Done! Evidence attached and test is now marked PASS.")