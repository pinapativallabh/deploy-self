import urllib.request, json, time, sys

try:
    req = urllib.request.Request('http://localhost:8000/auth/login', method='POST', data=json.dumps({'login':'test6','password':'password123'}).encode('utf-8'), headers={'Content-Type': 'application/json'})
    res = urllib.request.urlopen(req)
    tokens = json.loads(res.read().decode())
    token = tokens['access_token']
except Exception as e:
    print('Login error:', e.read().decode() if hasattr(e, 'read') else str(e))
    sys.exit(1)

# Fetch Project
try:
    req3 = urllib.request.Request('http://localhost:8000/projects', method='GET', headers={'Authorization': f'Bearer {token}'})
    res3 = urllib.request.urlopen(req3)
    projects = json.loads(res3.read().decode())
    if not projects:
        project_data = {
            'name': 'Test Project',
            'repository_url': 'https://github.com/pinapativallabh/deploy-self.git',
            'default_branch': 'master',
            'build_context': 'backend',
            'dockerfile_path': 'Dockerfile',
            'health_check_path': '/health'
        }
        req2 = urllib.request.Request('http://localhost:8000/projects', method='POST', data=json.dumps(project_data).encode('utf-8'), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
        res2 = urllib.request.urlopen(req2)
        project = json.loads(res2.read().decode())
        project_id = project['id']
    else:
        project_id = projects[0]['id']
except Exception as e:
    print('Project error:', e.read().decode() if hasattr(e, 'read') else str(e))
    sys.exit(1)

# Trigger Deployment
try:
    req4 = urllib.request.Request(f'http://localhost:8000/projects/{project_id}/deployments', method='POST', data=json.dumps({}).encode('utf-8'), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
    res4 = urllib.request.urlopen(req4)
    deployment = json.loads(res4.read().decode())
    dep_id = deployment['id']
    print(f'Deployment started: {dep_id}')
except Exception as e:
    print('Deploy error:', e.read().decode() if hasattr(e, 'read') else str(e))
    sys.exit(1)

# Poll status
while True:
    try:
        req5 = urllib.request.Request(f'http://localhost:8000/projects/{project_id}/deployments', method='GET', headers={'Authorization': f'Bearer {token}'})
        res5 = urllib.request.urlopen(req5)
        deps = json.loads(res5.read().decode())
        current_dep = next(d for d in deps if d['id'] == dep_id)
        print('Status:', current_dep['status'])
        if current_dep['status'] in ['FAILED', 'RUNNING']:
            if current_dep['status'] == 'FAILED':
                print('Error:', current_dep.get('error_message'))
            break
        time.sleep(2)
    except Exception as e:
        print('Poll error:', e.read().decode() if hasattr(e, 'read') else str(e))
        break
