import urllib.request
import json
import urllib.parse
import time

def fetch_json(url, auth=None):
    req = urllib.request.Request(url)
    if auth:
        import base64
        base64string = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        req.add_header("Authorization", f"Basic {base64string}")
    for _ in range(5):
        try:
            response = urllib.request.urlopen(req)
            return json.loads(response.read().decode())
        except urllib.error.URLError as e:
            if hasattr(e, 'read'):
                return {"error": e.code, "message": e.read().decode()}
            time.sleep(2)
        except Exception as e:
            time.sleep(2)
    return {"error": "Failed after retries"}

print("=== Grafana Datasources ===")
ds = fetch_json("http://127.0.0.1:3000/api/datasources", "admin:admin")
print(json.dumps(ds, indent=2) if isinstance(ds, list) else ds)

print("\n=== Grafana Dashboards ===")
dashboards = fetch_json("http://127.0.0.1:3000/api/search", "admin:admin")
print(json.dumps(dashboards, indent=2) if isinstance(dashboards, list) else dashboards)

print("\n=== Grafana Alert Rules ===")
alerts = fetch_json("http://127.0.0.1:3000/api/v1/provisioning/alert-rules", "admin:admin")
print(json.dumps(alerts, indent=2) if isinstance(alerts, list) else alerts)

queries = [
    "rate(http_server_requests_seconds_count[5m])",
    "rate(http_server_requests_seconds_count{status=~\"5..\"}[5m])",
    "histogram_quantile(0.50, sum(rate(http_server_requests_seconds_bucket[5m])) by (le))",
    "histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket[5m])) by (le))",
    "histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket[5m])) by (le))",
    "sum(rate(container_cpu_usage_seconds_total{job=\"cadvisor\"}[5m]))",
    "sum(container_memory_usage_bytes{job=\"cadvisor\"})",
    "100 - ((node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100)",
    "rate(kube_pod_container_status_restarts_total[1h])",
    "time() - process_start_time_seconds"
]

print("\n=== Prometheus Queries ===")
for q in queries:
    url = f"http://127.0.0.1:9090/api/v1/query?query={urllib.parse.quote(q)}"
    res = fetch_json(url)
    data = res.get("data", {}).get("result", [])
    if not data:
        print(f"[EMPTY] {q}")
    else:
        print(f"[OK] {q} -> Found {len(data)} results")

print("\n=== Prometheus HighCPU Rule Evaluation ===")
q_high_cpu = "(sum by(instance) (rate(container_cpu_usage_seconds_total[5m])) / count by(instance) (machine_cpu_cores)) * 100"
res_high_cpu = fetch_json(f"http://localhost:9090/api/v1/query?query={urllib.parse.quote(q_high_cpu)}")
results = res_high_cpu.get("data", {}).get("result", [])
if not results:
    print("No results for HighCPU")
else:
    for r in results:
        val = float(r['value'][1])
        print(f"Instance: {r['metric'].get('instance', 'unknown')}, CPU Usage %: {val:.2f}")
        if val > 80:
            print(f"  -> EXCEEDS THRESHOLD (80%)")
