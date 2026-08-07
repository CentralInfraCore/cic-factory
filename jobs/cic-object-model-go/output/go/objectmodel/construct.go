package objectmodel

import "fmt"

// construct is SPEC §8.4.
//
//	INPUT:  expanded tree
//	OUTPUT: every schema-known structured child represented as a CIC node
//	MUST:   apply the discriminator of §4 at every position; apply the
//	        closure rules of §7
//	MUST NOT: leave a schema-known child as a raw value (INV-027)
//
// Values that are absent here are left kindAbsent for §8.5; primitives are
// recorded but not evaluated until §8.6.
//
// `content` is a template's explicit value (conformance/README.md), which is
// what separates truth-table rows 3 and 4. It is threaded separately from the
// authored value so that a template-supplied value can never be mistaken for
// a yaml-supplied one — that mistake would produce origin [yaml] where the
// corpus requires [sealed(t,p)].
func construct(eff *effNode, authored any, authoredOK bool, content any, contentOK bool, path string, isRoot bool) (*Node, error) {
	if eff.hasContent && !contentOK {
		content, contentOK = eff.content, true
	}

	n := &Node{path: path, isRoot: isRoot, eff: eff}

	payload, payloadOK := authored, authoredOK
	if authoredOK && isEnvelope(eff.sch.shape, authored) {
		m, _ := asMap(authored)
		n.authoredPrims = map[string]any{}
		n.extraMembers = map[string]any{}
		payload, payloadOK = nil, false
		for _, k := range sortedKeys(m) {
			switch {
			case k == "values":
				payload, payloadOK = m[k], true
			case isPrimitiveName(k):
				n.authoredPrims[k] = m[k]
			default:
				// INV-021, raised at §8.6.
				n.extraMembers[k] = m[k]
			}
		}
	}

	switch eff.sch.shape {
	case shapeScalar:
		switch {
		case payloadOK:
			n.kind, n.scalar, n.origin = kindScalar, payload, originYAML()
		case contentOK:
			n.kind, n.scalar, n.origin = kindScalar, content, originSealed(eff.sealed)
		default:
			n.kind = kindAbsent
		}

	case shapeOpaque:
		// INV-028 — terminal. Preserved verbatim, never materialized into nodes.
		switch {
		case payloadOK:
			n.kind, n.opaque, n.origin = kindOpaque, deepCopy(payload), originYAML()
		case contentOK:
			n.kind, n.opaque, n.origin = kindOpaque, deepCopy(content), originSealed(eff.sealed)
		default:
			n.kind = kindAbsent
		}

	case shapeList:
		var src []any
		var org Origin
		switch {
		case payloadOK:
			l, ok := payload.([]any)
			if !ok {
				return nil, newError(CodeTypeMismatch, "INV-027", StageNodeConstruction, path,
					"a list position requires a sequence payload")
			}
			src, org = l, originYAML()
		case contentOK:
			l, ok := content.([]any)
			if !ok {
				return nil, newError(CodeTypeMismatch, "INV-027", StageNodeConstruction, path,
					"template content at a list position must be a sequence")
			}
			src, org = l, originSealed(eff.sealed)
		default:
			n.kind = kindAbsent
			return n, nil
		}
		if eff.item == nil {
			return nil, newError(CodeSchemaShapeMissing, "INV-027", StageNodeConstruction, path,
				"a list position must declare `item`")
		}
		n.kind, n.origin = kindList, org
		for i, e := range src {
			ip := fmt.Sprintf("%s[%d]", path, i)
			var child *Node
			var err error
			if payloadOK {
				child, err = construct(eff.item, e, true, nil, false, ip, false)
			} else {
				child, err = construct(eff.item, nil, false, e, true, ip, false)
			}
			if err != nil {
				return nil, err
			}
			// INV-027 — a list payload is List<CICNode>, not List<Scalar>.
			n.list = append(n.list, child)
		}

	case shapeObject:
		var authoredChildren map[string]any
		switch {
		case payloadOK:
			m, ok := asMap(payload)
			if !ok {
				return nil, newError(CodeTypeMismatch, "INV-027", StageNodeConstruction, path,
					"a structured object position requires a mapping payload")
			}
			// SPEC §7.1 — `foo: {}` is the author asserting the node exists.
			authoredChildren, n.origin = m, originYAML()
		case eff.sealed != nil:
			// The template defined and closed the node; its existence is the
			// template's, not a default's. Row 3/4 differ only below here.
			n.origin = originSealed(eff.sealed)
		case isRoot:
			n.origin = originYAML()
		default:
			n.origin, n.fromAbsence = originSchema(), true
		}

		var contentChildren map[string]any
		if contentOK {
			if cm, ok := asMap(content); ok {
				contentChildren = cm
			}
		}

		n.kind = kindMap
		n.entries = map[string]*Node{}
		for _, c := range eff.childOrder {
			cv, cok := authoredChildren[c]
			ct, ctok := contentChildren[c]
			child, err := construct(eff.children[c], cv, cok, ct, ctok, path+"."+c, false)
			if err != nil {
				return nil, err
			}
			n.entries[c] = child
			n.order = append(n.order, c)
		}

	default:
		return nil, newError(CodeSchemaShapeMissing, "INV-008", StageNodeConstruction, path,
			"the schema declares no shape at this position")
	}

	return n, nil
}
