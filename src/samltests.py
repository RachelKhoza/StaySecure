import os
import requests
import json
from datetime import datetime, timezone
import tempfile

# === Config ===
xray_token = os.getenv("XRAY_TOKEN")
test_exec_key = "HPCSVC-2922"
test_key = "HPCSVC-2001"
screenshot_file = "org_screenshot.png"
jira_base_url = "https://atc-int.<yourdomain>.group.net/jira"
upload_url = f"{jira_base_url}/rest/raven/1.0/import/execution"

# === Headers ===
headers = {
    "Authorization": f"Bearer {xray_token}"
}

# === Validate Screenshot
if not os.path.exists(screenshot_file):
    print(f"❌ Screenshot not found: {screenshot_file}")
    exit(1)

# === Dates
start_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
finish_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")

# === JSON Payload
xray_payload = {
    "testExecutionKey": test_exec_key,
    "info": {
        "summary": "Automated Test Execution Upload",
        "description": "Automated run with attached evidence",
        "user": "automation",
        "startDate": start_date,
        "finishDate": finish_date
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

# === Write JSON to temp file
with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tmp_json_file:
    json.dump(xray_payload, tmp_json_file)
    tmp_json_file_path = tmp_json_file.name

# === Upload via multipart/form-data
with open(screenshot_file, 'rb') as img, open(tmp_json_file_path, 'rb') as json_file:
    files = {
        'result': (os.path.basename(tmp_json_file_path), json_file, 'application/json'),
        'evidences': (os.path.basename(screenshot_file), img, 'image/png')
    }

    response = requests.post(upload_url, headers=headers, files=files)

# === Result
if response.status_code in [200, 201]:
    print(f"✅ Evidence uploaded for test {test_key} in execution {test_exec_key}")
else:
    print(f"❌ Upload failed. Status: {response.status_code}")
    print(response.text)