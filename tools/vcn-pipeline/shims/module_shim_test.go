//go:build !wasip1

package main

import (
	"encoding/json"
	"fmt"
	"os"
	"testing"
)

// Stage 3 entry point for ONE read outcome. This file is copied into a scratch copy of the module by tools/vcn-pipeline; the
// module checkout itself is never modified.
func TestPipelineShim(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("PIPELINE_SHIM_IN"))
	if err != nil {
		t.Fatal(err)
	}
	var in struct {
		Status    int    `json:"status"`
		Body      string `json:"body"`
		Transport string `json:"transport"`
	}
	if err := json.Unmarshal(raw, &in); err != nil {
		t.Fatal(err)
	}
	got, ok := normalizeObserved("cic:network:vcn", getOutcome{Status: in.Status, Body: []byte(in.Body), Transport: in.Transport})
	if !ok {
		t.Fatal("no contract for the VCN kind")
	}
	out, err := json.Marshal(got)
	if err != nil {
		t.Fatal(err)
	}
	fmt.Printf("PIPELINE_SHIM_OUT %s\n", out)
}
