#!/usr/bin/env python3
"""Quick test script to check analytics API responses."""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(endpoint, params=None):
    """Test an API endpoint and print the response."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=5)
        print(f"\n{'='*60}")
        print(f"Endpoint: {endpoint}")
        if params:
            print(f"Params: {params}")
        print(f"Status: {response.status_code}")
        print(f"{'='*60}")

        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.text}")
    except requests.exceptions.ConnectionError:
        print(f"ERROR: Could not connect to {BASE_URL}")
        print("Make sure the server is running: python server.py")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    return True

def main():
    """Test all analytics endpoints."""
    print("Testing Analytics API Endpoints")
    print("Ensure server is running on http://127.0.0.1:8000")

    # Test each endpoint
    endpoints = [
        ("/api/analytics/summary", {"period": "30d"}),
        ("/api/analytics/equity", {"period": "30d"}),
        ("/api/analytics/trades", {"period": "90d", "limit": 10}),
        ("/api/analytics/trade_stats", {"period": "90d"}),
        ("/api/analytics/positions", None),
    ]

    for endpoint, params in endpoints:
        if not test_endpoint(endpoint, params):
            break

    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
