package objectmodel

// OriginKind is one of the three terms of the origin grammar (SPEC §5.2,
// INV-013).
type OriginKind string

const (
	// OriginYAML — the instance YAML explicitly supplied this value.
	OriginYAML OriginKind = "yaml"
	// OriginSchema — the value materialized from this node's schema default.
	OriginSchema OriginKind = "schema"
	// OriginSealed — the node came from a closed template at a path.
	OriginSealed OriginKind = "sealed"
)

// OriginTerm is a single term of an origin. Template and Path are set only
// for OriginSealed, and INV-015 requires both.
type OriginTerm struct {
	Kind     OriginKind
	Template string
	Path     string
}

// Origin classifies authoring authority (SPEC §5). It is a classification,
// not a history (INV-014): it never accumulates lifecycle events.
type Origin []OriginTerm

// sealedCtx is the (template, path) pair a sealed boundary contributes to
// every origin below it (INV-015).
type sealedCtx struct {
	template string
	path     string
}

func originYAML() Origin   { return Origin{{Kind: OriginYAML}} }
func originSchema() Origin { return Origin{{Kind: OriginSchema}} }

func originSealed(s *sealedCtx) Origin {
	return Origin{{Kind: OriginSealed, Template: s.template, Path: s.path}}
}

// originSealedSchema is truth-table row 4 (SPEC §5.3): the template defined
// and closed the node, and the value came from the template node's own schema
// default. The two terms describe different dimensions, which is why they
// combine where yaml and schema do not (INV-017).
func originSealedSchema(s *sealedCtx) Origin {
	return Origin{{Kind: OriginSealed, Template: s.template, Path: s.path}, {Kind: OriginSchema}}
}

func (o Origin) project() any {
	out := make([]any, 0, len(o))
	for _, t := range o {
		if t.Kind == OriginSealed {
			inner := newOrderedMap()
			inner.set("template", t.Template)
			inner.set("path", t.Path)
			term := newOrderedMap()
			term.set("sealed", inner)
			out = append(out, term)
			continue
		}
		out = append(out, string(t.Kind))
	}
	return out
}
