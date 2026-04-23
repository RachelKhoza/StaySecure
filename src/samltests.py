#!/usr/bin/env python3
import requests
from datetime import datetime
import sys

# ──────────────────────────────────────────────────────────────────────────────
# 🔧  HARDCODED CONFIGURATION — adjust these before you run
# ──────────────────────────────────────────────────────────────────────────────

JIRA_BASE_URL   = "https://mydom.atlassian.net"
JIRA_API_TOKEN  = "YOUR_API_TOKEN_HERE"
SRC_TESTCASE    = "CORE-123"      # the Test Case you want to clone

# ──────────────────────────────────────────────────────────────────────────────
# 🛠  END OF CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "Authorization": f"Bearer {JIRA_API_TOKEN}",
    "Content-Type":  "application/json",
    "X-Atlassian-Token": "no-check",
}
XRAY_CLONE = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testcase/{{}}/clone"
XRAY_EXEC  = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec"

def clone_testcase(key):
    url = XRAY_CLONE.format(key)
    payload = {
      "fields": {
        "summary": f"{key} clone {datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
      }
    }
    r = requests.post(url, headers=HEADERS, json=payload)
    r.raise_for_status()
    return r.json()["key"]

def create_test_execution(test_key):
    exec_headers = HEADERS.copy()
    exec_headers.pop("X-Atlassian-Token", None)
    payload = {
      "info": {
        "summary":     f"Exec for {test_key}",
        "description": f"Automated exec for {test_key}",
        "issuetype":   "Test Execution"
      },
      "tests": [{"testKey": test_key}]
    }
    r = requests.post(XRAY_EXEC, headers=exec_headers, json=payload)
    r.raise_for_status()
    return r.json()["testExecIssue"]["key"]

def main():
    print(f"🔍 Cloning Test Case {SRC_TESTCASE}…")
    new_tc = clone_testcase(SRC_TESTCASE)
    print(f"✅ New Test Case: {new_tc}")

    print(f"🔍 Creating Test Execution for {new_tc}…")
    new_exec = create_test_execution(new_tc)
    print(f"✅ New Test Execution: {new_exec}")

if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print("❌ HTTP Error:", e.response.status_code, e.response.text)
        sys.exit(1)
    except Exception as e:
        print("❌ Error:", e)
        sys.exit(2)