package main

import (
	"encoding/json"
	"fmt"
	"os"
	"testing"
)

// Stage 6 entry point for ONE case, from the stage outputs the pipeline hands over. Copied into cmd/relay of a scratch copy of the
// Relay by tools/vcn-pipeline; the Relay checkout itself is never modified. It uses the test-side evidence builder of the Relay
// (vcnEvidenceFrom) and the Relay's own VerifyProofArtifact.
func TestPipelineShim(t *testing.T) {
	raw, err := os.ReadFile(os.Getenv("PIPELINE_SHIM_IN"))
	if err != nil {
		t.Fatal(err)
	}
	var in struct {
		Case    string                 `json:"case"`
		Raw     interface{}            `json:"raw"`
		Intent  interface{}            `json:"intent"`
		ObsOCI  interface{}            `json:"observed_oci"`
		ObsReg  map[string]interface{} `json:"observed_registry"`
		Verdict map[string]interface{} `json:"verdict"`
	}
	if err := json.Unmarshal(raw, &in); err != nil {
		t.Fatal(err)
	}
	art, sc, err := vcnEvidenceFrom(t, in.Case, in.Raw, in.Intent, in.ObsOCI, in.ObsReg, in.Verdict)
	out := map[string]interface{}{}
	if err != nil {
		out["error"] = err.Error()
	} else {
		out["artifact"] = art
		out["claims"] = sc
		out["sidecar_bound"] = vcnSidecarBound(t, art, sc)
		out["verify"] = VerifyProofArtifact(art)
	}
	b, _ := json.Marshal(out)
	fmt.Printf("PIPELINE_SHIM_OUT %s\n", b)
}
