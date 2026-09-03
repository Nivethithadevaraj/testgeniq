from __future__ import annotations
import html, json
from pathlib import Path
from engine.ai import explain_failure_with_gemini

def build_report(results, output="artifacts/test-report.html"):
    failures=[]
    for name, data in results.items():
        if not data.get("passed"):
            log=Path(data.get("log", f"artifacts/{name}.log"))
            text=log.read_text(encoding="utf-8",errors="replace") if log.exists() else ""
            failures.append((name,text[-8000:]))
    rcas=[]
    for name,text in failures:
        rcas.append({"tool":name,"explanation":explain_failure_with_gemini(text)})
    payload={"results":results,"rca":rcas}
    Path("artifacts/rca.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
    rows=[]
    for name,d in results.items():
        rows.append(f"<tr><td>{html.escape(name)}</td><td>{'PASS' if d.get('passed') else 'FAIL'}</td><td>{d.get('return_code')}</td></tr>")
    rca_html="".join(f"<h3>{html.escape(x['tool'])}</h3><pre>{html.escape(x['explanation'])}</pre>" for x in rcas) or "<p>No failures.</p>"
    doc=f"""<!doctype html><html><head><meta charset='utf-8'><title>TestGenIQ Report</title>
    <style>body{{font-family:Arial;margin:40px}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:8px}}pre{{white-space:pre-wrap}}</style></head>
    <body><h1>TestGenIQ Unified API Test Report</h1><table><tr><th>Engine</th><th>Status</th><th>Exit</th></tr>{''.join(rows)}</table>
    <h2>AI Failure Analysis</h2>{rca_html}</body></html>"""
    Path(output).write_text(doc,encoding="utf-8")
    return output
