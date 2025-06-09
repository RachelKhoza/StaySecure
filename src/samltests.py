#!/usr/bin/env python3
import os
import sys
import json
import base64
import argparse
import requests

# ─────────────── Configuration ───────────────
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
XRAY_TOKEN    = os.getenv("XRAY_TOKEN")
if not JIRA_BASE_URL or not XRAY_TOKEN:
    print("❌ Error: JIRA_BASE_URL and XRAY_TOKEN must be set in the environment")
    sys.exit(1)

# ─────────── Mapping ───────────
# For each testKey we define:
#  • status: PASS/FAIL/TODO
#  • step_results: a list of manual-step results, each with
#      - actualResult: text for that step
#      - attachments: list of { path, contentType }
MAPPING = {
    "HPCSVC-2003": {
        "status": "PASS",
        "step_results": [
            {
                "actualResult": "Verified that the Organization exists",
                "attachments": []
            },
            {
                "actualResult": "Fetched SAML settings JSON",
                "attachments": [
                    {
                        "path":        "filtered_settings/saml_settings_ansible_core.json",
                        "contentType": "application/json"
                    }
                ]
            }
        ]
    },
    "HPCSVC-2001": {
        "status": "PASS",
        "step_results": [
            {
                "actualResult": "Verified AAP org and teams",
                "attachments": [
                    {
                        "path":        "screenshots/screenshot.png",
                        "contentType": "image/png"
                    },
                    {
                        "path":        "screenshots/aap_screenshot.png",
                        "contentType": "image/png"
                    }
                ]
            },
            {
                "actualResult": "Verified team roles per team",
                "attachments": []
            }
        ]
    },
    # …add more testKeys here…
}

def encode_file_to_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_payload(test_exec_key: str, selected_keys: list[str] | None) -> dict:
    """
    Build the JSON body for Xray's Generic Import API,
    attaching evidences to individual manual test steps.
    """
    tests = []

    for test_key, details in MAPPING.items():
        if selected_keys and test_key not in selected_keys:
            continue

        steps = []
        for step in details["step_results"]:
            ev = []
            for att in step["attachments"]:
                if not os.path.isfile(att["path"]):
                    print(f"⚠️  Skipping missing file for {test_key}: {att['path']}")
                    continue
                ev.append({
                    "data":        encode_file_to_b64(att["path"]),
                    "filename":    os.path.basename(att["path"]),
                    "contentType": att["contentType"]
                })
            steps.append({
                "status":       details["status"],
                "actualResult": step["actualResult"],
                "evidences":    ev
            })

        if not steps:
            print(f"⚠️  No steps to import for {test_key}, skipping")
            continue

        tests.append({
            "testKey": test_key,
            "status":  details["status"],
            "steps":   steps
        })

    payload = {
        "testExecutionKey": test_exec_key,
        "info": {
            "summary":     f"Imported execution {test_exec_key}",
            "description": "Automated import via Generic Import API",
            "revision":    "1"
        },
        "tests": tests
    }
    return payload

def main():
    parser = argparse.ArgumentParser(
        description="Attach files to Xray manual test steps via the Generic Import API"
    )
    parser.add_argument("test_exec_key",
        help="Jira Test Execution key (e.g. HPCSVC-2869)")
    parser.add_argument("--tests", "--test-keys", nargs="+", metavar="KEY",
        help="Only include these Test Keys (default: all in MAPPING)")
    parser.add_argument("--dry-run", action="store_true",
        help="Print the JSON payload instead of POSTing to Xray")
    args = parser.parse_args()

    payload = build_payload(args.test_exec_key, args.tests)
    if not payload["tests"]:
        print("❌ No tests to import. Check your MAPPING and file paths.")
        sys.exit(1)

    if args.dry_run:
        print("📦 DRY RUN: this is what would be sent:\n")
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    url = f"{JIRA_BASE_URL}/rest/raven/1.0/import/execution"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }

    print(f"🚀 Importing {len(payload['tests'])} tests into {args.test_exec_key}…")
    resp = requests.post(url, headers=headers, json=payload)
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(f"❌ Import failed: HTTP {resp.status_code}\n{resp.text}")
        sys.exit(1)

    print(f"✅ Success! Imported execution {args.test_exec_key}")
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    main()