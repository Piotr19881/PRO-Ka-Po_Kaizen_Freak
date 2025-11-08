"""
Test habit API - sprawdzamy co faktycznie zwraca endpoint /api/habits/columns
"""

import requests
import json

# User ID
user_id = "207222a2-3845-40c2-9bea-cd5bbd6e15f6"

# Test endpoint
url = "http://127.0.0.1:8000/api/habits/columns"
params = {"user_id": user_id}

print(f"Testing: GET {url}")
print(f"Params: {params}")
print("-" * 80)

try:
    response = requests.get(url, params=params, timeout=10)
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print("-" * 80)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response type: {type(data)}")
        print(f"Response length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")
        print("-" * 80)
        print("Full response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("-" * 80)
        
        if isinstance(data, list) and len(data) > 0:
            print(f"First item type: {type(data[0])}")
            print(f"First item: {data[0]}")
    else:
        print(f"Error response:")
        print(response.text)
        
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()
