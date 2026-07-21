import requests
import json
import uuid

SESSION_ID = "12345678-1234-1234-1234-123456789012"
URL = "http://localhost:8000/api/v1/files"

with open("test_data.csv", "rb") as f:
    files = {"file": f}
    headers = {"X-Session-ID": SESSION_ID}
    response = requests.post(URL, files=files, headers=headers)
    print("Upload response:", response.status_code)
    data = response.json()
    print("Response json:", json.dumps(data, indent=2))
    
    file_id = data.get("file_id")
    
    # Optional: We can pre-save a chart to test backwards compatibility
    if file_id:
        cfg = {
            "charts": [
                {
                    "id": str(uuid.uuid4()),
                    # Notice we explicitly DO NOT send 'type' to test backwards compatibility
                    "chart_type": "bar",
                    "chart_spec": {
                        "_meta": {"title": "Old Chart", "xCol": "name", "yCol": "sales"},
                        "xAxis": {"type": "category", "data": ["Apple", "Banana"]},
                        "yAxis": {"type": "value"},
                        "series": [{"type": "bar", "data": [150.5, 80]}]
                    },
                    "layout": {"x": 0, "y": 0, "w": 6, "h": 4}
                }
            ]
        }
        res2 = requests.post(f"http://localhost:8000/api/v1/files/{file_id}/dashboard-config", json=cfg, headers=headers)
        print("Pre-save config response:", res2.status_code)
