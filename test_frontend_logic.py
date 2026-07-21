import asyncio
import httpx
import json

async def run_test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Uploading file...")
        with open("Fake_SAP_Dataset_5000_Rows.xlsx", "rb") as f:
            res = await client.post("http://localhost:8000/api/v1/files", files={"file": f})
        
        if res.status_code not in (200, 201, 202):
            print(f"Upload failed with status {res.status_code}:", res.text)
            return
            
        data = res.json()
        file_id = data["file_id"]
        print(f"Uploaded successfully. File ID: {file_id}")
        
        print("Fetching full data...")
        res = await client.get(f"http://localhost:8000/api/v1/files/{file_id}/data")
        if res.status_code not in (200, 201):
            print(f"Fetch data failed with status {res.status_code}:", res.text)
            return
            
        full_data = res.json()
        print(f"Fetched {len(full_data['data'])} rows.")
        print(f"Truncated: {full_data['is_truncated']}")
        print(f"Total Rows: {full_data['total_rows']}")
        
        # Calculate sum of Amount in the returned data to simulate the frontend
        total_amount = sum(float(r["Amount"]) for r in full_data['data'])
        print(f"\nFrontend Simulated Total Amount: {total_amount:.2f}")
        
        # Simulate Year = 2024 filter
        filtered_2024 = [r for r in full_data['data'] if str(r.get("Year", "")) == "2024"]
        total_2024 = sum(float(r["Amount"]) for r in filtered_2024)
        print(f"Frontend Simulated Filter (Year=2024): {total_2024:.2f}")
        
        # Simulate Year = 2024 AND Category = Electronics
        filtered_both = [r for r in filtered_2024 if str(r.get("Category", "")).lower() == "electronics"]
        total_both = sum(float(r["Amount"]) for r in filtered_both)
        print(f"Frontend Simulated Filter (Year=2024 & Category=Electronics): {total_both:.2f}")

asyncio.run(run_test())
