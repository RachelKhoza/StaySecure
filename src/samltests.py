import base64
import json
import requests
import os
import sys

# ─────────── CONFIGURATION ───────────
JIRA_BASE_URL   = "https://<your-jira-domain>"
XRAY_TOKEN      = "<YOUR_BEARER_TOKEN>"

TEST_EXEC_KEY   = "HPCSVC-2922"
TARGET_TEST_KEY = "HPCSVC-2003"

LOCAL_FILE_NAME = "saml-configuration.png"
CONTENT_TYPE    = "image/png"
# ─────────────────────────────────────

def fetch_test_run_id(test_exec_key: str, test_key: str) -> int:
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec/{test_exec_key}/test"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch tests for execution {test_exec_key}: "
            f"{resp.status_code} → {resp.text}"
        )

    data = resp.json()
    # If Xray returns a dict, extract the array; otherwise data is already the list
    if not isinstance(data, list):
        data = data.get("results", []) or data.get("values", [])

    for entry in data:
        if entry.get("key") == test_key:
            return entry["id"]

    raise ValueError(
        f"Test key '{test_key}' not found in execution '{test_exec_key}'."
    )

def upload_evidence_to_run(test_run_id: int, filename: str, content_type: str):
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Cannot find '{filename}' in {os.getcwd()}")

    with open(filename, "rb") as f:
        raw_bytes   = f.read()
        b64_content = base64.b64encode(raw_bytes).decode("utf-8")

    payload = {
        "data":        b64_content,
        "filename":    filename,
        "contentType": content_type
    }

    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testrun/{test_run_id}/attachment"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }
    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to upload evidence to run {test_run_id}: "
            f"{resp.status_code} → {resp.text}"
        )
    return resp.json()

if __name__ == "__main__":
    try:
        run_id = fetch_test_run_id(TEST_EXEC_KEY, TARGET_TEST_KEY)
        print(f"🔎 Found testRunId = {run_id} for test '{TARGET_TEST_KEY}'")
    except Exception as e:
        print("❌ Error while fetching testRunId:", e)
        sys.exit(1)

    try:
        response_json = upload_evidence_to_run(
            test_run_id=run_id,
            filename=LOCAL_FILE_NAME,
            content_type=CONTENT_TYPE
        )
        print("✅ Evidence uploaded successfully. Response:")
        print(json.dumps(response_json, indent=2))
    except Exception as e:
        print("❌ Error while uploading evidence:", e)
        sys.exit(1)