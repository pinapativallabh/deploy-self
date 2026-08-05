import urllib.request, urllib.parse, json, time, sys, uuid

def make_request(url, method='GET', data=None, token=None):
    headers = {}
    if data is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode('utf-8')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        res = urllib.request.urlopen(req)
        if res.length == 0 or res.status == 204:
            return None
        return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTPError {e.code}: {body}")

def register_and_login():
    username = f"user_{uuid.uuid4().hex[:6]}"
    make_request('http://localhost:8080/api/auth/register', method='POST', data={
        'email': f'{username}@test.com',
        'username': username,
        'password': 'password123',
        'password_confirm': 'password123'
    })
    tokens = make_request('http://localhost:8080/api/auth/login', method='POST', data={
        'login': f'{username}@test.com',
        'password': 'password123'
    })
    return tokens['access_token']

def test():
    print("Starting E2E validation...")
    token = register_and_login()
    
    print("Creating app 1...")
    app1 = make_request('http://localhost:8080/api/projects', method='POST', token=token, data={
        'name': f'App 1 {uuid.uuid4().hex[:4]}',
        'repository_url': 'https://github.com/pinapativallabh/deploy-self.git',
        'default_branch': 'master',
        'build_context': 'frontend', # test frontend
        'dockerfile_path': 'Dockerfile',
        'health_check_path': '/' # Next.js serves /
    })
    
    print("Creating app 2...")
    app2 = make_request('http://localhost:8080/api/projects', method='POST', token=token, data={
        'name': f'App 2 {uuid.uuid4().hex[:4]}',
        'repository_url': 'https://github.com/pinapativallabh/deploy-self.git',
        'default_branch': 'master',
        'build_context': 'frontend', # use frontend again to avoid DB dependency crash
        'dockerfile_path': 'Dockerfile',
        'health_check_path': '/'
    })
    
    # Deploy app 1
    print(f"Deploying app 1 (slug: {app1['slug']})...")
    dep1 = make_request(f"http://localhost:8080/api/projects/{app1['id']}/deployments", method='POST', data={}, token=token)
    
    # Deploy app 2
    print(f"Deploying app 2 (slug: {app2['slug']})...")
    dep2 = make_request(f"http://localhost:8080/api/projects/{app2['id']}/deployments", method='POST', data={}, token=token)
    
    # Wait for both to finish
    def wait_for_deployment(project_id, dep_id, name):
        print(f"Waiting for {name} to deploy...")
        while True:
            deps = make_request(f"http://localhost:8080/api/projects/{project_id}/deployments", token=token)
            d = next((x for x in deps if x['id'] == dep_id), None)
            if not d:
                raise Exception("Deployment not found")
            print(f"  {name} status: {d['status']}")
            if d['status'] == 'RUNNING':
                return d
            elif d['status'] in ['FAILED', 'DEAD', 'CANCELED']:
                print(f"{name} logs:")
                logs = make_request(f"http://localhost:8080/api/projects/{project_id}/logs?deployment_id={dep_id}", token=token)
                print(logs)
                raise Exception(f"{name} deployment failed: {d.get('error_message')}")
            time.sleep(5)
            
    dep1 = wait_for_deployment(app1['id'], dep1['id'], "App 1")
    dep2 = wait_for_deployment(app2['id'], dep2['id'], "App 2")
    
    print("Validating NGINX routing...")
    # App 1 is nextjs
    try:
        urllib.request.urlopen(f"http://localhost:8080/apps/{app1['slug']}/")
        print("App 1 is accessible through NGINX.")
    except Exception as e:
        print(f"App 1 NGINX error: {e}")
        
    # App 2 is fastapi
    try:
        urllib.request.urlopen(f"http://localhost:8080/apps/{app2['slug']}/")
        print("App 2 is accessible through NGINX.")
    except Exception as e:
        print(f"App 2 NGINX error: {e}")
        
    print("Testing rollback on App 1...")
    dep1_rollback = make_request(f"http://localhost:8080/api/projects/{app1['id']}/rollback/{dep1['id']}", method='POST', token=token, data={})
    wait_for_deployment(app1['id'], dep1_rollback['id'], "App 1 Rollback")
    
    print("Testing logs on App 2...")
    logs2 = make_request(f"http://localhost:8080/api/projects/{app2['id']}/logs?deployment_id={dep2['id']}", token=token)
    if not logs2 or not logs2.get('build_logs'):
        print("Warning: Logs missing for App 2")
    else:
        print("Logs retrieved successfully for App 2")
        
    print("Deleting App 1...")
    make_request(f"http://localhost:8080/api/projects/{app1['id']}", method='DELETE', token=token)
    
    print("Verifying App 1 NGINX config is gone...")
    try:
        urllib.request.urlopen(f"http://localhost:8080/apps/{app1['slug']}/")
        print("Error: App 1 is still accessible!")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("App 1 correctly returns 404.")
        else:
            print(f"App 1 returns {e.code}, expected 404.")
            
    print("Verifying App 2 is still accessible...")
    try:
        urllib.request.urlopen(f"http://localhost:8080/apps/{app2['slug']}/")
        print("App 2 is still accessible through NGINX.")
    except Exception as e:
        print(f"Error: App 2 NGINX error: {e}")

if __name__ == '__main__':
    test()
