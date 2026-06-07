## fmt-go futtatás
**Exit code:** 0
**Módosított fájlok száma:** 41

### Módosított fájlok
- cmd/relay/activator.go
- cmd/relay/activator_test.go
- cmd/relay/bootstrap.go
- cmd/relay/bootstrap_test.go
- cmd/relay/git_host_funcs_test.go
- cmd/relay/main.go
- cmd/relay/main_api_test.go
- cmd/relay/middleware.go
- cmd/relay/middleware_test.go
- cmd/relay/pki_bootstrap.go
- cmd/relay/proof_verify.go
- core/cabinet/execution_recorder.go
- core/cabinet/graph.go
- core/cabinet/graph_test.go
- core/cabinet/proof_trace.go
- core/cabinet/proof_trace_test.go
- core/cabinet/schema_validate.go
- core/cabinet/schema_validate_test.go
- core/cabinet/service.go
- core/cabinet/service_integration_test.go
- core/modules/certselfsigned/certselfsigned.go
- core/modules/certselfsigned/certselfsigned_test.go
- core/modules/cibuild/cibuild.go
- core/modules/cibuild/cibuild_test.go
- core/modules/schemapipeline/schemapipeline.go
- core/nexus/iac/source_upstream.go
- core/nexus/iac/validator_test.go
- core/nexus/isolation/ipc_test.go
- core/nexus/isolation/worker_subprocess.go
- core/nexus/operator/bootstrap.go
- core/nexus/operator/bootstrap_test.go
- core/nexus/operator/lifecycle.go
- core/nexus/operator/lifecycle_test.go
- core/nexus/operator/watcher.go
- core/nexus/recorder/workflow_recorder.go
- core/nexus/types/types.go
- pkg/obs/capture.go
- pkg/obs/logrus_sink.go
- pkg/obs/sink.go
- pkg/obs/types.go
- tools/sourcehash/main.go

## fmt-check ellenőrzés
**Exit code:** 0

**Megjegyzés:** A `builder` container git safe directory hibát dobott (`detected dubious ownership`). Egyszer kellett beállítani: `git config --global --add safe.directory /git-source` a container-ben, utána a `fmt-check` exit 0-val futott le.

## Git commit
**Branch:** fix/gofmt
**Commit hash:** 280b09fa0b7496e8825fd835071b4c0e304a68e4
**Push:** sikeres (origin/fix/gofmt)
