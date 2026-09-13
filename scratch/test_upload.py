import httpx
import sys

def main():
    base_url_kc = "http://localhost:8080"
    base_url_api = "http://localhost:8000/api/v1"

    # 1. Get admin token from master realm
    token_url = f"{base_url_kc}/realms/master/protocol/openid-connect/token"
    resp = httpx.post(token_url, data={
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": "admin",
        "password": "CqKiAA2CEdMWXLixQfWN3kkqVjmw72D_"
    })
    if resp.status_code != 200:
        print(f"Failed to get admin token: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    admin_token = resp.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}

    # 2. Check if user 'test_upload_user' exists in claria realm, or create/reset it
    users_url = f"{base_url_kc}/admin/realms/claria/users"
    resp = httpx.get(users_url, headers=headers_admin, params={"username": "test_upload_user"})
    users = resp.json()
    if users:
        user_id = users[0]["id"]
        print(f"Found test_upload_user (id={user_id})")
        # clear required actions
        httpx.put(f"{users_url}/{user_id}", headers=headers_admin, json={
            "enabled": True,
            "emailVerified": True,
            "requiredActions": []
        })
    else:
        print("Creating test_upload_user...")
        resp = httpx.post(users_url, headers=headers_admin, json={
            "username": "test_upload_user",
            "enabled": True,
            "emailVerified": True,
            "requiredActions": [],
            "credentials": [{"type": "password", "value": "TestPass123!", "temporary": False}]
        })
        if resp.status_code not in (201, 204):
            print(f"Failed to create user: {resp.status_code} {resp.text}")
            sys.exit(1)
        resp = httpx.get(users_url, headers=headers_admin, params={"username": "test_upload_user"})
        user_id = resp.json()[0]["id"]

    # Reset password with temporary: false
    reset_url = f"{base_url_kc}/admin/realms/claria/users/{user_id}/reset-password"
    httpx.put(reset_url, headers=headers_admin, json={"type": "password", "value": "TestPass123!", "temporary": False})

    # 3. Get user token for test_upload_user from claria realm
    user_token_url = f"{base_url_kc}/realms/claria/protocol/openid-connect/token"
    resp = httpx.post(user_token_url, data={
        "grant_type": "password",
        "client_id": "claria-frontend",
        "username": "test_upload_user",
        "password": "TestPass123!"
    })
    if resp.status_code != 200:
        print(f"Failed to get user token: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    user_token = resp.json()["access_token"]
    print("Got user token from claria realm!")

    # 4. Call /api/v1/files to test upload
    headers_user = {"Authorization": f"Bearer {user_token}"}
    files = {"file": ("test_upload.csv", b"id,val\n1,10\n2,20\n", "text/csv")}
    
    print(f"Testing file upload to {base_url_api}/files...")
    resp = httpx.post(f"{base_url_api}/files", headers=headers_user, files=files)
    print(f"Upload Status Code: {resp.status_code}")
    print(f"Upload Response: {resp.text}")

if __name__ == "__main__":
    main()
