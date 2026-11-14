#!/usr/bin/env bash
# PR-03: what would bringing tools/goastdump (a separate Go module) into the mutation scope mean? (measurement only)
export GOFLAGS="-buildvcs=false" GOPATH=/gp GOCACHE=/gc GOTOOLCHAIN=local
cd /m; go version
echo "### coverage of the nested module"; go test -count=1 -cover ./... 2>&1 | tail -3
echo "### gremlins v0.6.0 on the nested module"
go install github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0 >/tmp/inst.log 2>&1; echo "install exit=$?"; tail -2 /tmp/inst.log
export PATH=/gp/bin:$PATH
s=$(date +%s)
timeout 600 gremlins unleash --workers 2 . 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tail -12
echo "gremlins exit=${PIPESTATUS[0]} seconds=$(( $(date +%s) - s ))"
