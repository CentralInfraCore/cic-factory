set -u
git config --global --add safe.directory /src; cd /src; export GOFLAGS="$GOFLAGS -buildvcs=false"
echo "go: $(go version)"; echo "commit: $(cat .git/HEAD 2>/dev/null | head -1)"
go list ./... > /out/pkgs.txt 2>/out/pkgs.err; echo "packages: $(wc -l < /out/pkgs.txt)"
# whole module, one profile (statement coverage, set mode, no race)
go test -count=1 -coverprofile=/out/total.out ./... > /out/total.log 2>&1; echo "total test exit: $?"
go tool cover -func=/out/total.out | tail -1
# the per-package measurement exactly as verify.yml does
for p in $(cat /out/pkgs.txt); do
  if go test -count=1 -coverprofile=/out/pkg.out "$p" > /out/pkg.log 2>&1; then
    pc=$(go tool cover -func=/out/pkg.out 2>/dev/null | awk 'END{gsub(/%/,""); print $3+0}')
    echo "PKG $p ${pc}"
  else
    echo "PKG $p TESTFAIL"; tail -n 5 /out/pkg.log | sed 's/^/    /'
  fi
done
