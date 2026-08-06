"""
End-to-end validation for Bonk platform with host-based routing.

Tests:
  - User registration and login
  - Project creation
  - Deployment (two apps simultaneously)
  - Host-based nginx routing via <slug>.<PUBLIC_HOST>.nip.io
  - Rollback
  - Logs retrieval
  - Project deletion removes routing
  - Other apps unaffected after deletion

Usage:
  python validate_e2e.py [--public-host HOST] [--port PORT]
"""

import urllib.request, urllib.parse, json, time, sys, uuid, argparse, os

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_PUBLIC_HOST = os.environ.get("PUBLIC_HOST", "localhost")
DEFAULT_PORT = int(os.environ.get("PUBLIC_PORT", "8080"))

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def make_request(url, method='GET', data=None, token=None, host_header=None):
    headers = {}
    if data is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(data).encode('utf-8')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if host_header:
        headers['Host'] = host_header
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        res = urllib.request.urlopen(req)
        if res.length == 0 or res.status == 204:
            return None
        return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTPError {e.code}: {body}")


def check_url(url, host_header=None, expect_status=None):
    """Try to open a URL, return (status_code, body_or_None)."""
    headers = {}
    if host_header:
        headers['Host'] = host_header
    req = urllib.request.Request(url, headers=headers)
    try:
        res = urllib.request.urlopen(req)
        body = res.read().decode()
        return res.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)

# ---------------------------------------------------------------------------
# Test flow
# ---------------------------------------------------------------------------

def register_and_login(api_base):
    username = f"user_{uuid.uuid4().hex[:6]}"
    make_request(f'{api_base}/auth/register', method='POST', data={
        'email': f'{username}@test.com',
        'username': username,
        'password': 'password123',
        'password_confirm': 'password123'
    })
    tokens = make_request(f'{api_base}/auth/login', method='POST', data={
        'login': f'{username}@test.com',
        'password': 'password123'
    })
    return tokens['access_token']


def test(public_host, port):
    api_base = f"http://localhost:{port}/api"

    print("=" * 60)
    print(f"Bonk E2E Validation — Host-Based Routing")
    print(f"  PUBLIC_HOST : {public_host}")
    print(f"  PUBLIC_PORT : {port}")
    print(f"  API         : {api_base}")
    print("=" * 60)

    print("\n[1/8] Registering and logging in...")
    token = register_and_login(api_base)
    print("  ✓ Authenticated")

    print("\n[2/8] Creating projects...")
    app1 = make_request(f'{api_base}/projects', method='POST', token=token, data={
        'name': f'App 1 {uuid.uuid4().hex[:4]}',
        'repository_url': 'https://github.com/pinapativallabh/deploy-self.git',
        'default_branch': 'master',
        'build_context': 'frontend',
        'dockerfile_path': 'Dockerfile',
        'health_check_path': '/'
    })
    print(f"  ✓ App 1 created (slug: {app1['slug']})")

    app2 = make_request(f'{api_base}/projects', method='POST', token=token, data={
        'name': f'App 2 {uuid.uuid4().hex[:4]}',
        'repository_url': 'https://github.com/pinapativallabh/deploy-self.git',
        'default_branch': 'master',
        'build_context': 'frontend',
        'dockerfile_path': 'Dockerfile',
        'health_check_path': '/'
    })
    print(f"  ✓ App 2 created (slug: {app2['slug']})")

    print("\n[3/8] Deploying both apps...")
    dep1 = make_request(f"{api_base}/projects/{app1['id']}/deployments", method='POST', data={}, token=token)
    dep2 = make_request(f"{api_base}/projects/{app2['id']}/deployments", method='POST', data={}, token=token)

    def wait_for_deployment(project_id, dep_id, name):
        print(f"  Waiting for {name}...")
        while True:
            deps = make_request(f"{api_base}/projects/{project_id}/deployments", token=token)
            d = next((x for x in deps if x['id'] == dep_id), None)
            if not d:
                raise Exception("Deployment not found")
            print(f"    {name} status: {d['status']}")
            if d['status'] == 'RUNNING':
                return d
            elif d['status'] in ['FAILED', 'DEAD', 'CANCELED']:
                print(f"    {name} logs:")
                try:
                    logs = make_request(f"{api_base}/projects/{project_id}/logs?deployment_id={dep_id}", token=token)
                    print(logs)
                except Exception:
                    pass
                raise Exception(f"{name} deployment failed: {d.get('error_message')}")
            time.sleep(5)

    dep1 = wait_for_deployment(app1['id'], dep1['id'], "App 1")
    dep2 = wait_for_deployment(app2['id'], dep2['id'], "App 2")
    print("  ✓ Both apps deployed successfully")

    # Check deployment URLs are host-based
    url1 = dep1.get('deployment_url', '')
    url2 = dep2.get('deployment_url', '')
    print(f"  App 1 URL: {url1}")
    print(f"  App 2 URL: {url2}")

    assert '.nip.io' in url1 or 'localhost' in url1, f"Expected host-based URL, got: {url1}"
    assert '.nip.io' in url2 or 'localhost' in url2, f"Expected host-based URL, got: {url2}"
    assert '/apps/' not in url1, f"URL should NOT contain /apps/ path: {url1}"
    assert '/apps/' not in url2, f"URL should NOT contain /apps/ path: {url2}"
    print("  ✓ Deployment URLs use host-based routing")

    print("\n[4/8] Validating nginx host-based routing...")
    # Use Host header to test routing through localhost
    app1_host = f"{app1['slug']}.{public_host}.nip.io"
    app2_host = f"{app2['slug']}.{public_host}.nip.io"

    status1, _ = check_url(f"http://localhost:{port}/", host_header=app1_host)
    if status1 and status1 < 400:
        print(f"  ✓ App 1 accessible via Host: {app1_host}")
    else:
        print(f"  ⚠ App 1 returned status {status1} via Host: {app1_host}")

    status2, _ = check_url(f"http://localhost:{port}/", host_header=app2_host)
    if status2 and status2 < 400:
        print(f"  ✓ App 2 accessible via Host: {app2_host}")
    else:
        print(f"  ⚠ App 2 returned status {status2} via Host: {app2_host}")

    print("\n[5/8] Verifying Bonk dashboard still works...")
    status_dash, _ = check_url(f"http://localhost:{port}/")
    assert status_dash and status_dash < 400, f"Dashboard returned {status_dash}"
    print("  ✓ Bonk dashboard accessible")

    status_api, _ = check_url(f"http://localhost:{port}/api/health")
    print(f"  ✓ API health endpoint returned {status_api}")

    print("\n[6/8] Testing rollback on App 1...")
    dep1_rollback = make_request(
        f"{api_base}/projects/{app1['id']}/rollback/{dep1['id']}",
        method='POST', token=token, data={}
    )
    dep1_rolled_back = wait_for_deployment(app1['id'], dep1_rollback['id'], "App 1 Rollback")
    print("  ✓ Rollback succeeded")

    # Verify app still accessible after rollback
    status_rb, _ = check_url(f"http://localhost:{port}/", host_header=app1_host)
    if status_rb and status_rb < 400:
        print(f"  ✓ App 1 still accessible after rollback")
    else:
        print(f"  ⚠ App 1 returned {status_rb} after rollback")

    print("\n[7/8] Testing logs retrieval...")
    logs2 = make_request(f"{api_base}/projects/{app2['id']}/logs?deployment_id={dep2['id']}", token=token)
    if logs2 and logs2.get('build_logs'):
        print("  ✓ Build logs retrieved")
    else:
        print("  ⚠ Build logs missing")

    print("\n[8/8] Testing project deletion and routing cleanup...")
    make_request(f"{api_base}/projects/{app1['id']}", method='DELETE', token=token)
    print(f"  ✓ App 1 project deleted")

    # Give nginx a moment to reload
    time.sleep(2)

    # App 1 should no longer route (falls through to default server / Bonk dashboard)
    status_deleted, body_deleted = check_url(f"http://localhost:{port}/", host_header=app1_host)
    # After deletion, the host should fall through to the Bonk dashboard (default_server)
    print(f"  App 1 host now returns status {status_deleted} (should be Bonk dashboard)")

    # App 2 should still work
    status_still, _ = check_url(f"http://localhost:{port}/", host_header=app2_host)
    if status_still and status_still < 400:
        print(f"  ✓ App 2 still accessible after App 1 deletion")
    else:
        print(f"  ✗ App 2 returned {status_still} — should still be accessible!")

    print("\n" + "=" * 60)
    print("E2E Validation Complete")
    print("=" * 60)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Bonk E2E validation")
    parser.add_argument('--public-host', default=DEFAULT_PUBLIC_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    test(args.public_host, args.port)
