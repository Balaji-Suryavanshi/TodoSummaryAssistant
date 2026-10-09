# Monitoring and Operations

## Overview
The monitoring stack consists of Prometheus (metrics collection), node-exporter (host metrics), cAdvisor (container metrics), and Grafana (visualization and alerting).

## Key Metrics Monitored
- **Request Rate & Latency (`http_server_requests_seconds_bucket`)**: Provided by Micrometer/Actuator. Critical for understanding application throughput and user experience.
- **Error Rate (HTTP 5xx)**: Tracks backend unhandled exceptions or connection issues (`rate(http_server_requests_seconds_count{status=~"5.."}[5m]) or vector(0)`).
- **Host CPU Usage (`node_cpu_seconds_total`)**: 100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) indicates host load.
- **Host Disk Space (`node_filesystem_avail_bytes`)**: Restricted to mountpoint="/" to avoid alerting on overlay/tmpfs filesystems.

## Critical Logs
- **Spring Boot Application Logs**: Tracked via `docker logs`. Important for diagnosing `5xx` errors.
- **Nginx Access Logs**: Useful to see frontend traffic patterns and 404s.

## Alerts (Alert-rules.yml)
- **ServiceDown**: Critical. Triggers if the backend or frontend is unreachable for 1 minute (`up == 0`).
- **HighErrorRate**: Critical. Triggers if 5xx errors exceed 5% of traffic over 2 minutes (`(rate(http_server_requests_seconds_count{status=~"5.."}[5m]) or vector(0)) > 0.05`).
- **HighLatency (p95)**: Warning. Triggers if 95% of requests take more than 2 seconds.
- **HighCPU**: Warning. Triggers if host CPU usage > 80% (`100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80`).
- **HighMemory**: Warning. Triggers if usage > 80%.
- **LowDisk**: Warning. Triggers if disk < 20% (`(node_filesystem_avail_bytes{mountpoint="/",fstype!~"tmpfs|overlay"} / node_filesystem_size_bytes{mountpoint="/",fstype!~"tmpfs|overlay"}) * 100 < 20`).
- **ContainerRestarting**: Warning. Triggers if a container restarts multiple times (`changes(container_start_time_seconds{name!=""}[15m]) > 2`).

### Noise Reduction
- We use `for: 5m` for CPU/Memory to avoid alerting on short transient spikes (e.g. during application startup or JVM garbage collection).
- We do **NOT** alert on 4xx errors (like 404 Not Found), as these are typically client-side issues and not an actionable operational failure.
