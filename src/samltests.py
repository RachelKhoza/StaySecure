def fetch_test_run_id(test_exec_key, test_key):
    url = f"{JIRA_BASE_URL}/rest/raven/1.0/api/testexec/{test_exec_key}/test"
    headers = {
      "Authorization": f"Bearer {XRAY_TOKEN}",
      "Content-Type":  "application/json"
    }

    max_retries = 5
    base_backoff = 3

    for attempt in range(1, max_retries + 1):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            results = data if isinstance(data, list) else data.get("results", []) or data.get("values", [])
            for entry in results:
                if entry.get("key") == test_key:
                    return entry["id"]
            raise ValueError(f"Test key '{test_key}' not found in execution '{test_exec_key}'")
        
        if resp.status_code == 429:
            ra = resp.headers.get("Retry-After")
            sleep_for = int(ra) if ra and ra.isdigit() else base_backoff * attempt
            print(f"⚠️ GET rate-limited (attempt {attempt}/{max_retries}), sleeping {sleep_for}s…")
            time.sleep(sleep_for)
            continue

        resp.raise_for_status()

    raise RuntimeError(f"Failed to fetch run ID after {max_retries} retries (last code {resp.status_code})")