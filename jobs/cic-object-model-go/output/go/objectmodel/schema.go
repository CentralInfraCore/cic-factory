package objectmodel

import (
	"fmt"
	"slices"

	"gopkg.in/yaml.v3"
)

// primitiveSet is the eight irreducible atoms (SPEC §6.1). The order is the
// order SPEC §6.1 states them in, and it is also the canonical member order
// of a node (see canonical.go).
//
// D-003 was amended on 2026-05-04 to absorb D-011 and now says eight, not
// seven; the KB snapshot chunk c4255 still says seven. SPEC §6.1 is the
// authority here and it says eight.
var primitiveSet = []string{
	"shape", "role", "behavior", "contract", "address", "identity", "event", "access",
}

func isPrimitiveName(k string) bool { return slices.Contains(primitiveSet, k) }

// Shapes the vector schema language declares (conformance/README.md).
const (
	shapeScalar = "scalar"
	shapeList   = "list"
	shapeObject = "object"
	shapeOpaque = "opaque"
)

// schemaKeywords are the non-primitive keys of the vector schema language.
// `shape` is both a keyword and a primitive name: it is declared as a
// keyword (`shape: scalar` plus a sibling `scalar_type:`) and materialized
// as the `shape` primitive node (see primitives.go).
var schemaKeywords = map[string]bool{
	"shape": true, "scalar_type": true, "default": true, "required": true,
	"children": true, "item": true, "sealed_from": true, "content": true,
}

type sealedRef struct {
	template    string
	path        string
	hasTemplate bool
	hasPath     bool
}

type schemaNode struct {
	shape      string
	hasShape   bool
	scalarType string
	def        any
	hasDefault bool
	required   bool
	children   map[string]*schemaNode
	childOrder []string
	item       *schemaNode
	sealed     *sealedRef
	prims      map[string]any
	primOrder  []string
}

type templateEntry struct {
	node       *schemaNode
	content    any
	hasContent bool
}

// Schema is a loaded, schema-load-validated CIC schema.
type Schema struct {
	model     string
	root      *schemaNode
	templates map[string]map[string]*templateEntry
}

// LoadSchema parses and validates a schema. The checks it runs — INV-010,
// INV-015 and INV-005 — are the three the corpus places at stage
// `schema-load`, a stage SPEC §8 does not list (docs/spec-defects.md SD-002).
func LoadSchema(data []byte) (*Schema, error) {
	var raw any
	if err := yaml.Unmarshal(data, &raw); err != nil {
		return nil, newError(CodeMalformedDocument, "INV-013", StageSchemaLoad, "$",
			fmt.Sprintf("schema is not valid YAML: %v", err))
	}
	m, ok := asMap(raw)
	if !ok {
		return nil, newError(CodeMalformedDocument, "INV-013", StageSchemaLoad, "$",
			"schema must be a mapping")
	}

	s := &Schema{templates: map[string]map[string]*templateEntry{}}
	if mv, ok := m["model"]; ok && mv != nil {
		s.model = fmt.Sprint(mv)
	}

	rootRaw, ok := m["root"]
	if !ok {
		return nil, newError(CodeMalformedDocument, "INV-013", StageSchemaLoad, "$.root",
			"schema must declare a root node")
	}
	root, err := parseSchemaNode(rootRaw, "$")
	if err != nil {
		return nil, err
	}
	s.root = root

	if tRaw, ok := m["templates"]; ok && tRaw != nil {
		tm, ok := asMap(tRaw)
		if !ok {
			return nil, newError(CodeMalformedDocument, "INV-015", StageSchemaLoad, "$templates",
				"templates must be a mapping")
		}
		for _, name := range sortedKeys(tm) {
			pm, ok := asMap(tm[name])
			if !ok {
				return nil, newError(CodeMalformedDocument, "INV-015", StageSchemaLoad,
					"$templates."+name, "a template must be a mapping of path to node")
			}
			s.templates[name] = map[string]*templateEntry{}
			for _, p := range sortedKeys(pm) {
				entryPath := "$templates." + name + "." + p
				node, err := parseSchemaNode(pm[p], entryPath)
				if err != nil {
					return nil, err
				}
				entry := &templateEntry{node: node}
				if em, ok := asMap(pm[p]); ok {
					if c, ok := em["content"]; ok {
						entry.content, entry.hasContent = c, true
					}
				}
				s.templates[name][p] = entry
			}
		}
	}

	if err := s.schemaLoadChecks(); err != nil {
		return nil, err
	}
	return s, nil
}

func parseSchemaNode(raw any, path string) (*schemaNode, error) {
	m, ok := asMap(raw)
	if !ok {
		return nil, newError(CodeMalformedDocument, "INV-013", StageSchemaLoad, path,
			"a schema node must be a mapping")
	}
	n := &schemaNode{
		children: map[string]*schemaNode{},
		prims:    map[string]any{},
	}
	for _, k := range sortedKeys(m) {
		v := m[k]
		switch {
		case k == "shape":
			n.shape, n.hasShape = fmt.Sprint(v), true
		case k == "scalar_type":
			n.scalarType = fmt.Sprint(v)
		case k == "default":
			n.def, n.hasDefault = v, true
		case k == "required":
			b, _ := v.(bool)
			n.required = b
		case k == "content":
			// consumed by the template layer, not part of the node
		case k == "children":
			cm, ok := asMap(v)
			if !ok {
				return nil, newError(CodeMalformedDocument, "INV-013", StageSchemaLoad,
					path+".children", "children must be a mapping")
			}
			for _, cn := range sortedKeys(cm) {
				child, err := parseSchemaNode(cm[cn], path+"."+cn)
				if err != nil {
					return nil, err
				}
				n.children[cn] = child
				n.childOrder = append(n.childOrder, cn)
			}
		case k == "item":
			item, err := parseSchemaNode(v, path+"[]")
			if err != nil {
				return nil, err
			}
			n.item = item
		case k == "sealed_from":
			sm, ok := asMap(v)
			if !ok {
				return nil, newError(CodeSealedMissingTemplateOrPath, "INV-015", StageSchemaLoad,
					path+".sealed_from", "sealed_from must be a mapping carrying template and path")
			}
			ref := &sealedRef{}
			if t, ok := sm["template"]; ok && t != nil {
				ref.template, ref.hasTemplate = fmt.Sprint(t), true
			}
			if p, ok := sm["path"]; ok && p != nil {
				ref.path, ref.hasPath = fmt.Sprint(p), true
			}
			n.sealed = ref
		case isPrimitiveName(k):
			n.prims[k] = v
			n.primOrder = append(n.primOrder, k)
		case schemaKeywords[k]:
			// exhaustive above; kept for clarity
		default:
			// Fail closed. SPEC does not define the schema language, so an
			// unrecognised key cannot be assumed inert (docs/spec-defects.md SD-011).
			return nil, newError(CodeUnknownSchemaKey, "INV-021", StageSchemaLoad, path+"."+k,
				fmt.Sprintf("`%s` is neither a schema keyword nor a primitive name", k))
		}
	}
	return n, nil
}

func (s *Schema) schemaLoadChecks() error {
	if err := checkSchemaNode(s.root, "$"); err != nil {
		return err
	}
	for _, name := range sortedTemplateNames(s.templates) {
		paths := s.templates[name]
		for _, p := range sortedTemplatePaths(paths) {
			if err := checkSchemaNode(paths[p].node, "$templates."+name+"."+p); err != nil {
				return err
			}
		}
	}
	return nil
}

func checkSchemaNode(n *schemaNode, path string) error {
	// INV-015 — a sealed term must carry both template and path.
	if n.sealed != nil && (!n.sealed.hasTemplate || !n.sealed.hasPath) {
		missing := "template"
		if n.sealed.hasTemplate {
			missing = "path"
		}
		return newError(CodeSealedMissingTemplateOrPath, "INV-015", StageSchemaLoad,
			path+".sealed_from",
			fmt.Sprintf("sealed_from does not declare `%s`; template identity alone is not provenance", missing))
	}

	// INV-010 — a schema must not declare a child named `values` at a
	// structured object position. This is what makes INV-009 total.
	if n.shape == shapeObject {
		if _, ok := n.children["values"]; ok {
			return newError(CodeSchemaReservedChildValues, "INV-010", StageSchemaLoad,
				path+".values",
				"a schema must not declare a child property named `values` at a structured object position; it would collide with the envelope discriminator")
		}
	}

	// INV-005 — the primitive declaration graph must be acyclic.
	for _, name := range n.primOrder {
		next := []string{name}
		if err := checkPrimitiveCycle(n.prims[name], path+"."+name, next); err != nil {
			return err
		}
	}

	for _, c := range n.childOrder {
		if err := checkSchemaNode(n.children[c], path+"."+c); err != nil {
			return err
		}
	}
	if n.item != nil {
		if err := checkSchemaNode(n.item, path+"[]"); err != nil {
			return err
		}
	}
	return nil
}

// checkPrimitiveCycle enforces INV-005.
//
// INV-005 is worded as "a primitive's own primitives MUST NOT, directly or
// transitively, re-declare the node they hang from", but the vector schema
// language is a finite tree with no reference mechanism, so no schema written
// in it can re-declare a node and no materialization written against it can
// fail to terminate. invalid/008_cyclic_primitive_declaration therefore tests
// a different (stronger) property than INV-005 states: acyclicity of the
// primitive-*name* graph. This implementation enforces the property the
// vector requires and records the discrepancy as docs/spec-defects.md SD-005.
func checkPrimitiveCycle(v any, path string, stack []string) error {
	m, ok := asMap(v)
	if !ok {
		return nil
	}
	for _, k := range sortedKeys(m) {
		kp := path + "." + k
		if isPrimitiveName(k) {
			if slices.Contains(stack, k) {
				return newError(CodeCyclicPrimitiveDeclaration, "INV-005", StageSchemaLoad, kp,
					"the primitive declaration graph must be acyclic: a primitive must not directly or transitively re-declare the node it hangs from")
			}
			next := make([]string, len(stack)+1)
			copy(next, stack)
			next[len(stack)] = k
			if err := checkPrimitiveCycle(m[k], kp, next); err != nil {
				return err
			}
			continue
		}
		if err := checkPrimitiveCycle(m[k], kp, stack); err != nil {
			return err
		}
	}
	return nil
}

func sortedTemplateNames(t map[string]map[string]*templateEntry) []string {
	keys := make([]string, 0, len(t))
	for k := range t {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	return keys
}

func sortedTemplatePaths(t map[string]*templateEntry) []string {
	keys := make([]string, 0, len(t))
	for k := range t {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	return keys
}
