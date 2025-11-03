import requests
import json

# Test endpoint pomodoro/all
url = "http://127.0.0.1:8000/api/pomodoro/all"
token_file = r"C:\Users\probu\Desktop\Aplikacje komercyjne\PRO-Ka-Po_Kaizen_Freak\PRO-Ka-Po_Kaizen_Freak\data\tokens.json"

# Odczytaj token
with open(token_file, 'r') as f:
    tokens = json.load(f)
    access_token = tokens.get('access_token')

if not access_token:
    print("ERROR: Brak access_token w tokens.json")
    exit(1)

headers = {
    "Authorization": f"Bearer {access_token}"
}

print(f"Testing: GET {url}")
print(f"Token: {access_token[:20]}...")

response = requests.get(url, headers=headers)
print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text[:500]}")

if response.status_code == 200:
    data = response.json()
    print(f"\nTopics: {len(data.get('topics', []))}")
    print(f"Sessions: {len(data.get('sessions', []))}")
