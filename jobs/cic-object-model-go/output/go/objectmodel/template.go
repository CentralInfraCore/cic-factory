package objectmodel

import "fmt"

const maxTemplateDepth = 64

// effNode is the effective schema at a position after SPEC §8.3: every
// sealed_from has been replaced by the template's own schema, and every node
// at or below a sealed boundary carries the (template, path) pair its origins
// need (INV-015).
type effNode struct {
	sch        *schemaNode
	sealed     *sealedCtx
	content    any
	hasContent bool
	children   map[string]*effNode
	childOrder []string
	item       *effNode
}

// buildEffective is SPEC §8.3.
//
//	INPUT:  resolved authoring tree
//	OUTPUT: tree with no unexpanded template references
//	MUST:   record template identity and source path in the origin of every
//	        node produced (INV-015)
//
// Note what the vectors require here that SPEC §8.3 does not state: a node
// declared with `sealed_from` and nothing else has no shape of its own, yet
// materialization/003 and /004 expect `shape: {values: {type: object}}` on
// it. The shape — and the children, and their defaults — come from the
// template node at the referenced path. Recorded as docs/spec-defects.md SD-006.
func buildEffective(s *Schema) (*effNode, error) {
	return buildEff(s, s.root, nil, nil, false, "$", 0)
}

func buildEff(s *Schema, sch *schemaNode, sealed *sealedCtx, content any, hasContent bool, path string, depth int) (*effNode, error) {
	if depth > maxTemplateDepth {
		return nil, newError(CodeTemplateNotFound, "INV-005", StageSealedExpansion, path,
			"template expansion exceeded the maximum depth")
	}

	if sch.sealed != nil {
		paths, ok := s.templates[sch.sealed.template]
		if !ok {
			return nil, newError(CodeTemplateNotFound, "INV-015", StageSealedExpansion, path,
				fmt.Sprintf("template %s is not declared", sch.sealed.template))
		}
		entry, ok := paths[sch.sealed.path]
		if !ok {
			return nil, newError(CodeTemplateNotFound, "INV-015", StageSealedExpansion, path,
				fmt.Sprintf("template %s declares no path %s", sch.sealed.template, sch.sealed.path))
		}
		ctx := &sealedCtx{template: sch.sealed.template, path: sch.sealed.path}
		return buildEff(s, entry.node, ctx, entry.content, entry.hasContent, path, depth+1)
	}

	e := &effNode{
		sch:        sch,
		sealed:     sealed,
		content:    content,
		hasContent: hasContent,
		children:   map[string]*effNode{},
	}

	switch sch.shape {
	case shapeObject:
		for _, c := range sch.childOrder {
			child, err := buildEff(s, sch.children[c], sealed, nil, false, path+"."+c, depth+1)
			if err != nil {
				return nil, err
			}
			e.children[c] = child
			e.childOrder = append(e.childOrder, c)
		}
	case shapeList:
		if sch.item != nil {
			item, err := buildEff(s, sch.item, sealed, nil, false, path+"[]", depth+1)
			if err != nil {
				return nil, err
			}
			e.item = item
		}
	}
	return e, nil
}
