import httpx
import sys

def main():
    base_url = "http://localhost:8080"
    username = "admin"
    password = "CqKiAA2CEdMWXLixQfWN3kkqVjmw72D_"

    # 1. Get admin token from master realm
    token_url = f"{base_url}/realms/master/protocol/openid-connect/token"
    resp = httpx.post(token_url, data={
        "grant_type": "password",
        "client_id": "admin-cli",
        "username": username,
        "password": password
    })
    if resp.status_code != 200:
        print(f"Failed to get admin token: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 2. Get clients in claria realm
    clients_url = f"{base_url}/admin/realms/claria/clients"
    resp = httpx.get(clients_url, headers=headers, params={"clientId": "claria-frontend"})
    if resp.status_code != 200:
        print(f"Failed to get clients: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    clients = resp.json()
    if not clients:
        print("claria-frontend client not found")
        sys.exit(1)

    client = clients[0]
    client_uuid = client["id"]
    print(f"Found claria-frontend with UUID: {client_uuid}")
    print(f"Current redirectUris: {client.get('redirectUris')}")
    print(f"Current webOrigins: {client.get('webOrigins')}")

    # 3. Add wildcard redirectUris and webOrigins
    redirect_uris = set(client.get("redirectUris", []))
    redirect_uris.add("*")
    redirect_uris.add("http://localhost:5173/*")
    redirect_uris.add("https://*.trycloudflare.com/*")
    
    web_origins = set(client.get("webOrigins", []))
    web_origins.add("*")
    web_origins.add("+")
    web_origins.add("http://localhost:5173")
    web_origins.add("https://*.trycloudflare.com")

    client["redirectUris"] = list(redirect_uris)
    client["webOrigins"] = list(web_origins)

    # 4. Update client
    update_url = f"{base_url}/admin/realms/claria/clients/{client_uuid}"
    resp = httpx.put(update_url, headers=headers, json=client)
    if resp.status_code == 204:
        print("Successfully updated claria-frontend redirectUris and webOrigins to allow all hostnames/tunnels!")
    else:
        print(f"Failed to update client: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    main()
