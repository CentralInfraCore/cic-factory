package objectmodel

// valueKind is the arity of a node's payload (SPEC §2.1, `Value`).
type valueKind int

const (
	// kindAbsent is a staging state only: the node has no value yet. SPEC
	// §8.5 either fills it or the node does not exist.
	kindAbsent valueKind = iota
	kindScalar
	kindList
	kindMap
	kindOpaque
	// kindRaw is a primitive node's payload. The vectors keep it verbatim
	// rather than materializing it into CIC nodes; see docs/spec-defects.md SD-003.
	kindRaw
)

// Node is a CIC node (SPEC §2.1): exactly one `values` member (INV-001) and,
// in canonical form, exactly one `origin` member (INV-002), plus one member
// per primitive its schema declares (INV-022).
//
// Every field is unexported and there is no exported constructor, so a Node
// can only come out of Materialize. That is half of INV-032; CanonicalObject
// in materialize.go is the other half.
type Node struct {
	path   string
	isRoot bool
	eff    *effNode

	kind    valueKind
	scalar  any
	list    []*Node
	entries map[string]*Node
	order   []string
	opaque  any
	raw     any

	origin Origin

	// fromAbsence marks an object node that no author and no template
	// asserted. If nothing below it materializes, it does not exist.
	fromAbsence bool

	primitives map[string]*Node
	primOrder  []string

	// staging, populated by §8.4 and consumed by §8.6
	authoredPrims map[string]any
	extraMembers  map[string]any
}

// Path returns the node's address in the object ($.interface.mtu).
func (n *Node) Path() string { return n.path }

// Origin returns the node's authoring authority (SPEC §5).
func (n *Node) Origin() Origin { return n.origin }

// Child returns a child node of a structured payload.
func (n *Node) Child(name string) (*Node, bool) {
	if n.kind != kindMap {
		return nil, false
	}
	c, ok := n.entries[name]
	return c, ok
}

// Primitive returns a materialized primitive member of the node.
func (n *Node) Primitive(name string) (*Node, bool) {
	p, ok := n.primitives[name]
	return p, ok
}

// Scalar returns a scalar payload.
func (n *Node) Scalar() (any, bool) {
	if n.kind != kindScalar {
		return nil, false
	}
	return n.scalar, true
}

func (n *Node) setPrimitive(name string, p *Node) {
	if n.primitives == nil {
		n.primitives = map[string]*Node{}
	}
	if _, ok := n.primitives[name]; !ok {
		n.primOrder = append(n.primOrder, name)
	}
	n.primitives[name] = p
}
