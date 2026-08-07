package objectmodel

import (
	"fmt"

	"gopkg.in/yaml.v3"
)

// CanonicalObject is Validated<Canonical<CICObject>> (SPEC INV-032): the type
// of a module's input, and the only thing that may cross the module boundary
// of SPEC §9.
//
// The unexported method is the enforcement. No package outside this one can
// implement the interface, so no package outside this one can produce a value
// of the type — "an invalid object has no representation that crosses the
// boundary" rather than "validate before you call".
//
// The residual hole is the nil interface value, which Go cannot forbid; a
// module boundary therefore still rejects nil explicitly (see ../module).
type CanonicalObject interface {
	// ModelVersion is the model this object conforms to (INV-033), which a
	// module must match against the version it declares (INV-034).
	ModelVersion() string
	// CanonicalYAML is the deterministic serialization (INV-030).
	CanonicalYAML() []byte
	// Root is the root CIC node.
	Root() *Node

	sealedByMaterializer()
}

type validatedCanonical struct {
	model string
	root  *Node
	bytes []byte
}

func (o *validatedCanonical) ModelVersion() string { return o.model }
func (o *validatedCanonical) Root() *Node          { return o.root }

func (o *validatedCanonical) CanonicalYAML() []byte {
	out := make([]byte, len(o.bytes))
	copy(out, o.bytes)
	return out
}

func (o *validatedCanonical) sealedByMaterializer() {}

// Materialize runs the pipeline of SPEC §8 and is the only producer of a
// CanonicalObject.
//
// The stages run in the order SPEC §8 fixes, and each is a separate function
// over the previous one's output: a later stage cannot observe input an
// earlier stage would have rejected, which is what makes the `stage:` field
// of every expected-error.yaml meaningful.
func Materialize(schemaYAML, inputYAML []byte) (CanonicalObject, error) {
	// Precedes §8: the schema itself (INV-010, INV-015, INV-005).
	schema, err := LoadSchema(schemaYAML)
	if err != nil {
		return nil, err
	}

	var input any
	if err := yaml.Unmarshal(inputYAML, &input); err != nil {
		return nil, newError(CodeMalformedDocument, "INV-007", StageEntryValidation, "$",
			fmt.Sprintf("authoring input is not valid YAML: %v", err))
	}
	if input == nil {
		input = map[string]any{}
	}

	// §8.1
	if err := entryValidate(schema, input); err != nil {
		return nil, err
	}
	// §8.2
	resolved, err := resolveReferences(schema, input)
	if err != nil {
		return nil, err
	}
	// §8.3
	eff, err := buildEffective(schema)
	if err != nil {
		return nil, err
	}
	// §8.4
	root, err := construct(eff, resolved, true, nil, false, "$", true)
	if err != nil {
		return nil, err
	}
	// §8.5
	root, err = materializeDefaults(root)
	if err != nil {
		return nil, err
	}
	if root == nil {
		return nil, newError(CodeMissingValues, "INV-001", StageDefaultMaterialization, "$",
			"the root node materialized to nothing")
	}
	// §8.6
	if err := evaluatePrimitives(root); err != nil {
		return nil, err
	}
	// §8.7
	doc := root.document(schema.model)
	if err := validateDocument(doc); err != nil {
		return nil, err
	}
	// §8.8
	out, err := encodeCanonical(doc)
	if err != nil {
		return nil, err
	}

	return &validatedCanonical{model: schema.model, root: root, bytes: out}, nil
}

// ValidateCanonicalDocument is SPEC §8.7 applied directly to an
// already-canonical object.
//
// conformance/validation/* needs this entry point: truth-table rows 7 and 8
// cannot be produced by any authoring input, because origin may not be
// authored at all (INV-007). They are reachable only as a materializer defect
// or a hand-forged object, so without a schema-free validation entry point
// two rows of the table would be unfalsifiable.
func ValidateCanonicalDocument(objectYAML []byte) error {
	var raw any
	if err := yaml.Unmarshal(objectYAML, &raw); err != nil {
		return newError(CodeMalformedDocument, "INV-001", StageFinalValidation, "$",
			fmt.Sprintf("object is not valid YAML: %v", err))
	}
	return validateDocument(normalize(raw))
}
