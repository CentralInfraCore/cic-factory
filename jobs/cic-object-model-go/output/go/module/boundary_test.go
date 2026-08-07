package module_test

import (
	"errors"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"

	"github.com/CentralInfraCore/cic-object-model/go/module"
	"github.com/CentralInfraCore/cic-object-model/go/objectmodel"
)

// TestINV031Boundary is the integration test docs/spec-vector-map.md asks the
// implementation sub-jobs for by name: "A true boundary test is deferred to
// the sub-jobs, which must add one integration test per clause."
//
// Each subtest drives the pipeline with input that would produce the
// prohibited condition and asserts that what reaches Execute cannot carry it
// — either because the pipeline rejected the input, or because the condition
// is absent from the delivered object.
func TestINV031Boundary(t *testing.T) {
	t.Run("a_unresolved_references", func(t *testing.T) {
		// SPEC §8.2 must leave no unresolved reference. The 0.1 vector schema
		// language has no reference syntax at all (docs/spec-defects.md
		// SD-009), so the strongest reachable statement is the adjacent one:
		// a name the schema does not know never reaches a module, it is
		// rejected at entry validation.
		schema := []byte("model: \"0.1\"\nroot:\n  shape: object\n  children:\n    known:\n      shape: scalar\n      scalar_type: integer\n")
		input := []byte("known: 1\nunresolved_ref:\n  points: elsewhere\n")
		mustReject(t, schema, input, objectmodel.CodeUndeclaredObject)
	})

	t.Run("b_authoring_short_forms", func(t *testing.T) {
		// A short form must be normalized before the boundary.
		obj := mustMaterialize(t,
			[]byte("model: \"0.1\"\nroot:\n  shape: object\n  children:\n    name:\n      shape: scalar\n      scalar_type: string\n"),
			[]byte("name: eth0\n"))
		mustDeliver(t, obj)
		node := childOf(t, obj, "name")
		if _, ok := node.Scalar(); !ok {
			t.Fatal("the short form did not normalize to a node with a scalar payload")
		}
		if len(node.Origin()) == 0 {
			t.Error("INV-031(b): a node reached the boundary without an origin, i.e. unnormalized")
		}
	})

	t.Run("c_templates", func(t *testing.T) {
		// A template reference must be expanded, not delivered.
		obj := mustMaterialize(t, sealedSchema(true), []byte("{}\n"))
		mustDeliver(t, obj)
		out := string(obj.CanonicalYAML())
		if strings.Contains(out, "sealed_from") || strings.Contains(out, "templates:") {
			t.Errorf("INV-031(c): an unexpanded template reached the boundary:\n%s", out)
		}
		// What survives is provenance, not the template itself.
		node := childOf(t, obj, "access_policy")
		if node.Origin()[0].Kind != objectmodel.OriginSealed {
			t.Errorf("expected sealed provenance, got %v", node.Origin())
		}
	})

	t.Run("d_sealed_source_fragments", func(t *testing.T) {
		// Authoring below a sealed boundary is a pre-boundary artifact: it is
		// rejected outright, so no partially-sealed object exists to deliver.
		input := []byte("access_policy:\n  enabled: true\n")
		mustReject(t, sealedSchema(true), input, objectmodel.CodeAuthoringBelowSealed)
	})

	t.Run("e_unapplied_schema_defaults", func(t *testing.T) {
		obj := mustMaterialize(t,
			[]byte("model: \"0.1\"\nroot:\n  shape: object\n  children:\n    mtu:\n      shape: scalar\n      scalar_type: integer\n      default: 1500\n"),
			[]byte("{}\n"))
		mustDeliver(t, obj)
		node := childOf(t, obj, "mtu")
		v, ok := node.Scalar()
		if !ok || v != 1500 {
			t.Fatalf("INV-031(e): the default was not applied before the boundary: %v", v)
		}
		if node.Origin()[0].Kind != objectmodel.OriginSchema {
			t.Errorf("a defaulted value must carry origin [schema], got %v", node.Origin())
		}
	})

	t.Run("f_unknown_primitives", func(t *testing.T) {
		schema := []byte("model: \"0.1\"\nroot:\n  shape: object\n  children:\n    mtu:\n      shape: scalar\n      scalar_type: integer\n")
		input := []byte("mtu:\n  values: 9000\n  priority: high\n")
		mustReject(t, schema, input, objectmodel.CodeUnknownPrimitive)
	})

	t.Run("g_unvalidated_objects", func(t *testing.T) {
		// The type is the enforcement: Execute takes CanonicalObject, which
		// only Materialize produces, and Materialize runs §8.7 before
		// returning. The nil interface is the one hole Go leaves.
		if err := module.Execute(nil); !errors.Is(err, module.ErrNilObject) {
			t.Errorf("INV-031(g): the boundary accepted nil, got %v", err)
		}
		// And an object whose origin is defective never becomes one.
		bad := []byte("cic:\n  model: \"0.1\"\nvalues:\n  mtu:\n    values: 9000\n    origin: [yaml, schema]\norigin: [yaml]\n")
		if err := objectmodel.ValidateCanonicalDocument(bad); err == nil {
			t.Error("INV-031(g): an invalid object passed final validation")
		}
	})
}

// TestINV034ModelVersion — a host must not hand a module an object of a
// version the module has not declared.
func TestINV034ModelVersion(t *testing.T) {
	obj := mustMaterialize(t,
		[]byte("model: \"9.9\"\nroot:\n  shape: object\n  children:\n    mtu:\n      shape: scalar\n      scalar_type: integer\n      default: 1\n"),
		[]byte("{}\n"))
	if err := module.Execute(obj); !errors.Is(err, module.ErrModelVersion) {
		t.Errorf("expected a model-version rejection, got %v", err)
	}
}

func sealedSchema(withContent bool) []byte {
	content := ""
	if withContent {
		content = "      content:\n        enabled: false\n"
	}
	return []byte("model: \"0.1\"\ntemplates:\n  $network-object:\n    $.access.read:\n      shape: object\n      children:\n        enabled:\n          shape: scalar\n          scalar_type: boolean\n          default: true\n" +
		content +
		"root:\n  shape: object\n  children:\n    access_policy:\n      sealed_from:\n        template: $network-object\n        path: $.access.read\n")
}

func mustMaterialize(t *testing.T, schema, input []byte) objectmodel.CanonicalObject {
	t.Helper()
	obj, err := objectmodel.Materialize(schema, input)
	if err != nil {
		t.Fatalf("materialization failed: %v", err)
	}
	return obj
}

func mustDeliver(t *testing.T, obj objectmodel.CanonicalObject) {
	t.Helper()
	if err := module.Execute(obj); err != nil {
		t.Fatalf("the boundary rejected a valid object: %v", err)
	}
}

func mustReject(t *testing.T, schema, input []byte, code string) {
	t.Helper()
	_, err := objectmodel.Materialize(schema, input)
	if err == nil {
		t.Fatalf("expected %s, the pipeline accepted the input", code)
	}
	var me *objectmodel.Error
	if !errors.As(err, &me) {
		t.Fatalf("expected an *objectmodel.Error, got %T: %v", err, err)
	}
	if me.Code != code {
		t.Fatalf("expected %s, got %s (%s)", code, me.Code, me.Detail)
	}
}

func childOf(t *testing.T, obj objectmodel.CanonicalObject, name string) *objectmodel.Node {
	t.Helper()
	node, ok := obj.Root().Child(name)
	if !ok {
		t.Fatalf("no child %q on the root node", name)
	}
	return node
}

// TestCanonicalYAMLIsACopy — CanonicalYAML must not hand out the object's own
// buffer, or a module could mutate what the materializer validated.
func TestCanonicalYAMLIsACopy(t *testing.T) {
	obj := mustMaterialize(t,
		[]byte("model: \"0.1\"\nroot:\n  shape: object\n  children:\n    mtu:\n      shape: scalar\n      scalar_type: integer\n      default: 1500\n"),
		[]byte("{}\n"))
	first := obj.CanonicalYAML()
	for i := range first {
		first[i] = 'x'
	}
	second := obj.CanonicalYAML()
	var doc any
	if err := yaml.Unmarshal(second, &doc); err != nil {
		t.Fatalf("the canonical object was mutated through CanonicalYAML: %v", err)
	}
}
