#!/usr/bin/env python3
import os
import sys
import json
import base64
import requests

# ─────────────── Configuration ───────────────
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
XRAY_TOKEN    = os.getenv("XRAY_TOKEN")

if not JIRA_BASE_URL or not XRAY_TOKEN:
    print("❌ Error: JIRA_BASE_URL and XRAY_TOKEN must be set in the environment")
    sys.exit(1)

# ─────────────── Mapping ───────────────
# For each test key, point to the file you want to attach and its MIME type.
MAPPING = {
    "HPCSVC-2003": ("filtered_settings/saml_settings_ansible_core.json", "application/json"),
    "HPCSVC-2001": ("screenshots/screenshot.png",                   "image/png"),
    # Add more testKey → (path, contentType) entries here as needed
}


def encode_file_to_b64(path: str) -> str:
    """Read a file and return its Base64‐encoded contents."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def build_payload(test_exec_key: str) -> dict:
    """
    Construct the JSON payload for the Generic Import API:
    - testExecutionKey: your dispatch input
    - info: metadata about the import
    - tests: one entry per testKey, each with its evidences array
    """
    tests = []

    for test_key, (path, mime) in MAPPING.items():
        if not os.path.isfile(path):
            print(f"⚠️  Skipping missing file for {test_key}: {path}")
            continue

        b64data = encode_file_to_b64(path)
        tests.append({
            "testKey":   test_key,
            "status":    "TODO",  # or "PASS"/"FAIL" if you know the outcome
            "evidences": [
                {
                    "data":        b64data,
                    "filename":    os.path.basename(path),
                    "contentType": mime
                }
            ]
        })

    return {
        "testExecutionKey": test_exec_key,
        "info": {
            "summary":     f"Imported execution {test_exec_key}",
            "description": "Automated import via Generic Import API",
            "revision":    "1"
        },
        "tests": tests
    }


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <JIRA_TEST_EXECUTION_KEY>")
        sys.exit(1)

    test_exec_key = sys.argv[1]
    payload       = build_payload(test_exec_key)

    if not payload["tests"]:
        print("❌ No tests to import (check your MAPPING and file paths).")
        sys.exit(1)

    url = f"{JIRA_BASE_URL}/rest/raven/1.0/import/execution"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }

    print(f"🚀 Importing {len(payload['tests'])} tests into execution {test_exec_key}…")
    resp = requests.post(url, headers=headers, json=payload)

    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(f"❌ Import failed: HTTP {resp.status_code}\n{resp.text}")
        sys.exit(1)

    result = resp.json()
    print(f"✅ Success! Imported execution {test_exec_key}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()