import os
import json
import requests
from datetime import datetime, timezone

# Inputs
# Ensure XRAY_TOKEN is set as an environment variable
xray_token = os.getenv("XRAY_TOKEN")
if not xray_token:
    print("Error: XRAY_TOKEN environment variable not set.")
    exit()

test_exec_key = "HPCSVC-2922"  # Your Test Execution Key
test_key = "HPCSVC-2001"      # Your Test Key
screenshot_file = "org_screenshot.png"  # Ensure this file exists

# Replace with your actual Jira base URL
jira_base_url = "https://atc-int.YOUR_DOMAIN.net/jira"
upload_url = f"{jira_base_url}/rest/raven/1.0/import/execution"

# Header for authentication
headers = {
    "Authorization": f"Bearer {xray_token}"
}

# Time formatting for Xray
# Xray expects UTC time, usually in ISO 8601 format.
# The +0000 offset explicitly denotes UTC.
start_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
finish_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")

# Payload for Xray (Xray JSON format)
# The 'filename' in evidences should be the basename of the file.
actual_screenshot_basename = os.path.basename(screenshot_file)

xray_result = {
    "testExecutionKey": test_exec_key,
    "info": {
        "summary": "Automated Execution via Python",
        "description": "Test execution results and evidence uploaded using a Python script.",
        "user": "automation_user", # Optional: specify the user if needed
        "startDate": start_date,
        "finishDate": finish_date
        # You can add other info fields like "version", "testPlanKey", etc.
    },
    "tests": [
        {
            "testKey": test_key,
            "start": start_date, # Optional: test-specific start date
            "finish": finish_date, # Optional: test-specific finish date
            "status": "PASS",  # Or FAIL, TODO, EXECUTING, etc.
            "evidences": [
                {
                    "filename": actual_screenshot_basename,
                    "contentType": "image/png"
                    # For non-image files, adjust contentType accordingly (e.g., "text/plain", "application/pdf")
                }
            ]
            # You can add "comment", "steps", "defects", "customFields", etc. here
        }
    ]
}

# Write JSON payload to a file
json_filename = "xray_result.json"
try:
    with open(json_filename, "w") as jf:
        json.dump(xray_result, jf, indent=4) # Added indent for readability of the JSON file
    print(f"Xray JSON payload written to {json_filename}")
except IOError as e:
    print(f"Error writing JSON to file {json_filename}: {e}")
    exit()

# Upload JSON results and evidence file(s)
try:
    with open(json_filename, "rb") as result_file_handle, \
         open(screenshot_file, "rb") as evidence_file_handle:

        # Corrected 'files' dictionary structure
        # - The JSON result part is commonly named "results"
        # - The evidence file part name should match the 'filename' in the JSON payload
        files_to_upload = {
            "results": (json_filename, result_file_handle, "application/json"),
            actual_screenshot_basename: (actual_screenshot_basename, evidence_file_handle, "image/png")
        }

        print(f"Uploading to: {upload_url}")
        print(f"Files to upload: {list(files_to_upload.keys())}")

        response = requests.post(upload_url, headers=headers, files=files_to_upload)

        # Check response
        if response.status_code == 200 or response.status_code == 201:
            print(f"Successfully uploaded results and evidence for test execution {test_exec_key}.")
            try:
                print("Response from server:", response.json()) # Xray often returns info about the imported execution
            except json.JSONDecodeError:
                print("Response from server (non-JSON):", response.text)
        else:
            print(f"Error uploading to Xray. Status Code: {response.status_code}")
            print("Response body:", response.text)

except FileNotFoundError as e:
    print(f"Error: File not found. Please ensure '{json_filename}' and '{screenshot_file}' exist. Details: {e}")
except requests.exceptions.RequestException as e:
    print(f"An error occurred during the web request: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")