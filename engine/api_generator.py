from __future__ import annotations
import json
from pathlib import Path
from engine.ingestion import ingest_openapi_spec
from engine.ai import analyze_with_gemini, generate_with_groq

SCENARIOS = [
    ("POSITIVE", "valid request with documented/example values"),
    ("NEGATIVE", "invalid, missing, or unknown resource input"),
    ("EDGE_CASE", "boundary, empty, malformed, or state-transition input"),
]

def _example_for_parameter(p):
    schema = p.get("schema", {})
    examples = p.get("examples", {})
    if examples:
        first = next(iter(examples.values()))
        return first.get("value")
    if "example" in p:
        return p["example"]
    if p.get("name") in {"task_id", "id"}:
        return 1
    if p.get("name") == "username":
        return "testuser"
    typ = schema.get("type")
    return {"integer": 1, "number": 1, "boolean": True}.get(typ, "testuser")

def _request_example(operation):
    params = {p["name"]: _example_for_parameter(p) for p in operation.get("parameters", [])}
    body = operation.get("request_body") or {}
    content = body.get("content", {})
    appjson = content.get("application/json", {})
    schema = appjson.get("schema", {})
    props = schema.get("properties", {})
    payload = {}
    for name, spec in props.items():
        if "example" in spec:
            payload[name] = spec["example"]
        elif spec.get("type") == "boolean":
            payload[name] = True
        elif spec.get("type") == "integer":
            payload[name] = 1
        elif name == "priority":
            payload[name] = "medium"
        elif name == "password":
            payload[name] = "password123"
        elif name == "title":
            payload[name] = "AI generated test task"
        else:
            payload[name] = "testuser"
    return params, payload

def build_postman_collection(openapi_path="openapi.json", out="postman/generated_collection.json"):
    spec = ingest_openapi_spec(openapi_path)
    analysis_context = json.dumps(spec, indent=2)
    gemini_analysis = analyze_with_gemini(analysis_context[:50000])
    groq_analysis = generate_with_groq(analysis_context[:30000])
    items = []
    base = "{{baseUrl}}"
    for op in spec["operations"]:
        if op["path"] == "/":
            continue
        params, payload = _request_example(op)
        path_parts = []
        for segment in op["path"].strip("/").split("/"):
            if segment.startswith("{") and segment.endswith("}"):
                key = segment[1:-1]
                path_parts.append(str(params.get(key, "1" if key.endswith("id") else "testuser")))
            else:
                path_parts.append(segment)
        url = base + "/" + "/".join(path_parts)
        expected = 200
        codes = [int(c) for c in op.get("responses", {}) if str(c).isdigit()]
        if codes:
            expected = 200 if 200 in codes else codes[0]
        test_script = f"""pm.test("Status code is {expected}", function () {{ pm.response.to.have.status({expected}); }});
pm.test("Response is JSON", function () {{ pm.response.to.be.json; }});"""
        request = {"method": op["method"], "header": [{"key":"Content-Type","value":"application/json"}], "url": url}
        if op.get("request_body"):
            request["body"] = {"mode":"raw","raw":json.dumps(payload)}
        items.append({"name": f"{op['method']} {op['path']} [POSITIVE]", "request": request, "event":[{"listen":"test","script":{"exec":test_script.splitlines()}}]})
    collection = {
        "info": {"name":"TestGenIQ AI Generated API Tests","schema":"https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "variable":[{"key":"baseUrl","value":"http://127.0.0.1:8000"}],
        "item": items,
        "_testgeniq": {"scenario_categories":["POSITIVE","NEGATIVE","EDGE_CASE"], "gemini_analysis":gemini_analysis, "groq_generation":groq_analysis}
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(collection, indent=2), encoding="utf-8")
    return out
