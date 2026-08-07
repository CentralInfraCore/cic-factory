package objectmodel

import "fmt"

// entryValidate is SPEC §8.1.
//
//	INPUT:  raw authoring tree
//	OUTPUT: structurally legal authoring tree
//	MUST:   reject an `origin` member (INV-007); reject authoring at or below
//	        a sealed boundary (INV-019); reject undeclared arbitrary objects
//	        (INV-029)
//	MUST NOT: resolve references, expand templates, or apply defaults
//
// It deliberately does not reject an unknown envelope member: SPEC §8.6 owns
// INV-021, and invalid/006_unknown_primitive asserts stage
// `primitive-evaluation`. Rejecting it here would be the right code at the
// wrong stage, which conformance/README.md calls a failure.
func entryValidate(s *Schema, input any) error {
	return entryWalk(s.root, input, "$")
}

// isEnvelope is the discriminator table of SPEC §4.3. It is called with the
// schema-declared shape at the position — never with key inspection alone
// (INV-008).
func isEnvelope(shape string, v any) bool {
	m, isMap := asMap(v)
	if !isMap {
		return false // short form, at every shape
	}
	switch shape {
	case shapeScalar, shapeList:
		return true
	case shapeObject:
		// INV-009 — envelope if and only if the mapping directly contains
		// the key `values`. INV-010 keeps that total.
		_, ok := m["values"]
		return ok
	case shapeOpaque:
		return false // SPEC §7: payload, always
	}
	return false
}

func entryWalk(sch *schemaNode, v any, path string) error {
	// INV-019 — authoring is closed at and below a sealed boundary, and the
	// rejection is structural and immediate: the traversal stops here rather
	// than letting the value reach reference resolution or expansion.
	if sch.sealed != nil {
		return newError(CodeAuthoringBelowSealed, "INV-019", StageEntryValidation,
			firstLeafPath(v, path),
			fmt.Sprintf("authoring is closed at and below %s, which originates from sealed template %s at %s",
				path, sch.sealed.template, sch.sealed.path))
	}

	if sch.shape == shapeOpaque {
		// INV-028 / INV-011 — terminal. Nothing below it is interpreted, so
		// nothing below it can be rejected for carrying a primitive name.
		return nil
	}

	if isEnvelope(sch.shape, v) {
		m, _ := asMap(v)
		for _, k := range sortedKeys(m) {
			switch {
			case k == "values":
				if err := entryPayload(sch, m[k], path); err != nil {
					return err
				}
			case k == "origin":
				// INV-007 — origin is computed, never declared. This is what
				// makes it trustworthy: a node cannot claim its own provenance.
				return newError(CodeOriginDeclaredInInput, "INV-007", StageEntryValidation,
					path+".origin",
					"origin is computed by the materializer and must not appear in authoring input")
			case isPrimitiveName(k):
				// An instance-level primitive override. SPEC fixes the
				// internal structure of `access` only (§6.4); it is checked
				// at §8.6, where primitive semantics are resolved.
			default:
				// Unknown envelope member — deferred to §8.6 (INV-021).
			}
		}
		return nil
	}

	return entryPayload(sch, v, path)
}

func entryPayload(sch *schemaNode, v any, path string) error {
	switch sch.shape {
	case shapeOpaque:
		return nil
	case shapeScalar:
		return nil
	case shapeList:
		l, ok := v.([]any)
		if !ok {
			return newError(CodeTypeMismatch, "INV-008", StageEntryValidation, path,
				"a list position requires a sequence payload")
		}
		for i, e := range l {
			if err := entryWalk(sch.item, e, fmt.Sprintf("%s[%d]", path, i)); err != nil {
				return err
			}
		}
		return nil
	case shapeObject:
		m, ok := asMap(v)
		if !ok {
			return newError(CodeTypeMismatch, "INV-008", StageEntryValidation, path,
				"a structured object position requires a mapping payload")
		}
		for _, k := range sortedKeys(m) {
			child, declared := sch.children[k]
			if !declared {
				// INV-029 — neither schema-known nor declared opaque.
				// Opacity is declared, never inferred.
				//
				// INV-029 literally says "an object"; this rejects an
				// undeclared scalar too, because accepting one would mean
				// silently dropping authored data. See docs/spec-defects.md SD-008.
				return newError(CodeUndeclaredObject, "INV-029", StageEntryValidation,
					path+"."+k,
					fmt.Sprintf("%s.%s is neither declared in the schema nor declared opaque", path, k))
			}
			if err := entryWalk(child, m[k], path+"."+k); err != nil {
				return err
			}
		}
		return nil
	}
	return newError(CodeSchemaShapeMissing, "INV-008", StageEntryValidation, path,
		"the schema declares no shape at this position; the discriminator of SPEC §4.3 needs one")
}

// firstLeafPath names the deepest authored position of an illegal authoring
// attempt, which is what invalid/001 and invalid/002 assert
// ($.access_policy.enabled, not $.access_policy).
func firstLeafPath(v any, path string) string {
	if m, ok := asMap(v); ok {
		if len(m) == 0 {
			return path
		}
		k := sortedKeys(m)[0]
		return firstLeafPath(m[k], path+"."+k)
	}
	if l, ok := v.([]any); ok {
		if len(l) == 0 {
			return path
		}
		return firstLeafPath(l[0], path+"[0]")
	}
	return path
}
