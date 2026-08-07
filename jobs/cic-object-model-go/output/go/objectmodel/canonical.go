package objectmodel

// project is the projection half of SPEC §8.8: the node tree becomes the
// document the canonical serializer writes and the final validator reads.
//
// Member order is values, origin, then primitives in the order SPEC §6.1
// states the atom set. SPEC §8.8 defines no order; see docs/spec-defects.md SD-010.
func (n *Node) project() any {
	m := newOrderedMap()
	m.set("values", n.projectValue())
	m.set("origin", n.origin.project())
	for _, name := range primitiveSet {
		if p, ok := n.primitives[name]; ok {
			m.set(name, p.project())
		}
	}
	return m
}

func (n *Node) projectValue() any {
	switch n.kind {
	case kindScalar:
		return n.scalar
	case kindOpaque:
		// INV-028 / INV-011 — verbatim. Keys named like primitives below
		// here are domain data.
		return normalize(n.opaque)
	case kindRaw:
		return n.raw
	case kindList:
		out := make([]any, 0, len(n.list))
		for _, c := range n.list {
			out = append(out, c.project())
		}
		return out
	case kindMap:
		m := newOrderedMap()
		for _, k := range n.order {
			m.set(k, n.entries[k].project())
		}
		return m
	}
	return nil
}

// document stamps the model version (INV-033) onto the root node's
// projection. The root carries no primitives; see docs/spec-defects.md SD-004.
func (n *Node) document(model string) any {
	cic := newOrderedMap()
	cic.set("model", model)

	m := newOrderedMap()
	m.set("cic", cic)
	m.set("values", n.projectValue())
	m.set("origin", n.origin.project())
	return m
}
