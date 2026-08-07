package objectmodel

import "fmt"

// validateDocument is SPEC §8.7.
//
//	INPUT:  fully materialized node tree
//	OUTPUT: validated node tree
//	MUST:   enforce the origin grammar and truth table (§5.2, §5.3); confirm
//	        INV-001 and INV-002 hold at every node
//
// It runs on the projected document rather than on *Node so that the same
// rules apply to an object the materializer just built and to a hand-forged
// one presented at the module boundary (conformance/validation/*). That is
// the only way row 7 and row 8 of the truth table are reachable at all.
//
// It has to identify nodes without a schema, by looking for a `values` key —
// exactly what INV-008 forbids ("MUST NOT decide this by inspecting keys
// alone"). There is no alternative: validation/* supplies no schema.
// docs/spec-defects.md SD-013.
func validateDocument(doc any) error {
	m, ok := doc.(*orderedMap)
	if !ok {
		return newError(CodeMalformedDocument, "INV-001", StageFinalValidation, "$",
			"a canonical object must be a mapping")
	}

	// INV-033 — every canonical CIC object carries the model version it
	// conforms to. Without it a host cannot decide whether delivery to a
	// module is safe (INV-034).
	if err := validateModelVersion(m); err != nil {
		return err
	}
	return validateNode(m, "$", true)
}

func validateModelVersion(m *orderedMap) error {
	missing := newError(CodeMissingModelVersion, "INV-033", StageFinalValidation, "$.cic.model",
		"every canonical CIC object must carry the model version it conforms to")
	cic, ok := m.get("cic")
	if !ok {
		return missing
	}
	cm, ok := cic.(*orderedMap)
	if !ok {
		return missing
	}
	mv, ok := cm.get("model")
	if !ok || mv == nil || fmt.Sprint(mv) == "" {
		return missing
	}
	return nil
}

func validateNode(m *orderedMap, path string, isDocRoot bool) error {
	// INV-001 / INV-002.
	if !m.has("values") {
		return newError(CodeMissingValues, "INV-001", StageFinalValidation, path+".values",
			"every CIC node must have exactly one `values` member")
	}
	if !m.has("origin") {
		return newError(CodeMissingOrigin, "INV-002", StageFinalValidation, path+".origin",
			"every CIC node in canonical form must have exactly one `origin` member")
	}

	for _, k := range m.keys {
		switch {
		case k == "values" || k == "origin":
		case isDocRoot && k == "cic":
			// The version stamp of INV-033. Strictly it makes the root node
			// carry a member that is neither values, origin nor a primitive,
			// which INV-021 forbids. docs/spec-defects.md SD-004.
		case k == "description" || k == "descr":
			// INV-006 — documentation is a property of the schema.
			return newError(CodeDocumentationOnNode, "INV-006", StageFinalValidation, path+"."+k,
				"documentation must be obtained from the schema, not carried on the node")
		case k == "default":
			// INV-012 — superseded by origin.
			return newError(CodeDefaultMemberOnNode, "INV-012", StageFinalValidation, path+"."+k,
				"value provenance is expressed through origin; a `default` member is not part of the canonical node")
		case isPrimitiveName(k):
		default:
			return newError(CodeUnknownPrimitive, "INV-021", StageFinalValidation, path+"."+k,
				fmt.Sprintf("`%s` is not a member of the primitive set (%s)", k, primitiveSetList()))
		}
	}

	if err := validateOrigin(m.vals["origin"], path+".origin"); err != nil {
		return err
	}

	// INV-003 — each primitive member is itself a CIC node.
	for _, k := range m.keys {
		if !isPrimitiveName(k) {
			continue
		}
		pm, ok := m.vals[k].(*orderedMap)
		if !ok {
			return newError(CodeMalformedDocument, "INV-003", StageFinalValidation, path+"."+k,
				"a primitive member must itself be a CIC node")
		}
		if err := validateNode(pm, path+"."+k, false); err != nil {
			return err
		}
	}

	return validatePayload(m.vals["values"], path)
}

func validatePayload(v any, path string) error {
	switch t := v.(type) {
	case *orderedMap:
		for _, k := range t.keys {
			child, ok := t.vals[k].(*orderedMap)
			if ok && child.has("values") {
				if err := validateNode(child, path+"."+k, false); err != nil {
					return err
				}
			}
		}
	case []any:
		for i, e := range t {
			child, ok := e.(*orderedMap)
			if ok && child.has("values") {
				if err := validateNode(child, fmt.Sprintf("%s[%d]", path, i), false); err != nil {
					return err
				}
			}
		}
	}
	return nil
}

// validateOrigin enforces SPEC §5.2 (the grammar, INV-013) and §5.3 (the
// truth table, INV-016 / INV-017 / INV-018), plus INV-004 and INV-020.
func validateOrigin(v any, path string) error {
	// INV-004 — origin is terminal. If it has been expanded into a node it
	// would need an origin of its own, without end.
	if _, isMap := v.(*orderedMap); isMap {
		return newError(CodeOriginNotTerminal, "INV-004", StageFinalValidation, path,
			"origin must be a value in the grammar of SPEC §5.2, not a CIC node; it must not carry values, origin or primitives")
	}
	terms, ok := v.([]any)
	if !ok {
		return newError(CodeOriginNotTerminal, "INV-004", StageFinalValidation, path,
			"origin must be a sequence of origin terms")
	}
	// INV-018 — row 8. Every materialized node has an authority.
	if len(terms) == 0 {
		return newError(CodeOriginEmpty, "INV-018", StageFinalValidation, path,
			"origin must not be empty; the node's authority is unattributable")
	}

	var hasYAML, hasSchema, hasSealed bool
	for _, t := range terms {
		switch tv := t.(type) {
		case string:
			switch tv {
			case string(OriginYAML):
				hasYAML = true
			case string(OriginSchema):
				hasSchema = true
			case string(OriginSealed):
				// INV-020 — origin `sealed` is always a 2-arity constructor.
				// The bare token belongs to the aggregate slot-mode vocabulary.
				return newError(CodeOriginGrammar, "INV-020", StageFinalValidation, path,
					"the bare token `sealed` is not a valid origin term; origin sealed is always a constructor carrying template and path")
			default:
				return newError(CodeOriginGrammar, "INV-013", StageFinalValidation, path,
					fmt.Sprintf("`%s` is not an origin term", tv))
			}
		case *orderedMap:
			sv, ok := tv.get("sealed")
			if !ok {
				return newError(CodeOriginGrammar, "INV-013", StageFinalValidation, path,
					"the only constructor term in the origin grammar is `sealed`")
			}
			sm, ok := sv.(*orderedMap)
			if !ok {
				return newError(CodeSealedMissingTemplateOrPath, "INV-015", StageFinalValidation, path,
					"a sealed term must carry both template and path")
			}
			tpl, tok := sm.get("template")
			pth, pok := sm.get("path")
			if !tok || !pok || tpl == nil || pth == nil {
				// INV-015 — template identity alone is not provenance.
				return newError(CodeSealedMissingTemplateOrPath, "INV-015", StageFinalValidation, path,
					"a sealed term must carry both template and path")
			}
			hasSealed = true
		default:
			return newError(CodeOriginGrammar, "INV-013", StageFinalValidation, path,
				"an origin term must be `yaml`, `schema`, or a sealed constructor")
		}
	}

	// INV-017 — row 7. A single effective value is either explicitly
	// supplied or defaulted; it cannot be both.
	if hasYAML && hasSchema {
		return newError(CodeOriginYAMLSchemaConflict, "INV-017", StageFinalValidation, path,
			"origin holds both `yaml` and `schema`; these are mutually exclusive value sources")
	}
	// INV-016 — rows 5 and 6. sealed means authoring is closed at and below
	// this node.
	if hasSealed && hasYAML {
		return newError(CodeOriginSealedYAMLConflict, "INV-016", StageFinalValidation, path,
			"origin holds both `sealed` and `yaml`; a yaml-sourced value below a sealed boundary is structurally illegal")
	}
	return nil
}
