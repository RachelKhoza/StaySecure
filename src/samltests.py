#!/usr/bin/env python3
import os, sys, json, base64, argparse, requests

# ───────────── Configuration ─────────────
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
XRAY_TOKEN    = os.getenv("XRAY_TOKEN")
if not (JIRA_BASE_URL and XRAY_TOKEN):
    print("❌ Please export JIRA_BASE_URL and XRAY_TOKEN")
    sys.exit(1)

# ─────────── Mapping ───────────
# testKey → {
#   status:      "PASS"/"FAIL"/"TODO",
#   attachments: { step_index: [ { path, contentType }, … ] }
# }
MAPPING = {
    "HPCSVC-2003": {
        "status": "PASS",
        "attachments": {
            # put your JSON file on step 0 (the first manual step)
            0: [{
                "path":        "filtered_settings/saml_settings_ansible_core.json",
                "contentType": "application/json"
            }]
        }
    },
    "HPCSVC-2001": {
        "status": "PASS",
        "attachments": {
            # screenshot.png → step 0
            0: [{
                "path":        "screenshots/screenshot.png",
                "contentType": "image/png"
            }],
            # aap_screenshot.png → step 1
            1: [{
                "path":        "screenshots/aap_screenshot.png",
                "contentType": "image/png"
            }]
        }
    },
    # …add more testKeys here…
}

def encode_file_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def build_payload(exec_key, selected=None):
    tests = []
    for tkey, details in MAPPING.items():
        if selected and tkey not in selected:
            continue

        step_entries = []
        for idx, atts in details["attachments"].items():
            ev = []
            for att in atts:
                if not os.path.isfile(att["path"]):
                    print(f"⚠️  Missing {att['path']} for {tkey} step {idx}, skipping")
                    continue
                ev.append({
                    "data":        encode_file_to_b64(att["path"]),
                    "filename":    os.path.basename(att["path"]),
                    "contentType": att["contentType"]
                })

            if not ev:
                continue

            step_entries.append({
                "index":       idx,
                "status":      details["status"],
                "actualResult":"",
                "evidence":    ev
            })

        if step_entries:
            tests.append({
                "testKey": tkey,
                "status":  details["status"],
                "steps":   step_entries
            })

    return {
        "testExecutionKey": exec_key,
        "info": {
            "summary":     f"Import {exec_key}",
            "description": "Attach step-level files via Generic Import API",
            "revision":    "1"
        },
        "tests": tests
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("exec_key", help="Test Execution key (e.g. HPCSVC-2869)")
    p.add_argument("--tests",  nargs="+", help="Only these testKeys (default: all)")
    p.add_argument("--dry-run", action="store_true",
                   help="Print JSON payload and exit")
    args = p.parse_args()

    payload = build_payload(args.exec_key, args.tests)
    if not payload["tests"]:
        print("❌ Nothing to import. Check MAPPING and file paths.")
        sys.exit(1)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        sys.exit(0)

    url = f"{JIRA_BASE_URL}/rest/raven/1.0/import/execution"
    headers = {
        "Authorization": f"Bearer {XRAY_TOKEN}",
        "Content-Type":  "application/json"
    }

    print(f"🚀 Importing {len(payload['tests'])} tests into {args.exec_key}")
    resp = requests.post(url, headers=headers, json=payload)
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(f"❌ Import failed: HTTP {resp.status_code}\n{resp.text}")
        sys.exit(1)

    print("✅ Success!", json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    main()