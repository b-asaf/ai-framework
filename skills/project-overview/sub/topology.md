# Project Overview — Topology
> Load when: orchestrator (on every task), architect, tasks spanning multiple services.

## Architecture topology
- Type: [Monolith / Microservices / Hybrid] — confirmed by developer on [date]
- Services: [list of services with paths, or "single BE + single FE"]
- API gateway: [yes — path / no]
- Shared libraries: [yes — path / no]
- Containerization: [Docker / Kubernetes / none]

## Workspace layout
```
[XXX]/
├── [XXX]-be/    # [language] [framework] backend
└── [XXX]-fe/    # [framework] frontend
```

## CI/CD setup
[Detected from .github/, azure-pipelines.yml, Jenkinsfile, etc. or "none detected"]
