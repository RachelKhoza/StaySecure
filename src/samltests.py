import base64
import json
import requests
import os
import sys

# ─────────── CONFIGURATION ───────────
JIRA_BASE_URL   = "https://<your-jira-domain>"
XRAY_TOKEN      = "<YOUR_BEARER_TOKEN>"

TEST_EXEC_KEY   = "HPCSVC-2922"
TARGET_TEST_KEY = "HPCSVC-1971"    # or HPCSVC-2003, whichever you want

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
            f"Failed to fetch tests for execution {test_exec_key}:\n"
            f"  HTTP {resp.status_code} → {resp.text}"
        )

    data = resp.json()
    # Data is a LIST of objects, each like:
    # {
    #   "id": 36841106,
    #   "status": "TODO",
    #   "archived": false,
    #   "key": "HPCSVC-2003",
    #   "rank": 1
    # }
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

    # Treat 200/201/204 as success
    if resp.status_code in (200, 201, 204):
        print(f"→ Attachment upload returned HTTP {resp.status_code}. Response body:")
        print(f"'''{resp.text}'''")  # usually empty
        if resp.headers.get("Content-Type", "").startswith("application/json") and resp.text.strip():
            return resp.json()
        else:
            return None

    # Any other status is an error
    raise RuntimeError(
        f"Failed to upload evidence to run {test_run_id}:\n"
        f"  HTTP {resp.status_code} → {resp.text}"
    )


if __name__ == "__main__":
    try:
        run_id = fetch_test_run_id(TEST_EXEC_KEY, TARGET_TEST_KEY)
        print(f"🔎 Found testRunId = {run_id} for test '{TARGET_TEST_KEY}'")
    except Exception as e:
        print("❌ Error while fetching testRunId:", e)
        sys.exit(1)

    try:
        result = upload_evidence_to_run(
            test_run_id=run_id,
            filename=LOCAL_FILE_NAME,
            content_type=CONTENT_TYPE
        )
        if result is not None:
            print("✅ Evidence uploaded successfully. JSON response:")
            print(json.dumps(result, indent=2))
        else:
            print("✅ Evidence uploaded successfully (no JSON returned).")
    except Exception as e:
        print("❌ Error while uploading evidence:", e)
        sys.exit(1)