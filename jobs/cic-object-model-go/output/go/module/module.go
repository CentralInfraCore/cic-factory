// Package module is the module boundary of SPEC §9.
//
// It contains no provisioning logic. It exists so that INV-031 and INV-032
// have a boundary to be true of: docs/spec-vector-map.md marks both
// unvectorizable and assigns them to the implementation as source-level
// checks, and a boundary that does not exist cannot be checked.
package module

import (
	"errors"
	"fmt"

	"github.com/CentralInfraCore/cic-object-model/go/objectmodel"
)

// ModelVersion is the object model version this module declares it consumes
// (SPEC INV-034). A host must not hand it an object of any other version.
const ModelVersion = "0.1"

// ErrNilObject is returned for a nil CanonicalObject.
//
// INV-032 is enforced by objectmodel.CanonicalObject's unexported method: no
// other package can implement it, so no other package can construct one. Go
// has one residual hole — the nil interface value — which no type system
// trick closes, so the boundary closes it at runtime.
var ErrNilObject = errors.New("module: nil object at the boundary; INV-032 requires Validated<Canonical<CICObject>>")

// ErrModelVersion is returned when the host offers an object of a version
// this module has not declared (SPEC INV-034).
var ErrModelVersion = errors.New("module: undeclared object model version")

// Execute is the module entry point.
//
// Its parameter type is the whole of INV-032: it accepts
// objectmodel.CanonicalObject and nothing else. An Execute(map[string]any) —
// which SPEC §9 names explicitly as a violation — could not be given an
// object this package can trust, because the pipeline is the only thing that
// produces one.
func Execute(obj objectmodel.CanonicalObject) error {
	if obj == nil {
		return ErrNilObject
	}
	if obj.ModelVersion() != ModelVersion {
		return fmt.Errorf("%w: got %q, this module consumes %q",
			ErrModelVersion, obj.ModelVersion(), ModelVersion)
	}
	root := obj.Root()
	if root == nil {
		return ErrNilObject
	}
	// A real module would act here. What matters for the spec is what it can
	// no longer be handed: INV-031(a)-(g) are all eliminated upstream, and
	// boundary_test.go asserts that clause by clause.
	return nil
}
