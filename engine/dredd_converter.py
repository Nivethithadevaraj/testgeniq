from __future__ import annotations
import copy, json
from pathlib import Path

def _schema(s):
    if not s: return {}
    if "$ref" in s: return {"$ref": "#/definitions/" + s["$ref"].split("/")[-1]}
    out = {k:s[k] for k in ("type","format","description","required","enum","default","minimum","maximum","minLength","maxLength") if k in s}
    if "properties" in s: out["properties"] = {k:_schema(v) for k,v in s["properties"].items()}
    if "items" in s: out["items"] = _schema(s["items"])
    return out

def convert_oas3_to_oas2(src, dst):
    data = json.loads(Path(src).read_text(encoding="utf-8-sig"))
    out = {"swagger":"2.0","info":data.get("info",{}),"host":"127.0.0.1:8000","basePath":"/","schemes":["http"],"paths":{},"definitions":{}}
    for name, schema in data.get("components",{}).get("schemas",{}).items():
        out["definitions"][name] = _schema(schema)
    for path, path_item in data.get("paths",{}).items():
        out["paths"][path] = {}
        for method, op in path_item.items():
            if method.lower() not in {"get","post","put","patch","delete","options","head"}: continue
            newop = {k:op[k] for k in ("summary","description","operationId") if k in op}
            params=[]
            for p in op.get("parameters",[]):
                q = {"name":p["name"],"in":p["in"],"required":p.get("required",False),"type":p.get("schema",{}).get("type","string")}
                if "example" in p: q["x-example"] = p["example"]
                if p.get("examples"):
                    q["x-example"] = next(iter(p["examples"].values())).get("value")
                params.append(q)
            rb = op.get("requestBody",{}).get("content",{}).get("application/json",{})
            if rb:
                params.append({"name":"body","in":"body","required":True,"schema":_schema(rb.get("schema",{}))})
            if params: newop["parameters"]=params
            responses={}
            for code, resp in op.get("responses",{}).items():
                r={"description":resp.get("description","")}
                content=resp.get("content",{}).get("application/json",{})
                if content.get("schema"): r["schema"]=_schema(content["schema"])
                responses[code]=r
            newop["responses"]=responses
            out["paths"][path][method]=newop
    Path(dst).write_text(json.dumps(out,indent=2),encoding="utf-8")
    return dst
