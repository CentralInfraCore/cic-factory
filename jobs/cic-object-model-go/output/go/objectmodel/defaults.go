package objectmodel

import "fmt"

// materializeDefaults is SPEC §8.5.
//
//	INPUT:  node tree with authored values
//	OUTPUT: node tree with every absent defaultable value filled
//	MUST:   set origin [schema] on every node filled from a default, and
//	        [sealed(t,p), schema] where the default came from a sealed
//	        template's schema
//	MUST NOT: produce a node whose origin holds both yaml and schema (INV-017)
//	FAILURE: a required value neither authored nor defaultable -> reject
//
// A nil return with a nil error means the node does not exist: it was neither
// authored, nor template-supplied, nor defaultable, nor required. SPEC has no
// rule for that case and no vector reaches it (docs/spec-defects.md SD-007);
// omitting is the only option that does not invent a value or violate INV-001.
func materializeDefaults(n *Node) (*Node, error) {
	switch n.kind {
	case kindAbsent:
		s := n.eff.sch
		switch {
		case s.hasDefault:
			org := originSchema()
			if n.eff.sealed != nil {
				// Truth-table row 4: the template closed the node, the value
				// came from the template node's own schema default.
				org = originSealedSchema(n.eff.sealed)
			}
			return nodeFromDefault(n, s.def, org)
		case s.required:
			return nil, newError(CodeRequiredValueMissing, "INV-022", StageDefaultMaterialization,
				n.path, "a required value was neither authored nor defaultable")
		default:
			return nil, nil
		}

	case kindMap:
		kept := make([]string, 0, len(n.order))
		for _, k := range n.order {
			child, err := materializeDefaults(n.entries[k])
			if err != nil {
				return nil, err
			}
			if child == nil {
				delete(n.entries, k)
				continue
			}
			n.entries[k] = child
			kept = append(kept, k)
		}
		n.order = kept
		if n.fromAbsence && len(n.order) == 0 {
			// Nothing below it materialized, and nobody asserted it.
			return nil, nil
		}

	case kindList:
		for i, item := range n.list {
			child, err := materializeDefaults(item)
			if err != nil {
				return nil, err
			}
			if child == nil {
				return nil, newError(CodeRequiredValueMissing, "INV-001", StageDefaultMaterialization,
					item.path, "a list element has no value and no default")
			}
			n.list[i] = child
		}
	}
	return n, nil
}

// nodeFromDefault fills an absent node from its schema default.
//
// An object-shaped position takes no default literal: SPEC §7.1 says a
// structured node materializes from its children's defaults, not from an
// object-level default. Declaring one is therefore a schema error rather than
// a second, competing mechanism.
func nodeFromDefault(n *Node, lit any, org Origin) (*Node, error) {
	n.origin = org
	switch n.eff.sch.shape {
	case shapeScalar:
		n.kind, n.scalar = kindScalar, lit
	case shapeOpaque:
		n.kind, n.opaque = kindOpaque, deepCopy(lit)
	case shapeList:
		l, ok := lit.([]any)
		if !ok {
			return nil, newError(CodeTypeMismatch, "INV-027", StageDefaultMaterialization, n.path,
				"the default at a list position must be a sequence")
		}
		if n.eff.item == nil {
			return nil, newError(CodeSchemaShapeMissing, "INV-027", StageDefaultMaterialization, n.path,
				"a list position must declare `item`")
		}
		n.kind = kindList
		for i, e := range l {
			child := &Node{path: fmt.Sprintf("%s[%d]", n.path, i), eff: n.eff.item}
			filled, err := nodeFromDefault(child, e, org)
			if err != nil {
				return nil, err
			}
			n.list = append(n.list, filled)
		}
	case shapeObject:
		return nil, newError(CodeTypeMismatch, "INV-027", StageDefaultMaterialization, n.path,
			"a structured object position must not declare a default literal; SPEC §7.1 materializes it from its children's defaults")
	default:
		return nil, newError(CodeSchemaShapeMissing, "INV-008", StageDefaultMaterialization, n.path,
			"the schema declares no shape at this position")
	}
	return n, nil
}
