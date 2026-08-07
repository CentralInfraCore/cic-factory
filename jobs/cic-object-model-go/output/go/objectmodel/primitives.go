package objectmodel

import "fmt"

// evaluatePrimitives is SPEC §8.6.
//
//	INPUT:  node tree with values materialized
//	OUTPUT: node tree with every schema-declared primitive materialized as a node
//	MUST:   materialize every declared primitive (INV-022); resolve `inherit`
//	        chains for `access` (INV-025)
//	MUST NOT: admit an unknown primitive (INV-021)
//
// The `inherit` chain resolution this stage is told to perform is not
// implemented, and cannot be in 0.1: INV-025's tri-state resolves against the
// PolicySurface, which SPEC §1 puts out of scope. materialization/013 records
// `inherit` verbatim rather than resolved, so no vector requires resolution
// either. Recorded as docs/spec-defects.md SD-012 — a normative MUST with no
// reachable semantics, not an omission this implementation chose.
func evaluatePrimitives(n *Node) error {
	// INV-021 — a node must not carry a member that is neither values,
	// origin, nor a member of the primitive set.
	if len(n.extraMembers) > 0 {
		k := sortedKeys(n.extraMembers)[0]
		return newError(CodeUnknownPrimitive, "INV-021", StagePrimitiveEvaluation,
			n.path+"."+k,
			fmt.Sprintf("`%s` is not a member of the primitive set (%s)", k, primitiveSetList()))
	}

	if !n.isRoot {
		if err := attachPrimitives(n); err != nil {
			return err
		}
	}
	// The root node carries `cic`, `values` and `origin` only. Every
	// materialization vector shows a root without `shape`, even though every
	// vector schema declares `root: shape: object` and INV-022 says a
	// canonical node MUST carry every primitive its schema declares.
	// docs/spec-defects.md SD-004; the corpus wins per SPEC §10.

	switch n.kind {
	case kindMap:
		for _, k := range n.order {
			if err := evaluatePrimitives(n.entries[k]); err != nil {
				return err
			}
		}
	case kindList:
		for _, item := range n.list {
			if err := evaluatePrimitives(item); err != nil {
				return err
			}
		}
	}
	return nil
}

func attachPrimitives(n *Node) error {
	s := n.eff.sch
	for _, name := range primitiveSet {
		authored, authoredOK := n.authoredPrims[name]

		var decl any
		declared := false
		if name == "shape" {
			// The `shape` primitive is assembled from the schema keywords
			// `shape:` and `scalar_type:`, not declared as a payload.
			if s.hasShape {
				sv := map[string]any{"type": s.shape}
				if s.scalarType != "" {
					sv["scalar_type"] = s.scalarType
				}
				decl, declared = sv, true
			}
		} else {
			decl, declared = s.prims[name]
		}

		var payload any
		var org Origin
		switch {
		case authoredOK:
			payload, org = authored, originYAML()
		case declared:
			payload, org = decl, originSchema()
		default:
			continue
		}

		normalized, err := normalizePrimitive(name, payload, n.path+"."+name)
		if err != nil {
			return err
		}
		// INV-003 — the primitive member is itself a CIC node: it has its own
		// values and its own origin.
		n.setPrimitive(name, &Node{
			path:   n.path + "." + name,
			kind:   kindRaw,
			raw:    normalized,
			origin: org,
		})
	}
	return nil
}

// normalizePrimitive turns a declared primitive payload into its canonical
// form. Only `access` has a form SPEC fixes (§6.4); everything else is
// carried through as declared.
//
// Note what is NOT done here: the payload is not materialized into CIC nodes.
// SPEC §2.2 motivates the model with "network.values.mtu.access.read is a
// first-class, addressable object", and INV-027 says a schema-known
// structured object must be recursively materialized — but every vector keeps
// primitive payloads as plain mappings. docs/spec-defects.md SD-003.
func normalizePrimitive(name string, payload any, path string) (any, error) {
	if name != "access" {
		return normalize(payload), nil
	}

	m, ok := asMap(payload)
	if !ok {
		return nil, newError(CodeTypeMismatch, "INV-024", StagePrimitiveEvaluation, path,
			"access must be a mapping of operations")
	}
	out := newOrderedMap()
	for _, op := range sortedKeys(m) {
		// INV-024 — the operations are `read` and `modify`. `write` is not a
		// valid operation name.
		if op != "read" && op != "modify" {
			return nil, newError(CodeInvalidAccessOperation, "INV-024", StagePrimitiveEvaluation,
				path+"."+op,
				fmt.Sprintf("`%s` is not a valid access operation; access declares `read` and `modify`", op))
		}
		opm, ok := asMap(m[op])
		if !ok {
			return nil, newError(CodeTypeMismatch, "INV-024", StagePrimitiveEvaluation,
				path+"."+op, "an access operation must be a mapping")
		}
		merged := make(map[string]any, len(opm)+1)
		for k, v := range opm {
			merged[k] = v
		}
		// INV-025 — inherit is per-operation and defaults to true.
		//
		// Injecting the default is what materialization/011 and /013 require,
		// but no invariant states that a primitive's sub-defaults are
		// materialized, and INV-026's `null` default for default_injection is
		// pointedly NOT injected by the same vectors. docs/spec-defects.md SD-001.
		if _, ok := merged["inherit"]; !ok {
			merged["inherit"] = true
		}
		// INV-026 — default_injection is invalid under modify: a denied write
		// has no value to inject.
		if op == "modify" {
			if _, ok := merged["default_injection"]; ok {
				return nil, newError(CodeDefaultInjectionOnModify, "INV-026", StagePrimitiveEvaluation,
					path+".modify.default_injection",
					"default_injection is valid under access.read only")
			}
		}
		out.set(op, normalize(merged))
	}
	return out, nil
}

func primitiveSetList() string {
	s := ""
	for i, p := range primitiveSet {
		if i > 0 {
			s += ", "
		}
		s += p
	}
	return s
}
