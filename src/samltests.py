import os
import requests
import json

# === Config ===
xray_token = os.getenv("JIRA_API_TOKEN")
test_exec_key = os.getenv("JIRA_ISSUE_KEY")       # e.g. HPCSVC-2619 (Test Execution)
test_key = os.getenv("XRAY_TEST_KEY")             # e.g. HPCSVC-2003 (Test inside the execution)
screenshot_file = "screenshots/screenshot.png"

# === Fixed INT Jira base URL for Xray
jira_base_url = "https://atc-int.yourdomain.group.net/jira"
upload_url = f"{jira_base_url}/rest/raven/1.0/import/execution"

# === Headers
headers = {
    "Authorization": f"Bearer {xray_token}"
}

# === Xray JSON Payload for Execution + Evidence
xray_payload = {
    "testExecutionKey": test_exec_key,
    "info": {
        "summary": "Automated Test Execution Upload",
        "description": "Automated run with attached evidence",
        "user": "automation",
        "startDate": "2025-06-05T12:00:00+0000",
        "finishDate": "2025-06-05T12:02:00+0000"
    },
    "tests": [
        {
            "testKey": test_key,
            "status": "PASS",
            "evidences": [
                {
                    "filename": os.path.basename(screenshot_file),
                    "contentType": "image/png"
                }
            ]
        }
    ]
}

# === Validate screenshot path
if not os.path.exists(screenshot_file):
    print(f"❌ Screenshot not found: {screenshot_file}")
    exit(1)

# === Prepare multipart form-data
with open(screenshot_file, 'rb') as img:
    files = {
        'result': (None, json.dumps(xray_payload), 'application/json'),
        'evidences': (os.path.basename(screenshot_file), img, 'image/png')
    }

    response = requests.post(upload_url, headers=headers, files=files)

# === Result
if response.status_code in [200, 201]:
    print(f"✅ Evidence successfully attached to test {test_key} in execution {test_exec_key}")
else:
    print(f"❌ Upload failed. Status: {response.status_code}")
    print(response.text)