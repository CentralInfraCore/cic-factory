// Package conformance runs the corpus in ../../conformance against the Go
// implementation.
//
// The vectors are implementation-independent (YAML in, YAML out) and this
// runner adds no Go-specific fixture: it reads the same files the Rust
// implementation will read. Where the two disagree, the disagreement is the
// spec's, not the language's.
package conformance

import (
	"errors"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"gopkg.in/yaml.v3"

	"github.com/CentralInfraCore/cic-object-model/go/objectmodel"
)

const corpus = "../../conformance"

// expectedCounts is what "the corpus ran" means. A runner that discovers zero
// vectors and exits 0 has not run the corpus, so the counts are asserted
// rather than reported.
var expectedCounts = map[string]int{
	"materialization": 13,
	"invalid":         8,
	"validation":      6,
}

type expectedError struct {
	Error struct {
		Code      string `yaml:"code"`
		Invariant string `yaml:"invariant"`
		Stage     string `yaml:"stage"`
		Path      string `yaml:"path"`
		Detail    string `yaml:"detail"`
	} `yaml:"error"`
}

func vectors(t *testing.T, group string) []string {
	t.Helper()
	entries, err := os.ReadDir(filepath.Join(corpus, group))
	if err != nil {
		t.Fatalf("cannot read the %s vectors: %v", group, err)
	}
	var names []string
	for _, e := range entries {
		if e.IsDir() {
			names = append(names, e.Name())
		}
	}
	if got, want := len(names), expectedCounts[group]; got != want {
		t.Fatalf("%s: discovered %d vectors, expected %d", group, got, want)
	}
	return names
}

func read(t *testing.T, parts ...string) []byte {
	t.Helper()
	b, err := os.ReadFile(filepath.Join(parts...))
	if err != nil {
		t.Fatalf("cannot read %s: %v", filepath.Join(parts...), err)
	}
	return b
}

// TestCorpusSize fails if the corpus is not the 27 vectors SPEC §10 and
// docs/spec-vector-map.md describe.
func TestCorpusSize(t *testing.T) {
	total := 0
	for group := range expectedCounts {
		total += len(vectors(t, group))
	}
	if total != 27 {
		t.Fatalf("discovered %d vectors, the corpus is 27", total)
	}
	t.Logf("corpus: %d vectors", total)
}

// TestMaterialization runs conformance/materialization/*: authoring input to
// canonical object.
func TestMaterialization(t *testing.T) {
	for _, name := range vectors(t, "materialization") {
		dir := filepath.Join(corpus, "materialization", name)
		t.Run(name, func(t *testing.T) {
			schema := read(t, dir, "schema.yaml")
			input := read(t, dir, "input.yaml")
			expected := read(t, dir, "expected.yaml")

			obj, err := objectmodel.Materialize(schema, input)
			if err != nil {
				t.Fatalf("materialization failed: %v", err)
			}

			// SPEC §10: the output must match expected.yaml exactly. §8.8
			// never defines a canonical serialization, so "exactly" can only
			// be checked semantically — see docs/spec-defects.md SD-010.
			var got, want any
			if err := yaml.Unmarshal(obj.CanonicalYAML(), &got); err != nil {
				t.Fatalf("canonical output is not valid YAML: %v", err)
			}
			if err := yaml.Unmarshal(expected, &want); err != nil {
				t.Fatalf("expected.yaml is not valid YAML: %v", err)
			}
			if !reflect.DeepEqual(got, want) {
				t.Errorf("canonical object does not match expected.yaml\n--- got ---\n%s\n--- want ---\n%s",
					obj.CanonicalYAML(), expected)
			}

			// INV-030 — the same schema and input must produce a
			// byte-identical canonical object.
			again, err := objectmodel.Materialize(schema, input)
			if err != nil {
				t.Fatalf("second materialization failed: %v", err)
			}
			if !reflect.DeepEqual(obj.CanonicalYAML(), again.CanonicalYAML()) {
				t.Errorf("INV-030: materialization is not deterministic")
			}
		})
	}
}

// TestInvalid runs conformance/invalid/*: authoring input that must be
// rejected, with the right code at the right stage.
func TestInvalid(t *testing.T) {
	for _, name := range vectors(t, "invalid") {
		dir := filepath.Join(corpus, "invalid", name)
		t.Run(name, func(t *testing.T) {
			schema := read(t, dir, "schema.yaml")
			input := read(t, dir, "input.yaml")

			var want expectedError
			if err := yaml.Unmarshal(read(t, dir, "expected-error.yaml"), &want); err != nil {
				t.Fatalf("expected-error.yaml is not valid YAML: %v", err)
			}

			_, err := objectmodel.Materialize(schema, input)
			assertRejected(t, err, want)
		})
	}
}

// TestValidation runs conformance/validation/*: an already-canonical object
// presented to SPEC §8.7 directly.
func TestValidation(t *testing.T) {
	for _, name := range vectors(t, "validation") {
		dir := filepath.Join(corpus, "validation", name)
		t.Run(name, func(t *testing.T) {
			object := read(t, dir, "object.yaml")

			var want expectedError
			if err := yaml.Unmarshal(read(t, dir, "expected-error.yaml"), &want); err != nil {
				t.Fatalf("expected-error.yaml is not valid YAML: %v", err)
			}

			assertRejected(t, objectmodel.ValidateCanonicalDocument(object), want)
		})
	}
}

func assertRejected(t *testing.T, err error, want expectedError) {
	t.Helper()
	if err == nil {
		t.Fatalf("expected rejection %s at stage %s, got none",
			want.Error.Code, want.Error.Stage)
	}
	var got *objectmodel.Error
	if !errors.As(err, &got) {
		t.Fatalf("expected an *objectmodel.Error, got %T: %v", err, err)
	}
	if got.Code != want.Error.Code {
		t.Errorf("code: got %s, want %s", got.Code, want.Error.Code)
	}
	if got.Invariant != want.Error.Invariant {
		t.Errorf("invariant: got %s, want %s", got.Invariant, want.Error.Invariant)
	}
	// conformance/README.md: "Rejecting with the right code at the wrong
	// stage is a failure: stage order is normative (§8)."
	if string(got.Stage) != want.Error.Stage {
		t.Errorf("stage: got %s, want %s", got.Stage, want.Error.Stage)
	}
	if got.Path != want.Error.Path {
		t.Errorf("path: got %s, want %s", got.Path, want.Error.Path)
	}
}
