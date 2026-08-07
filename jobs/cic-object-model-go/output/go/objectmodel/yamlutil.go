package objectmodel

import (
	"bytes"
	"fmt"
	"sort"

	"gopkg.in/yaml.v3"
)

// orderedMap is a mapping with an explicit key order.
//
// SPEC INV-030 requires a byte-identical canonical object for the same schema
// and input, but SPEC §8.8 never defines the canonical key order (or indent,
// or scalar style). This implementation defines one — node members in the
// order values, origin, then primitives in SPEC §6.1 declaration order;
// payload mappings sorted — and records the gap as docs/spec-defects.md
// SD-010.
type orderedMap struct {
	keys []string
	vals map[string]any
}

func newOrderedMap() *orderedMap {
	return &orderedMap{vals: map[string]any{}}
}

func (m *orderedMap) set(k string, v any) {
	if _, ok := m.vals[k]; !ok {
		m.keys = append(m.keys, k)
	}
	m.vals[k] = v
}

func (m *orderedMap) get(k string) (any, bool) {
	v, ok := m.vals[k]
	return v, ok
}

func (m *orderedMap) has(k string) bool {
	_, ok := m.vals[k]
	return ok
}

// asMap accepts both shapes gopkg.in/yaml.v3 can produce for a mapping.
func asMap(v any) (map[string]any, bool) {
	switch t := v.(type) {
	case map[string]any:
		return t, true
	case map[any]any:
		out := make(map[string]any, len(t))
		for k, vv := range t {
			out[fmt.Sprint(k)] = vv
		}
		return out, true
	}
	return nil, false
}

func sortedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

// normalize converts a plain decoded YAML value into the orderedMap form the
// canonicaliser and the final validator both work on. Mapping keys are
// sorted, which is what makes payload serialization deterministic.
func normalize(v any) any {
	if m, ok := asMap(v); ok {
		om := newOrderedMap()
		for _, k := range sortedKeys(m) {
			om.set(k, normalize(m[k]))
		}
		return om
	}
	if l, ok := v.([]any); ok {
		out := make([]any, len(l))
		for i, e := range l {
			out[i] = normalize(e)
		}
		return out
	}
	return v
}

func toYAMLNode(v any) (*yaml.Node, error) {
	switch t := v.(type) {
	case *orderedMap:
		n := &yaml.Node{Kind: yaml.MappingNode, Tag: "!!map"}
		for _, k := range t.keys {
			kn := &yaml.Node{Kind: yaml.ScalarNode, Tag: "!!str", Value: k}
			vn, err := toYAMLNode(t.vals[k])
			if err != nil {
				return nil, err
			}
			n.Content = append(n.Content, kn, vn)
		}
		return n, nil
	case []any:
		n := &yaml.Node{Kind: yaml.SequenceNode, Tag: "!!seq"}
		for _, e := range t {
			en, err := toYAMLNode(e)
			if err != nil {
				return nil, err
			}
			n.Content = append(n.Content, en)
		}
		return n, nil
	default:
		n := &yaml.Node{}
		if err := n.Encode(v); err != nil {
			return nil, err
		}
		return n, nil
	}
}

// encodeCanonical is the serializer half of SPEC §8.8.
func encodeCanonical(v any) ([]byte, error) {
	root, err := toYAMLNode(v)
	if err != nil {
		return nil, newError(CodeMalformedDocument, "INV-030", StageCanonicalization, "$",
			fmt.Sprintf("canonical serialization failed: %v", err))
	}
	var buf bytes.Buffer
	enc := yaml.NewEncoder(&buf)
	enc.SetIndent(2)
	if err := enc.Encode(root); err != nil {
		return nil, newError(CodeMalformedDocument, "INV-030", StageCanonicalization, "$",
			fmt.Sprintf("canonical serialization failed: %v", err))
	}
	if err := enc.Close(); err != nil {
		return nil, newError(CodeMalformedDocument, "INV-030", StageCanonicalization, "$",
			fmt.Sprintf("canonical serialization failed: %v", err))
	}
	return buf.Bytes(), nil
}

// deepCopy protects an opaque payload (SPEC INV-028: preserved verbatim) from
// aliasing the caller's input tree.
func deepCopy(v any) any {
	if m, ok := asMap(v); ok {
		out := make(map[string]any, len(m))
		for k, vv := range m {
			out[k] = deepCopy(vv)
		}
		return out
	}
	if l, ok := v.([]any); ok {
		out := make([]any, len(l))
		for i, e := range l {
			out[i] = deepCopy(e)
		}
		return out
	}
	return v
}
