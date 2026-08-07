// Package forge MUST NOT COMPILE.
//
// It is the negative artifact docs/spec-vector-map.md requires for INV-032:
// "Unconstructibility is a compile-time property of a type; no data file can
// demonstrate it, because the failure mode is code that compiles when it
// should not." A vector cannot fail on code that compiles. This file can.
//
// It lives under testdata/ so that `go build ./...` and `go vet ./...` skip
// it; ../inv032_test.go builds it by explicit path and asserts the failure.
package forge

import "github.com/CentralInfraCore/cic-object-model/go/objectmodel"

// Forged implements every exported method of objectmodel.CanonicalObject and
// is still not one: the interface carries an unexported marker method that
// only the materializer's package can supply.
type Forged struct{}

func (Forged) ModelVersion() string    { return "0.1" }
func (Forged) CanonicalYAML() []byte   { return []byte("cic:\n  model: \"0.1\"\n") }
func (Forged) Root() *objectmodel.Node { return nil }

// INV-032: a value of Validated<Canonical<CICObject>> must be constructible
// only by the core materializer. This assignment is the attempt, and it must
// be rejected by the compiler.
var _ objectmodel.CanonicalObject = Forged{}

// The concrete node type is equally closed: every field is unexported, so a
// composite literal from another package cannot populate one.
var _ = objectmodel.Node{
	path:   "$",
	origin: nil,
}
