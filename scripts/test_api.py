#!/usr/bin/env python3
"""Simple API test script for the inventory API.

Usage: export API_URL or pass as first arg.
"""
import os
import sys
import time
import requests


def main():
    api_url = os.environ.get("API_URL") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not api_url:
        print("Usage: API_URL=<url> python3 scripts/test_api.py <api_url>")
        return 2

    print(f"Testing GET {api_url}")
    r = requests.get(api_url, timeout=10)
    if r.status_code != 200:
        print("GET failed:", r.status_code, r.text)
        return 3

    items = r.json()
    if not isinstance(items, list):
        print("GET did not return a list")
        return 4

    if not items:
        print("GET returned empty list — nothing to test POST with")
        return 0

    item = items[0]
    item_id = item.get("id")
    if item_id is None:
        print("First item missing id")
        return 5

    old = bool(item.get("on_loan"))
    new = not old
    print(f"Toggling id={item_id} on_loan {old} -> {new}")

    r2 = requests.post(api_url, json={"id": int(item_id), "on_loan": new}, timeout=10)
    if r2.status_code != 200:
        print("POST failed:", r2.status_code, r2.text)
        return 6

    # allow eventual consistency briefly
    time.sleep(1)
    r3 = requests.get(api_url, timeout=10)
    if r3.status_code != 200:
        print("GET after POST failed:", r3.status_code, r3.text)
        return 7

    items2 = r3.json()
    found = None
    for it in items2:
        if it.get("id") == item_id:
            found = it
            break

    if found is None:
        print("Item disappeared after update")
        return 8

    if bool(found.get("on_loan")) != new:
        print("Update didn't persist. Expected", new, "got", found.get("on_loan"))
        return 9

    print("Test passed: update persisted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
