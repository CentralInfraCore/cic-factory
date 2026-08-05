# oci-invoke-async-result — reachability

Question: does a **production** code path reach `Invoke()` and the new
`work_request_id`-filling branch — not just a test?

## `grep -rn` for `Invoke(` in module/*.go, excluding `_test.go`

```
$ grep -rn "Invoke(auth" module/*.go | grep -v _test.go
module/abi.go:49:		out, derr = Invoke(auth, data)
module/provider.go:647:func Invoke(auth, data []byte) ([]byte, error) {
```

One call site outside the function's own definition: `module/abi.go:49`.

## `module/abi.go:49` is the production WASM guest entrypoint

```
$ head -1 module/abi.go
//go:build wasip1
```

`abi.go` carries the `wasip1` build tag — it is compiled **only** into the
TinyGo/wasip1 target, i.e. `module.wasm` (`make wasm.build`'s output, the
artifact the relay's wazero host loads and calls). It is not part of the host
`go test` build (`provider_test.go` carries `//go:build !wasip1` and calls
`Invoke` directly instead, exercising the same `provider.go` source under the
host build).

```go
// module/abi.go
//export Call
func Call(opPtr, opLen, authPtr, authLen, dataPtr, dataLen uint32) uint64 {
	op := readString(opPtr, opLen)
	auth := readBytes(authPtr, authLen)
	data := readBytes(dataPtr, dataLen)
	...
	case "invoke":
		out, derr = Invoke(auth, data)
	...
}
```

`Call` is the single `//export`ed entrypoint the host (relay's wazero runtime)
invokes across the WASM ABI boundary (docs/design/specs/provider-abi.md). Any
external caller sending the `"invoke"` op string reaches this line, which
reaches `Invoke(auth, data)` at `module/provider.go:647` unconditionally — no
feature flag, no dead branch, no test-only guard around the dispatch.

## `provider.go` has no build tag — same source, both builds

```
$ head -3 module/provider.go
// Package main — provider.go is the cic:provider ABI domain layer
// (docs/design/specs/provider-abi.md). It has no build tag so the same code is
// compiled into the TinyGo/wasip1 guest (dispatched by abi.go) AND exercised by
```

So `Invoke()`'s body — including the new struct field and the new switch —
is the *literal same compiled source* whether reached via `abi.go:49` (guest,
wasip1, production) or via `provider_test.go` (host, `!wasip1`, test). There is
no host/guest divergence to worry about for this change.

## The new field and branch inside `Invoke()`, by line

```
$ grep -n "WorkRequestID" module/provider.go
638:	WorkRequestID string `json:"work_request_id,omitempty"` // set when the op is async (202); poll it
681:		WorkRequestID: headers["opc-work-request-id"],
687:	case res.WorkRequestID != "":
```

- `:638` — the struct field declaration (`operationResult`).
- `:681` — inside `Invoke()`, unconditionally reads the response header into
  the field, for every call that reaches `Invoke` (no branch guards this
  read).
- `:687` — the switch arm that turns a non-empty `WorkRequestID` into
  `status: "accepted"`, reached whenever `status < 400` and the header was
  present — i.e. exactly the real 202 case measured against OCI on
  2026-08-05 (`ChangeInstanceCompartment`, see
  `docs/design/manual-verification.md`).

None of this is reachable only from a test file: the sole non-test call site
(`abi.go:49`) is the production WASM entrypoint, unconditionally dispatched
from the host-facing `Call` export.

## Same check for part B (`Destroy()`'s 404 branch)

```
$ grep -rn "func Destroy\|Destroy(auth" module/*.go | grep -v _test.go
module/abi.go:51:		out, derr = Destroy(auth, data)
module/provider.go:585:func Destroy(auth, data []byte) ([]byte, error) {
```

Same shape: `abi.go:51` (`case "destroy": out, derr = Destroy(auth, data)`) is
the sole production call site, same `wasip1`-tagged `Call` dispatcher, same
untagged shared source for `Destroy()` itself. The 404 branch (now calling
`ociError`) is at `module/provider.go:598-605`, reached whenever `Destroy()`'s
signed DELETE gets a `404` back — unconditional on that status code, no
test-only guard.
