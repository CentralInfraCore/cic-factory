# Claim Evidence

| Állítás | Státusz | Bizonyíték | Verifikációs módszer | Kockázat |
|---|---|---|---|---|
| VerifyProofArtifact meghívható HTTP handler-ből | true | `cmd/relay/proof_verify_handler.go:56` — `result := VerifyProofArtifact(req.ProofArtifact)` | kód olvasva + tesztek futottak | kritikus |
| /v1/proof/verify route regisztrálva | true | `cmd/relay/main.go:190` — `mux.HandleFunc("/v1/proof/verify", s.proofVerifyHandler)` | kód olvasva + grep megerősítve | kritikus |
| handler tesztek zöldek | true | exit code 0, `ok centralrelay/cmd/relay 1.222s`, 7 handler teszt PASS | `make test-go` futtatva | kritikus |
| változások commitolva | true | `af77c2a feat(api): POST /v1/proof/verify — chain hash verification endpoint` | git log | alacsony |
