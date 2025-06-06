import base64
import json
import requests
import os
import sys

# ─────────── CONFIGURATION ───────────
JIRA_BASE_URL   = "https://<your-jira-domain>"    # e.g. "https://atc-int.yourcompany.net"
XRAY_TOKEN      = "<YOUR_BEARER_TOKEN>"

# The Test Execution and Test you want to operate on:
TEST_EXEC_KEY   = "HPCSVC-2922"    # e.g. the Test Execution issue key
TARGET_TEST_KEY = "HPCSVC-2003"    # e.g. the Test (inside that execution)

# The evidence file (must live in the same directory as this script):
LOCAL_FILE_NAME = "saml-configuration.png"
CONTENT_TYPE    = "image/png"
# ─────────────────────────────────────

def fetch_test_run_id(test_exec_key: str, test_key: str) -> int:
    """
    1. Calls GET /rest/raven/1.0/api/testexec/{testExecKey}/test
    2. The response is a LIST of test‐run objects, each of which looks like:
       {
         "id":  36841106,      <-- this is the numeric testRunId
         "status": "TODO",
         "archived": false,
         "key": "HPCSVC-2003", <-- this is the Test issue key
         "rank": 1
       },
       { … next test … }
    3. We loop through that list, find the object whose "key" matches test_key,
       and return its "id".
    """
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec/{test_exec_key}/test"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch tests for execution {test_exec_key}: "
            f"HTTP {resp.status_code} → {resp.text}"
        )

    data = resp.json()
    # Data should be a list; if it is wrapped in a dict, extract "results" or "values"
    if not isinstance(data, list):
        data = data.get("results", []) or data.get("values", [])

    for entry in data:
        # The Test issue key is in entry["key"]
        if entry.get("key") == test_key:
            return entry["id"]

    raise ValueError(
        f"Test key '{test_key}' not found in execution '{test_exec_key}'."
    )


def upload_evidence_to_run(test_run_id: int, filename: str, content_type: str):
    """
    1. Reads the local file (same directory) and base64‐encodes it.
    2. POSTS to /rest/raven/1.0/api/testrun/{testRunId}/attachment
    3. Treats HTTP 200, 201, or 204 as “success” (Xray often returns 204 No Content).
    4. Returns any JSON if present, or None if the body is empty.
    """
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

    # Xray often returns 204 No Content (or 200/201) on success
    if resp.status_code in (200, 201, 204):
        print(f"→ Attachment upload returned HTTP {resp.status_code}. Response body:")
        print(f"'''{resp.text}'''")  # usually empty

        if resp.headers.get("Content-Type", "").startswith("application/json") and resp.text.strip():
            return resp.json()
        else:
            return None

    # Any other status is treated as an error
    raise RuntimeError(
        f"Failed to upload evidence to run {test_run_id}: "
        f"HTTP {resp.status_code} → {resp.text}"
    )


def update_test_run_status(test_run_id: int, new_status: str):
    """
    Marks a single Test Run as PASS (or FAIL, TODO, etc.).
    1. PUT /rest/raven/1.0/api/testrun/{testRunId}/status
       with JSON { "status": "<new_status>" }
    2. On success, returns the returned JSON (if any), otherwise None.
    """
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testrun/{test_run_id}/status"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }
    payload = { "status": new_status }

    resp = requests.put(url, headers=headers, data=json.dumps(payload))
    if resp.status_code == 200:
        # Xray may return a small JSON response confirming the update
        print(f"→ Status update returned HTTP 200. Response body:")
        print(f"'''{resp.text}'''")
        if resp.text.strip():
            try:
                return resp.json()
            except json.JSONDecodeError:
                return None
        else:
            return None

    raise RuntimeError(
        f"Failed to update status for run {test_run_id}: "
        f"HTTP {resp.status_code} → {resp.text}"
    )


if __name__ == "__main__":
    # Step 1: Find the testRunId for (TEST_EXEC_KEY + TARGET_TEST_KEY)
    try:
        run_id = fetch_test_run_id(TEST_EXEC_KEY, TARGET_TEST_KEY)
        print(f"🔎 Found testRunId = {run_id} for test '{TARGET_TEST_KEY}'")
    except Exception as e:
        print("❌ Error while fetching testRunId:", e)
        sys.exit(1)

    # Step 2: Upload the evidence (screenshot) to that run
    try:
        upload_result = upload_evidence_to_run(
            test_run_id=run_id,
            filename=LOCAL_FILE_NAME,
            content_type=CONTENT_TYPE
        )
        print("✅ Evidence upload step succeeded.")
    except Exception as e:
        print("❌ Error while uploading evidence:", e)
        sys.exit(1)

    # Step 3: Mark that same run as PASS
    try:
        status_result = update_test_run_status(
            test_run_id=run_id,
            new_status="PASS"
        )
        print("✅ Test Run status updated to PASS.")
        if status_result is not None:
            print("Returned JSON:")
            print(json.dumps(status_result, indent=2))
    except Exception as e:
        print("❌ Error while updating test run status:", e)
        sys.exit(1)

    print("🎉 All done! The screenshot is attached and the test is now PASS.")