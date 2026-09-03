from __future__ import annotations
import ast, json
from pathlib import Path
from typing import Any

def ingest_source_file(filepath: str) -> dict[str, Any]:
    path = Path(filepath)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = []
            for arg in node.args.args:
                args.append(arg.arg)
            functions.append({
                "name": node.name,
                "signature": f"{node.name}({', '.join(args)})",
                "docstring": ast.get_docstring(node) or "",
                "line": node.lineno,
            })
    return {"file": str(path), "functions": functions, "source": source}

def ingest_openapi_spec(filepath: str) -> dict[str, Any]:
    data = json.loads(Path(filepath).read_text(encoding="utf-8-sig"))
    operations = []
    for route, item in data.get("paths", {}).items():
        for method, operation in item.items():
            if method.lower() not in {"get","post","put","patch","delete","options","head","trace"}:
                continue
            operations.append({
                "method": method.upper(),
                "path": route,
                "operation_id": operation.get("operationId"),
                "summary": operation.get("summary", ""),
                "parameters": operation.get("parameters", []),
                "request_body": operation.get("requestBody"),
                "responses": operation.get("responses", {}),
            })
    return {
        "openapi": data.get("openapi"),
        "info": data.get("info", {}),
        "servers": data.get("servers", []),
        "paths": data.get("paths", {}),
        "operations": operations,
        "schemas": data.get("components", {}).get("schemas", {}),
    }
