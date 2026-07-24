import httpx
import time
import os

BASE_URL = "http://127.0.0.1:8000"
REPO_URL = "file:///C:/Users/pinap/Projects/Self-Deploy/test-app"
TEST_APP_DIR = "C:/Users/pinap/Projects/Self-Deploy/test-app"

def run_git_cmd(repo, cmd):
    os.chdir(repo)
    os.system(cmd)
    os.chdir("..")

def wait_deployment(client, project_id, deployment_id):
    while True:
        r = client.get(f"/projects/{project_id}/deployments/{deployment_id}")
        r.raise_for_status()
        status = r.json()["status"]
        if status in ["RUNNING", "FAILED", "CANCELED"]:
            return r.json()
        time.sleep(2)

def run_tests():
    client = httpx.Client(base_url=BASE_URL)
    
    print("Registering user...")
    r = client.post("/auth/register", json={
        "email": "testroll1@example.com",
        "username": "testroll1",
        "password": "password123",
        "password_confirm": "password123"
    })
    
    print("Logging in...")
    r = client.post("/auth/login", json={"login": "testroll1", "password": "password123"})
    r.raise_for_status()
    token = r.json()["access_token"]
    
    client.headers.update({"Authorization": f"Bearer {token}"})
    
    # Reset git repo
    run_git_cmd(TEST_APP_DIR, "git reset --hard a39bb654fb8664f8e30d4d77eb992b1c4ae3f278")
    run_git_cmd(TEST_APP_DIR, "git clean -fd")

    # Create project
    print("Creating project...")
    r = client.post("/projects", json={
        "name": "Test Rollback",
        "repository_url": REPO_URL,
        "default_branch": "master"
    })
    r.raise_for_status()
    project_id = r.json()["id"]
    
    # 1. Deploy v1
    print("Deploying v1...")
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    d1 = wait_deployment(client, project_id, r.json()["id"])
    print(f"v1 status: {d1['status']} (Deployment #{d1['deployment_number']})")
    
    # 2. Deploy v2
    print("\nModifying app for v2...")
    with open(f"{TEST_APP_DIR}/index.js", "a") as f:
        f.write("\n// v2 comment\n")
    run_git_cmd(TEST_APP_DIR, "git add .")
    run_git_cmd(TEST_APP_DIR, 'git commit -m "v2"')
    
    print("Deploying v2...")
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    d2 = wait_deployment(client, project_id, r.json()["id"])
    print(f"v2 status: {d2['status']} (Deployment #{d2['deployment_number']})")
    
    # 3. Redeploy
    print("\nRedeploying active deployment (v2)...")
    r = client.post(f"/projects/{project_id}/redeploy")
    d3 = wait_deployment(client, project_id, r.json()["id"])
    print(f"Redeploy status: {d3['status']} (Deployment #{d3['deployment_number']})")
    print(f"Redeploy commit: {d3['commit_sha']}")
    
    # 4. Break application
    print("\nBreaking application...")
    with open(f"{TEST_APP_DIR}/Dockerfile", "a") as f:
        f.write("\nRUN exit 1\n")
    run_git_cmd(TEST_APP_DIR, "git add .")
    run_git_cmd(TEST_APP_DIR, 'git commit -m "broken build"')
    
    print("Deploying broken v3...")
    r = client.post(f"/projects/{project_id}/deployments", json={"branch": "master"})
    d4 = wait_deployment(client, project_id, r.json()["id"])
    print(f"Broken v3 status: {d4['status']} (Deployment #{d4['deployment_number']})")
    
    # 5. Rollback to v1
    print("\nRolling back to v1...")
    r = client.post(f"/projects/{project_id}/rollback/{d1['id']}")
    d5 = wait_deployment(client, project_id, r.json()["id"])
    print(f"Rollback status: {d5['status']} (Deployment #{d5['deployment_number']})")
    print(f"Rollback commit: {d5['commit_sha']}")
    print("Expected commit:", d1["commit_sha"])
    
    # 6. Verify deployment history
    print("\nVerifying deployment history...")
    r = client.get(f"/projects/{project_id}/deployments")
    history = r.json()
    for d in history:
        print(f"#{d['deployment_number']} - {d['status']} - active={d['is_active']} - {d['commit_sha']}")
        
    print(f"\nActive deployment ID: {client.get(f'/projects/{project_id}').json()['active_deployment_id']}")
    print(f"Latest rollback deployment ID: {d5['id']}")

if __name__ == "__main__":
    run_tests()
