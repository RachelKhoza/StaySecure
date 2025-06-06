import base64
import json
import requests

# ─────────── CONFIGURATION ───────────
JIRA_BASE_URL    = "https://<your-jira-domain>"   # e.g. "https://atc-int.yourcompany.net"
XRAY_USERNAME    = "<your-jira-username>"
XRAY_API_TOKEN   = "<your-jira-api-token-or-password>"

TEST_EXEC_KEY    = "HPCSVC-2922"   # the Test Execution issue key
TARGET_TEST_KEY  = "HPCSVC-2003"   # the Test (inside that execution) whose run we want
LOCAL_FILE_PATH  = "/path/to/screenshot.png"
UPLOAD_FILENAME  = "saml-configuration.png"
CONTENT_TYPE     = "image/png"
# ─────────────────────────────────────

def fetch_test_run_id(test_exec_key: str, test_key: str) -> int:
    """
    1. Calls GET /rest/raven/1.0/api/testexec/{testExecKey}/test
    2. Finds the entry where testIssueKey == test_key
    3. Returns its numeric testRunId
    """
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec/{test_exec_key}/test"
    resp = requests.get(
        url,
        auth=(XRAY_USERNAME, XRAY_API_TOKEN),
        headers={"Content-Type": "application/json"}
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch tests for execution {test_exec_key}: "
            f"{resp.status_code} → {resp.text}"
        )

    data = resp.json()
    # Example structure:
    # {
    #   "total": 2,
    #   "results": [
    #     {
    #       "testIssueKey": "HPCSVC-2002",
    #       "testExecIssueKey": "HPCSVC-2922",
    #       "testRunId": 123450,
    #       … 
    #     },
    #     {
    #       "testIssueKey": "HPCSVC-2003",
    #       "testExecIssueKey": "HPCSVC-2922",
    #       "testRunId": 123456,
    #       …
    #     }
    #   ]
    # }
    for entry in data.get("results", []):
        if entry.get("testIssueKey") == test_key:
            return entry["testRunId"]

    raise ValueError(
        f"Test key {test_key} not found in execution {test_exec_key}."
    )

def upload_evidence_to_run(test_run_id: int, file_path: str, filename: str, content_type: str):
    """
    1. Reads the local file and base64-encodes it.
    2. POSTS to /rest/raven/1.0/api/testrun/{testRunId}/attachment
    """
    # Read & encode:
    with open(file_path, "rb") as f:
        raw_bytes   = f.read()
        b64_content = base64.b64encode(raw_bytes).decode("utf-8")

    payload = {
        "data":        b64_content,
        "filename":    filename,
        "contentType": content_type
    }

    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testrun/{test_run_id}/attachment"
    resp = requests.post(
        url,
        auth=(XRAY_USERNAME, XRAY_API_TOKEN),
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload)
    )

    if resp.status_code != 200:
        raise RuntimeError(
            f"Failed to upload evidence to run {test_run_id}: "
            f"{resp.status_code} → {resp.text}"
        )

    return resp.json()

if __name__ == "__main__":
    # 1. Fetch the numeric testRunId for TEST_EXEC_KEY + TARGET_TEST_KEY
    try:
        run_id = fetch_test_run_id(TEST_EXEC_KEY, TARGET_TEST_KEY)
        print(f"🔎 Found testRunId = {run_id} for test {TARGET_TEST_KEY}")
    except Exception as e:
        print("❌ Error while fetching testRunId:", e)
        exit(1)

    # 2. Upload evidence (base64‐encoded) to that run:
    try:
        response_json = upload_evidence_to_run(
            test_run_id=run_id,
            file_path=LOCAL_FILE_PATH,
            filename=UPLOAD_FILENAME,
            content_type=CONTENT_TYPE
        )
        print("✅ Evidence uploaded successfully:")
        print(json.dumps(response_json, indent=2))
    except Exception as e:
        print("❌ Error while uploading evidence:", e)
        exit(1)