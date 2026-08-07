package objectmodel

import "fmt"

// Stage names a stage of the materialization pipeline (SPEC §8).
//
// The four stage names that conformance vectors assert on
// (schema-load, entry-validation, primitive-evaluation, final-validation)
// are fixed by conformance/README.md's error table and by the `stage:` field
// of every expected-error.yaml. The remaining names are this
// implementation's, because SPEC §8 numbers its stages but does not name
// them; see docs/spec-defects.md (SD-002).
type Stage string

const (
	// StageSchemaLoad precedes SPEC §8: the schema is checked before any
	// authoring input is looked at. SPEC §8 does not list this stage, but
	// three vectors require it. See docs/spec-defects.md (SD-002).
	StageSchemaLoad Stage = "schema-load"
	// StageEntryValidation is SPEC §8.1.
	StageEntryValidation Stage = "entry-validation"
	// StageReferenceResolution is SPEC §8.2.
	StageReferenceResolution Stage = "reference-resolution"
	// StageSealedExpansion is SPEC §8.3.
	StageSealedExpansion Stage = "sealed-expansion"
	// StageNodeConstruction is SPEC §8.4.
	StageNodeConstruction Stage = "node-construction"
	// StageDefaultMaterialization is SPEC §8.5.
	StageDefaultMaterialization Stage = "default-materialization"
	// StagePrimitiveEvaluation is SPEC §8.6.
	StagePrimitiveEvaluation Stage = "primitive-evaluation"
	// StageFinalValidation is SPEC §8.7.
	StageFinalValidation Stage = "final-validation"
	// StageCanonicalization is SPEC §8.8.
	StageCanonicalization Stage = "canonicalization"
)

// Error codes.
//
// The first block is the set named in conformance/README.md and/or asserted
// by a vector's expected-error.yaml. The second block is codes this
// implementation had to introduce because a normative FAILURE clause in
// SPEC §8 has no code and no vector; each is listed in docs/spec-defects.md.
const (
	// --- codes asserted by conformance vectors ---
	CodeOriginDeclaredInInput       = "E_ORIGIN_DECLARED_IN_INPUT"
	CodeAuthoringBelowSealed        = "E_AUTHORING_BELOW_SEALED"
	CodeUndeclaredObject            = "E_UNDECLARED_OBJECT"
	CodeSchemaReservedChildValues   = "E_SCHEMA_RESERVED_CHILD_VALUES"
	CodeSealedMissingTemplateOrPath = "E_SEALED_MISSING_TEMPLATE_OR_PATH"
	CodeUnknownPrimitive            = "E_UNKNOWN_PRIMITIVE"
	CodeCyclicPrimitiveDeclaration  = "E_CYCLIC_PRIMITIVE_DECLARATION"
	CodeOriginYAMLSchemaConflict    = "E_ORIGIN_YAML_SCHEMA_CONFLICT"
	CodeOriginEmpty                 = "E_ORIGIN_EMPTY"
	CodeOriginNotTerminal           = "E_ORIGIN_NOT_TERMINAL"
	CodeDocumentationOnNode         = "E_DOCUMENTATION_ON_NODE"
	CodeDefaultMemberOnNode         = "E_DEFAULT_MEMBER_ON_NODE"
	CodeMissingModelVersion         = "E_MISSING_MODEL_VERSION"

	// --- codes with no vector and no name in the spec (docs/spec-defects.md) ---
	CodeMalformedDocument        = "E_MALFORMED_DOCUMENT"
	CodeUnknownSchemaKey         = "E_UNKNOWN_SCHEMA_KEY"
	CodeSchemaShapeMissing       = "E_SCHEMA_SHAPE_MISSING"
	CodeTemplateNotFound         = "E_TEMPLATE_NOT_FOUND"
	CodeTypeMismatch             = "E_TYPE_MISMATCH"
	CodeRequiredValueMissing     = "E_REQUIRED_VALUE_MISSING"
	CodeInvalidAccessOperation   = "E_INVALID_ACCESS_OPERATION"
	CodeDefaultInjectionOnModify = "E_DEFAULT_INJECTION_ON_MODIFY"
	CodeOriginSealedYAMLConflict = "E_ORIGIN_SEALED_YAML_CONFLICT"
	CodeOriginGrammar            = "E_ORIGIN_GRAMMAR"
	CodeMissingValues            = "E_MISSING_VALUES"
	CodeMissingOrigin            = "E_MISSING_ORIGIN"
)

// Error is the single error type the materializer raises. Every rejection
// names the code, the invariant it enforces, the pipeline stage it was
// raised at and the path it applies to — the four fields every
// expected-error.yaml asserts on.
type Error struct {
	Code      string
	Invariant string
	Stage     Stage
	Path      string
	Detail    string
}

func (e *Error) Error() string {
	return fmt.Sprintf("%s (%s) at %s [stage %s]: %s",
		e.Code, e.Invariant, e.Path, e.Stage, e.Detail)
}

func newError(code, invariant string, stage Stage, path, detail string) *Error {
	return &Error{Code: code, Invariant: invariant, Stage: stage, Path: path, Detail: detail}
}
