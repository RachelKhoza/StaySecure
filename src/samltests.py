#!/usr/bin/env python3
import sys
import requests
import json
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# ▶️  CONFIGURATION: Fill these in (or override SRC_TESTCASE via command-line)
# ──────────────────────────────────────────────────────────────────────────────

JIRA_BASE_URL = "https://your-domain.atlassian.net"      # e.g. https://acme.atlassian.net
JIRA_API_TOKEN = "YOUR_JIRA_API_TOKEN_HERE"              # paste your API token
SRC_TESTCASE = "CORE-123"                                # default Test Case key

# ──────────────────────────────────────────────────────────────────────────────
# 🚀  You can also override the source Test Case by passing it as the first
#     argument:
#        python clone_and_exec.py ORG-456
# ──────────────────────────────────────────────────────────────────────────────

if len(sys.argv) > 1:
    SRC_TESTCASE = sys.argv[1]

# ──────────────────────────────────────────────────────────────────────────────
# 📦  Prepare HTTP headers for Bearer auth
# ──────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "Authorization": f"Bearer {JIRA_API_TOKEN}",
    "Content-Type": "application/json",
    # Only needed on clone:
    "X-Atlassian-Token": "no-check",
}

# ──────────────────────────────────────────────────────────────────────────────
# 🔄  Clone a Test Case
# ──────────────────────────────────────────────────────────────────────────────

def clone_testcase(testcase_key: str) -> str:
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{testcase_key}/clone"
    payload = {
        "fields": {
            "summary": f"{testcase_key} clone {datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        }
    }
    resp = requests.post(url, headers=HEADERS, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["key"]

# ──────────────────────────────────────────────────────────────────────────────
# 📋  Create a Test Execution in Xray for a given Test Case
# ──────────────────────────────────────────────────────────────────────────────

def create_test_execution(testcase_key: str) -> str:
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec"
    # Remove the X-Atlassian-Token header for this call
    exec_headers = HEADERS.copy()
    exec_headers.pop("X-Atlassian-Token", None)

    payload = {
        "info": {
            "summary": f"Exec for {testcase_key}",
            "description": f"Automated execution for {testcase_key}",
            "issuetype": "Test Execution"
        },
        "tests": [{"testKey": testcase_key}]
    }
    resp = requests.post(url, headers=exec_headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["testExecIssue"]["key"]

# ──────────────────────────────────────────────────────────────────────────────
# 🎬  Main flow
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print(f"🔍 Cloning Test Case {SRC_TESTCASE} …")
    new_tc = clone_testcase(SRC_TESTCASE)
    print(f"✅ New Test Case key: {new_tc}")

    print(f"🔍 Creating Test Execution for {new_tc} …")
    new_exec = create_test_execution(new_tc)
    print(f"✅ New Test Execution key: {new_exec}")

if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as e:
        print(f"❌ HTTP error: {e.response.status_code} {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(2)