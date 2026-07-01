import sys
import os
import json
import requests

def query_backend_scores():
    url = "http://localhost:8000/rank?query_text=Senior%20Backend%20Developer.%20Python%20FastAPI%20AWS%20Docker%20Kubernetes."
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    query_backend_scores()
