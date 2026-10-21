
// Appended by tools/vcn-pipeline to a scratch COPY of engine/tests/differential.rs (the engine checkout is never modified):
// stage 5 entry point for ONE input.json, through the library's own `evaluate_verdict`, using the harness's own object builders.
#[test]
fn pipeline_shim() {
    let path = std::env::var("PIPELINE_SHIM_IN").expect("PIPELINE_SHIM_IN");
    let bytes = fs::read(&path).expect("input");
    let input = reader::parse(&bytes, Stage::Read, "$", "input.json").expect("input parses");
    let intent = map_get(&input, "intent").unwrap_or(&Value::Null);
    let observed = map_get(&input, "observed").unwrap_or(&Value::Null);
    let obs = build_observation(&input);
    let plan = build_plan(&input);
    let got = evaluate_verdict(
        &intent_object(intent),
        &observed_object(observed, &obs),
        &obs,
        &plan,
    )
    .expect("evaluate_verdict");
    let bytes = verdict_canonical_bytes(&got).expect("canonical");
    println!("PIPELINE_SHIM_OUT {}", String::from_utf8_lossy(&bytes));
}
