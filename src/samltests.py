import base64
import json
import requests
import os
import sys

# ─────────── CONFIGURATION ───────────
JIRA_BASE_URL   = "https://<your-jira-domain>"   # e.g. "https://atc-int.yourcompany.net"
XRAY_TOKEN      = "<YOUR_BEARER_TOKEN>"

TEST_EXEC_KEY   = "HPCSVC-2922"   # the Test Execution issue key
TARGET_TEST_KEY = "HPCSVC-2003"   # the Test (inside that execution) whose run we want

# Just the filename (assumes the file is in the same directory as this script)
LOCAL_FILE_NAME = "saml-configuration.png"
CONTENT_TYPE    = "image/png"
# ─────────────────────────────────────


def fetch_test_run_id(test_exec_key: str, test_key: str) -> int:
    """
    1. Calls GET /rest/raven/1.0/api/testexec/{testExecKey}/test  
    2. Since the response is a JSON array (list) of objects, we iterate over that list.  
    3. Find the entry where entry["testIssueKey"] == test_key and return its numeric testRunId.
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
            f"{resp.status_code} → {resp.text}"
        )

    data = resp.json()
    # At this point, `data` is typically a list of objects like:
    # [
    #   {
    #     "testIssueKey":    "HPCSVC-2002",
    #     "testExecIssueKey": "HPCSVC-2922",
    #     "testRunId":       123450,
    #     … 
    #   },
    #   {
    #     "testIssueKey":    "HPCSVC-2003",
    #     "testExecIssueKey": "HPCSVC-2922",
    #     "testRunId":       123456,
    #     …
    #   },
    #   …
    # ]
    if isinstance(data, list):
        entries = data
    else:
        # (defensive) if Xray ever returns a dict with "results": [...]
        entries = data.get("results", [])

    for entry in entries:
        # key in each entry is exactly "testIssueKey" (case-sensitive)
        if entry.get("testIssueKey") == test_key:
            return entry["testRunId"]

    raise ValueError(
        f"Test key '{test_key}' not found in execution '{test_exec_key}'."
    )


def upload_evidence_to_run(test_run_id: int, filename: str, content_type: str):
    """
    1. Reads the local file (same directory) and base64-encodes it.
    2. POSTS to /rest/raven/1.0/api/testrun/{testRunId}/attachment with Bearer auth.
    """
    # Ensure the file actually exists in the current working directory:
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Cannot find '{filename}' in {os.getcwd()}")

    # Read & base64‐encode the file
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
    # 1. Fetch the numeric testRunId for (TEST_EXEC_KEY + TARGET_TEST_KEY)
    try:
        run_id = fetch_test_run_id(TEST_EXEC_KEY, TARGET_TEST_KEY)
        print(f"🔎 Found testRunId = {run_id} for test '{TARGET_TEST_KEY}'")
    except Exception as e:
        print("❌ Error while fetching testRunId:", e)
        sys.exit(1)

    # 2. Upload evidence (base64‐encoded) to that run (uses ONLY the filename)
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