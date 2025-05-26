import os
import requests
from requests.auth import HTTPBasicAuth

# Replace with your actual values
jira_base_url = "https://your-domain.atlassian.net"
issue_key = "ABC-123"  # Your Jira test case or test execution key
username = os.getenv("JIRA_EMAIL")
api_token = os.getenv("JIRA_API_TOKEN")
screenshot_path = "screenshot.png"  # Replace with your screenshot path

# Endpoint to attach files to a Jira issue
url = f"{jira_base_url}/rest/api/2/issue/{issue_key}/attachments"

# Headers
headers = {
    "X-Atlassian-Token": "no-check"
}

# Open the image file
with open(screenshot_path, "rb") as f:
    files = {
        "file": (os.path.basename(screenshot_path), f, "image/png")
    }

    # Send POST request
    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(username, api_token),
        files=files
    )

# Output result
if response.status_code == 200 or response.status_code == 201:
    print(f"✅ Screenshot uploaded successfully to {issue_key}")
else:
    print(f"❌ Failed to upload screenshot. Status: {response.status_code}")
    print(response.text)