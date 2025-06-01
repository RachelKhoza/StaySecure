
import os
import requests

def upload_screenshot_to_jira(jira_url, issue_key, auth):
    screenshot_path = "screenshots/screenshot.png"
    upload_url = f"{jira_url}/rest/api/2/issue/{issue_key}/attachments"
    headers = {
        "X-Atlassian-Token": "no-check"
    }

    if not os.path.isfile(screenshot_path):
        print(f"❌ Screenshot not found at path: {screenshot_path}")
        return False

    with open(screenshot_path, 'rb') as f:
        files = {'file': (os.path.basename(screenshot_path), f)}
        response = requests.post(upload_url, headers=headers, files=files, auth=auth)

    if response.status_code in (200, 201):
        print(f"✅ Screenshot uploaded successfully to Jira issue {issue_key}")
        return True
    else:
        print(f"❌ Failed to upload screenshot. Status: {response.status_code}")
        print(response.text)
        return False

def transition_issue_to_pass(jira_url, issue_key, auth):
    transition_url = f"{jira_url}/rest/api/2/issue/{issue_key}/transitions"
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.get(transition_url, headers=headers, auth=auth)
    if response.status_code != 200:
        print(f"❌ Failed to fetch transitions. Status: {response.status_code}")
        print(response.text)
        return

    transitions = response.json().get("transitions", [])
    pass_transition_id = None

    for t in transitions:
        if "pass" in t['name'].lower() or "done" in t['name'].lower():
            pass_transition_id = t["id"]
            break

    if not pass_transition_id:
        print("❌ No suitable 'PASS' or 'Done' transition found.")
        print("Available transitions:", [t['name'] for t in transitions])
        return

    payload = {
        "transition": {
            "id": pass_transition_id
        }
    }

    post_response = requests.post(transition_url, json=payload, headers=headers, auth=auth)
    if post_response.status_code == 204:
        print(f"✅ Jira issue {issue_key} marked as PASSED.")
    else:
        print(f"❌ Failed to transition issue: {post_response.status_code}")
        print(post_response.text)

def main():
    # Load environment variables or use defaults
    jira_env = os.getenv("JIRA_ENV", "int")
    jira_username = os.getenv("JIRA_USERNAME")
    jira_token = os.getenv("JIRA_API_TOKEN")
    jira_issue_key = os.getenv("JIRA_ISSUE_KEY")

    base_urls = {
        "int": "https://atc-int.yourdomain.group.net/jira",
        "prod": "https://atc.yourdomain.group.net/jira"
    }

    if not all([jira_username, jira_token, jira_issue_key]):
        print("❌ Missing required environment variables.")
        return

    if jira_env not in base_urls:
        print(f"❌ Invalid JIRA_ENV '{jira_env}'. Use one of {list(base_urls.keys())}")
        return

    jira_url = base_urls[jira_env]
    auth = (jira_username, jira_token)

    # Upload and transition
    if upload_screenshot_to_jira(jira_url, jira_issue_key, auth):
        transition_issue_to_pass(jira_url, jira_issue_key, auth)

if __name__ == "__main__":
    main()
