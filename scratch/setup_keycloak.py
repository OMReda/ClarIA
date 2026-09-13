import asyncio
import httpx

async def setup():
    admin_user = "admin"
    admin_password = "CqKiAA2CEdMWXLixQfWN3kkqVjmw72D_"
    
    # 1. Get master token
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "http://localhost:8080/realms/master/protocol/openid-connect/token",
            data={
                "client_id": "admin-cli",
                "username": admin_user,
                "password": admin_password,
                "grant_type": "password"
            }
        )
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        # 2. Create claria-admin client
        res = await client.post(
            "http://localhost:8080/admin/realms/claria/clients",
            headers=headers,
            json={
                "clientId": "claria-admin",
                "enabled": True,
                "clientAuthenticatorType": "client-secret",
                "secret": "claria-admin-secret-12345",
                "serviceAccountsEnabled": True,
                "publicClient": False,
                "standardFlowEnabled": False,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False
            }
        )
        print("Create client:", res.status_code, res.text)
        
        # Get client UUID
        res = await client.get(
            "http://localhost:8080/admin/realms/claria/clients?clientId=claria-admin",
            headers=headers
        )
        client_uuid = res.json()[0]["id"]
        
        # 3. Get realm-management client UUID
        res = await client.get(
            "http://localhost:8080/admin/realms/claria/clients?clientId=realm-management",
            headers=headers
        )
        realm_mgmt_uuid = res.json()[0]["id"]
        
        # 4. Get manage-users role
        res = await client.get(
            f"http://localhost:8080/admin/realms/claria/clients/{realm_mgmt_uuid}/roles/manage-users",
            headers=headers
        )
        manage_users_role = res.json()
        
        # 5. Get service account user UUID for claria-admin
        res = await client.get(
            f"http://localhost:8080/admin/realms/claria/clients/{client_uuid}/service-account-user",
            headers=headers
        )
        service_account_uuid = res.json()["id"]
        
        # 6. Assign manage-users role to service account
        res = await client.post(
            f"http://localhost:8080/admin/realms/claria/users/{service_account_uuid}/role-mappings/clients/{realm_mgmt_uuid}",
            headers=headers,
            json=[manage_users_role]
        )
        print("Assign role:", res.status_code, res.text)
        
        # 7. Create adminuser
        res = await client.post(
            "http://localhost:8080/admin/realms/claria/users",
            headers=headers,
            json={
                "username": "adminuser",
                "email": "admin@claria.local",
                "firstName": "Admin",
                "lastName": "User",
                "enabled": True,
                "emailVerified": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": "admin",
                        "temporary": False
                    }
                ]
            }
        )
        print("Create adminuser:", res.status_code, res.text)
        
        # 8. Assign admin role to adminuser
        res = await client.get(
            "http://localhost:8080/admin/realms/claria/users?username=adminuser",
            headers=headers
        )
        if res.status_code == 200 and len(res.json()) > 0:
            admin_uuid = res.json()[0]["id"]
            
            res = await client.get(
                "http://localhost:8080/admin/realms/claria/roles/admin",
                headers=headers
            )
            admin_role = res.json()
            
            res = await client.post(
                f"http://localhost:8080/admin/realms/claria/users/{admin_uuid}/role-mappings/realm",
                headers=headers,
                json=[admin_role]
            )
            print("Assign admin role to adminuser:", res.status_code, res.text)

if __name__ == "__main__":
    asyncio.run(setup())
