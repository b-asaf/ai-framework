# Multi-repo workspaces (BE/FE or microservices)

Run graphify per repo, then merge into one workspace-level graph so cross-service calls (e.g. FE fetch → BE endpoint) resolve:

```bash
graphify extract [xxx]-be --global --as be
graphify extract [xxx]-fe --global --as fe
# or, to register an already-built graph without re-extracting:
graphify global add [xxx]-be/graphify-out/graph.json --as be
graphify global add [xxx]-fe/graphify-out/graph.json --as fe
```