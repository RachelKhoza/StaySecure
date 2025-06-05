import os
import json
import requests
from datetime import datetime, timezone

# Inputs
xray_token = os.getenv("XRAY_TOKEN")
test_exec_key = "HPCSVC-2922"
test_key = "HPCSVC-2001"
screenshot_file = "org_screenshot.png"
jira_base_url = "https://atc-int.<yourdomain>.group.net/jira"
upload_url = f"{jira_base_url}/rest/raven/1.0/import/execution"

# Header
headers = {
    "Authorization": f"Bearer {xray_token}"
}

# Time formatting
start_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
finish_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")

# Payload for Xray
xray_result = {
    "testExecutionKey": test_exec_key,
    "info": {
        "summary": "Automated Execution",
        "description": "Evidence via Python",
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

# Write JSON to file
json_filename = "xray_result.json"
with open(json_filename, "w") as jf:
    json.dump(xray_result, jf)

# Upload
with open(json_filename, "rb") as result_file, open(screenshot_file, "rb") as img_file:
    files = {
        "result": (json_filename, result_file, "application/json"),
        "evidences": (os.path.basename(screenshot_file), img_file, "image/png")
    }

    response = requests.post(upload_url, headers=headers, files=files)

if response.status_code in [200, 201]:
    print(f"✅ Successfully attached evidence to {test_key} in execution {test_exec_key}")
else:
    print(f"❌ Upload failed: {response.status_code}")
    print(response.text)


    curl -X POST "https://atc-int.<yourdomain>.group.net/jira/rest/raven/1.0/import/execution" \
  -H "Authorization: Bearer <YOUR_XRAY_TOKEN>" \
  -F "result=@xray_result.json;type=application/json" \
  -F "evidences=@org_screenshot.png;type=image/png"