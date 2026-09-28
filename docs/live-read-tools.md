# Live Read-Only Observability Tools

The AIOps slice now includes real HTTP adapters for Prometheus and Kubernetes.

They are deliberately **read-only**.

## Prometheus

`PrometheusReadTool` uses:

`GET /api/v1/query?query=...`

Each configured PromQL query becomes Evidence containing:

- query name,
- PromQL,
- result type,
- returned series count,
- compact raw JSON result.

## Kubernetes

`KubernetesListTool` performs an HTTP GET against a configured resource path.

Example:

```text
/api/v1/namespaces/{namespace}/pods
```

The `{namespace}` value is taken from the Incident scope:

```text
namespace=checkout
```

The resulting Evidence records:

- API resource path,
- object count,
- up to the first 20 object names,
- resourceVersion.

## Authentication

`JsonHttpClient` supports an optional Bearer token and CA file.

The adapters never issue POST, PUT, PATCH or DELETE requests.

Write/remediation operations belong behind the Action Policy and Approval boundary, not inside observability collectors.

## Evidence-first rule

Live adapters only collect observations.

They do not mark a hypothesis as supported automatically. Verification remains a separate step.
