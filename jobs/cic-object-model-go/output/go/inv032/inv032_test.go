// Package inv032 holds the source-level check for SPEC INV-032.
//
// docs/spec-vector-map.md marks INV-032 unvectorizable and assigns it to this
// implementation by name: "the type's constructor and fields unexported,
// verified by a test in a separate package that must fail to compile — plus
// grep -rn for any exported constructor". Both halves are here.
package inv032

import (
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

// TestForgedObjectDoesNotCompile is the compile-fail half. testdata/forge
// implements every exported method of objectmodel.CanonicalObject and tries
// to assign it; the build must fail on the unexported marker method.
func TestForgedObjectDoesNotCompile(t *testing.T) {
	if _, err := exec.LookPath("go"); err != nil {
		t.Fatalf("INV-032 cannot be verified without the go tool: %v", err)
	}

	cmd := exec.Command("go", "build", "./inv032/testdata/forge")
	cmd.Dir = ".."
	out, err := cmd.CombinedOutput()

	if err == nil {
		t.Fatalf("INV-032 VIOLATED: testdata/forge compiled.\n"+
			"A value of Validated<Canonical<CICObject>> was constructible outside the materializer.\n%s", out)
	}

	got := string(out)
	// The failure must be the INV-032 one, not an unrelated build break.
	if !strings.Contains(got, "sealedByMaterializer") {
		t.Errorf("build failed, but not on the INV-032 marker method.\n%s", got)
	}
	// ...and the Node literal must be rejected for its unexported fields.
	if !strings.Contains(got, "unexported field") && !strings.Contains(got, "unknown field") {
		t.Errorf("build failed, but the Node composite literal was not rejected for unexported fields.\n%s", got)
	}
	t.Logf("INV-032 holds; the compiler rejected the forgery:\n%s", got)
}

// TestNoExportedConstructor is the grep half. An exported New*/Must*
// returning a CanonicalObject or a *Node would reopen what the unexported
// marker method closes.
func TestNoExportedConstructor(t *testing.T) {
	pattern := regexp.MustCompile(`^func (New|Must)[A-Za-z0-9_]*\(`)

	var offenders []string
	err := filepath.WalkDir("..", func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		if !strings.HasSuffix(path, ".go") || strings.HasSuffix(path, "_test.go") {
			return nil
		}
		body, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		for i, line := range strings.Split(string(body), "\n") {
			if pattern.MatchString(line) {
				offenders = append(offenders, filepath.ToSlash(path)+":"+strconv.Itoa(i+1)+": "+line)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walk failed: %v", err)
	}

	if len(offenders) > 0 {
		t.Errorf("INV-032: exported constructor(s) found — a value of the module input type must be constructible only by the core materializer:\n%s",
			strings.Join(offenders, "\n"))
	}
}
