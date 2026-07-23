import httpx
import time
import sys

BASE_URL = "http://127.0.0.1:8000"
REPO_URL = "file:///C:/Users/pinap/Projects/Self-Deploy/test-app"

def run_tests():
    client = httpx.Client(base_url=BASE_URL)
    
    # 1. Register and login
    print("Registering user...")
    r = client.post("/auth/register", json={
        "email": "testenv6@example.com",
        "username": "testenv6",
        "password": "password123",
        "password_confirm": "password123"
    })
    print(r.text)
    r.raise_for_status()
    
    print("Logging in...")
    r = client.post("/auth/login", json={"login": "testenv6", "password": "password123"})
    print(r.text)
    r.raise_for_status()
    token = r.json()["access_token"]
    
    client.headers.update({"Authorization": f"Bearer {token}"})
    
    # 2. Create project
    print("Creating project...")
    r = client.post("/projects", json={
        "name": "Test Env Project",
        "repository_url": REPO_URL,
        "default_branch": "master"
    })
    r.raise_for_status()
    project_id = r.json()["id"]
    print(f"Project created: {project_id}")
    
    # 3. Add env vars
    print("Adding env vars...")
    r = client.post(f"/projects/{project_id}/environment", json={
        "key": "DATABASE_PASSWORD",
        "value": "supersecret123",
        "is_secret": True
    })
    r.raise_for_status()
    var1_id = r.json()["id"]
    print(f"Created secret var: {r.json()}")
    
    r = client.post(f"/projects/{project_id}/environment", json={
        "key": "API_KEY",
        "value": "public_key_abc",
        "is_secret": False
    })
    r.raise_for_status()
    print(f"Created public var: {r.json()}")
    
    # 4. Trigger deployment
    print("Triggering deployment...")
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    r.raise_for_status()
    deployment_id = r.json()["id"]
    
    # Wait for deployment
    for _ in range(60):
        r = client.get(f"/projects/{project_id}/deployments/{deployment_id}")
        status = r.json()["status"]
        print(f"Deployment status: {status}")
        if status == "running":
            break
        elif status == "failed":
            print(f"Deployment failed: {r.json()['error_message']}")
            sys.exit(1)
        time.sleep(2)
        
    print("Deployment successful!")
    
    # 5. Check runtime status to get port
    r = client.get(f"/projects/{project_id}/runtime")
    r.raise_for_status()
    ports = r.json()["inspect"]["NetworkSettings"]["Ports"]
    port_mapping = ports["3000/tcp"][0]["HostPort"]
    print(f"App is running on port {port_mapping}")
    
    # 6. Verify env vars in app
    app_url = f"http://127.0.0.1:{port_mapping}/env"
    print(f"Checking {app_url}...")
    for _ in range(5):
        try:
            r = httpx.get(app_url)
            print("App response:", r.json())
            break
        except Exception as e:
            print("Waiting for app to boot...", e)
            time.sleep(1)
            
    # 7. Update var
    print("Updating var...")
    r = client.patch(f"/projects/{project_id}/environment/{var1_id}", json={"value": "newsecret456"})
    r.raise_for_status()
    print("Updated var:", r.json())
    
    # Trigger deployment again
    print("Triggering second deployment...")
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    deployment_id = r.json()["id"]
    
    for _ in range(60):
        r = client.get(f"/projects/{project_id}/deployments/{deployment_id}")
        status = r.json()["status"]
        if status == "running":
            break
        elif status == "failed":
            print(f"Deployment failed: {r.json()['error_message']}")
            sys.exit(1)
        time.sleep(2)
        
    r = client.get(f"/projects/{project_id}/runtime")
    port_mapping = r.json()["inspect"]["NetworkSettings"]["Ports"]["3000/tcp"][0]["HostPort"]
    
    app_url = f"http://127.0.0.1:{port_mapping}/env"
    print(f"Checking {app_url} after update...")
    time.sleep(2)
    r = httpx.get(app_url)
    print("App response:", r.json())
    
    # 8. Delete var
    print("Deleting var...")
    r = client.delete(f"/projects/{project_id}/environment/{var1_id}")
    r.raise_for_status()
    
    print("All tests passed.")

if __name__ == "__main__":
    run_tests()
