import httpx
import time
import sys
import os

BASE_URL = "http://127.0.0.1:8000"
REPO_URL = "file:///C:/Users/pinap/Projects/Self-Deploy/test-app"
TEST_APP_DIR = "C:/Users/pinap/Projects/Self-Deploy/test-app"

def run_cmd(cmd):
    os.system(cmd)

def run_tests():
    client = httpx.Client(base_url=BASE_URL)
    
    print("Registering user...")
    r = client.post("/auth/register", json={
        "email": "testlogs6@example.com",
        "username": "testlogs6",
        "password": "password123",
        "password_confirm": "password123"
    })
    
    print("Logging in...")
    r = client.post("/auth/login", json={"login": "testlogs6", "password": "password123"})
    r.raise_for_status()
    token = r.json()["access_token"]
    
    client.headers.update({"Authorization": f"Bearer {token}"})
    
    # Create project
    print("Creating project...")
    r = client.post("/projects", json={
        "name": "Test Logs Project",
        "repository_url": REPO_URL,
        "default_branch": "master"
    })
    r.raise_for_status()
    project_id = r.json()["id"]
    print(f"Project created: {project_id}")
    
    # 1. Successful App
    print("Deploying successful app...")
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    r.raise_for_status()
    deployment_id = r.json()["id"]
    
    # Wait for deployment
    while True:
        r = client.get(f"/projects/{project_id}/deployments/{deployment_id}")
        status = r.json()["status"]
        if status in ["RUNNING", "FAILED", "CANCELED"]:
            break
        time.sleep(2)
        
    print(f"Deployment status: {status}")
    
    print("Checking logs for successful app...")
    r = client.get(f"/projects/{project_id}/logs?deployment_id={deployment_id}")
    r.raise_for_status()
    logs = r.json()
    # 2. Broken App (build fails)
    def run_git_cmd(repo, cmd):
        os.chdir(repo)
        os.system(cmd)
        os.chdir("..")

    print("\nModifying app to fail build...")
    with open(f"{TEST_APP_DIR}/Dockerfile", "a") as f:
        f.write("\nRUN exit 1\n")
        
    run_git_cmd(TEST_APP_DIR, "git add .")
    run_git_cmd(TEST_APP_DIR, 'git commit -m "break build"')
    
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    r.raise_for_status()
    deployment_id_fail = r.json()["id"]
    
    while True:
        r = client.get(f"/projects/{project_id}/deployments/{deployment_id_fail}")
        status = r.json()["status"]
        if status in ["RUNNING", "FAILED", "CANCELED"]:
            break
        time.sleep(2)
        
    print(f"Broken build deployment status: {status}")
    r = client.get(f"/projects/{project_id}/logs?deployment_id={deployment_id_fail}")
    logs = r.json()
    print("Build logs (should contain error):", "exit 1" in logs.get("build_logs", ""))
    
    # 3. App that crashes after startup
    print("\nModifying app to crash at runtime...")
    # Clean Dockerfile to remove the build failure
    with open(f"{TEST_APP_DIR}/Dockerfile", "r") as f:
        lines = f.readlines()
    with open(f"{TEST_APP_DIR}/Dockerfile", "w") as f:
        f.writelines([l for l in lines if "RUN exit 1" not in l])
    
    with open(f"{TEST_APP_DIR}/index.js", "a") as f:
        f.write("\nsetTimeout(() => process.exit(1), 1000);\n")
        
    run_git_cmd(TEST_APP_DIR, "git add .")
    run_git_cmd(TEST_APP_DIR, 'git commit -m "crash runtime"')
    
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    r.raise_for_status()
    deployment_id_crash = r.json()["id"]
    
    while True:
        r = client.get(f"/projects/{project_id}/deployments/{deployment_id_crash}")
        status = r.json()["status"]
        if status in ["RUNNING", "FAILED", "CANCELED"]:
            break
        time.sleep(2)
        
    print(f"Crash runtime deployment status: {status}")
    r = client.get(f"/projects/{project_id}/logs?deployment_id={deployment_id_crash}")
    logs = r.json()
    print("Build logs length:", len(logs.get("build_logs", "")))
    print("Runtime logs (might be empty or contain crash):", logs.get("runtime_logs"))

if __name__ == "__main__":
    run_tests()
