from __future__ import annotations

import html
import json
from pathlib import Path

from engine.ai import explain_failure_with_gemini


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def _read_log(path: str | None) -> str:
    if not path:
        return ""

    log_path = Path(path)

    if not log_path.is_absolute():
        log_path = ROOT / log_path

    if not log_path.exists():
        return ""

    return log_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def _status(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _status_class(passed: bool) -> str:
    return "pass" if passed else "fail"


def _safe_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def build_report(
    results,
    output="artifacts/test-report.html",
):
    output_path = ROOT / output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total = len(results)
    passed = sum(
        1 for data in results.values()
        if data.get("passed")
    )
    failed = total - passed

    pass_percent = round(
        (passed / total) * 100,
        1
    ) if total else 0

    # ---------------------------------------------------------
    # AI RCA
    # ---------------------------------------------------------
    rcas = []

    for name, data in results.items():
        if data.get("passed"):
            continue

        log_text = _read_log(data.get("log"))

        evidence = (
            f"Tool: {name}\n"
            f"Return code: {data.get('return_code')}\n"
            f"Command: {' '.join(data.get('command', []))}\n\n"
            f"Recorded output:\n{log_text[-12000:]}"
        )

        try:
            explanation = explain_failure_with_gemini(evidence)
        except Exception as exc:
            explanation = (
                "AI RCA unavailable for this failure. "
                f"Error: {exc}"
            )

        rcas.append(
            {
                "tool": name,
                "return_code": data.get("return_code"),
                "explanation": explanation,
                "log": data.get("log"),
            }
        )

    # ---------------------------------------------------------
    # Save RCA JSON
    # ---------------------------------------------------------
    rca_payload = {
        "summary": {
            "total_tools": total,
            "passed_tools": passed,
            "failed_tools": failed,
        },
        "rca": rcas,
    }

    (ARTIFACTS / "rca.json").write_text(
        _safe_json(rca_payload),
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # Tool rows
    # ---------------------------------------------------------
    tool_rows = []

    for name, data in results.items():
        is_passed = bool(data.get("passed"))

        log_name = ""
        if data.get("log"):
            log_name = Path(data["log"]).name

        tool_rows.append(
            f"""
            <tr>
                <td><strong>{html.escape(name.title())}</strong></td>
                <td>
                    <span class="badge {_status_class(is_passed)}">
                        {_status(is_passed)}
                    </span>
                </td>
                <td>{html.escape(str(data.get("return_code")))}</td>
                <td>
                    <span class="availability">
                        {"Available" if data.get("available") else "Unavailable"}
                    </span>
                </td>
                <td>
                    {f'<a href="{html.escape(log_name)}">View log</a>' if log_name else "-"}
                </td>
            </tr>
            """
        )

    # ---------------------------------------------------------
    # RCA sections
    # ---------------------------------------------------------
    rca_sections = []

    if not rcas:
        rca_sections.append(
            """
            <div class="success-box">
                <strong>All test engines passed.</strong>
                No failure RCA was required.
            </div>
            """
        )

    for item in rcas:
        tool = html.escape(str(item["tool"]).title())
        explanation = html.escape(
            str(item["explanation"])
        )

        log_name = ""
        if item.get("log"):
            log_name = Path(item["log"]).name

        rca_sections.append(
            f"""
            <div class="rca-card">
                <div class="rca-header">
                    <h3>{tool}</h3>
                    <span class="badge fail">FAIL</span>
                </div>

                <div class="rca-content">
                    <h4>AI Failure Analysis</h4>
                    <pre>{explanation}</pre>
                </div>

                <div class="rca-footer">
                    Return code:
                    <strong>{html.escape(str(item["return_code"]))}</strong>
                    &nbsp;&nbsp;
                    {f'<a href="{html.escape(log_name)}">Open raw log</a>' if log_name else ""}
                </div>
            </div>
            """
        )

    # ---------------------------------------------------------
    # HTML report
    # ---------------------------------------------------------
    doc = f"""
<!DOCTYPE html>
<html lang="en">

<head>
<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>TestGenIQ - API Test Intelligence Report</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #f4f7fb;
    color: #172033;
    font-family:
        Inter,
        Segoe UI,
        Arial,
        sans-serif;
}}

.container {{
    max-width: 1250px;
    margin: 0 auto;
    padding: 32px;
}}

.hero {{
    background: #111827;
    color: white;
    border-radius: 18px;
    padding: 34px;
    margin-bottom: 24px;
}}

.hero h1 {{
    margin: 0 0 8px;
    font-size: 32px;
}}

.hero p {{
    margin: 0;
    opacity: .75;
}}

.grid {{
    display: grid;
    grid-template-columns:
        repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}}

.card {{
    background: white;
    border-radius: 14px;
    padding: 22px;
    box-shadow:
        0 2px 10px rgba(15, 23, 42, .06);
}}

.metric {{
    font-size: 32px;
    font-weight: 700;
    margin-top: 8px;
}}

.label {{
    color: #64748b;
    font-size: 14px;
}}

.section {{
    background: white;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow:
        0 2px 10px rgba(15, 23, 42, .06);
}}

.section h2 {{
    margin-top: 0;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    text-align: left;
    background: #f8fafc;
    color: #475569;
}}

th, td {{
    padding: 14px;
    border-bottom: 1px solid #e2e8f0;
}}

.badge {{
    display: inline-block;
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}}

.badge.pass {{
    background: #dcfce7;
    color: #166534;
}}

.badge.fail {{
    background: #fee2e2;
    color: #991b1b;
}}

.availability {{
    color: #475569;
}}

a {{
    color: #2563eb;
    text-decoration: none;
    font-weight: 600;
}}

a:hover {{
    text-decoration: underline;
}}

.progress {{
    height: 12px;
    background: #e2e8f0;
    border-radius: 20px;
    overflow: hidden;
    margin-top: 15px;
}}

.progress-bar {{
    height: 100%;
    width: {pass_percent}%;
    background: #22c55e;
}}

.success-box {{
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
    padding: 18px;
    border-radius: 12px;
}}

.rca-card {{
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    margin-bottom: 18px;
    overflow: hidden;
}}

.rca-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px;
    background: #f8fafc;
}}

.rca-header h3 {{
    margin: 0;
}}

.rca-content {{
    padding: 20px;
}}

.rca-content h4 {{
    margin-top: 0;
}}

pre {{
    white-space: pre-wrap;
    word-wrap: break-word;
    background: #0f172a;
    color: #e2e8f0;
    padding: 18px;
    border-radius: 10px;
    line-height: 1.55;
    font-size: 13px;
}}

.rca-footer {{
    padding: 14px 20px;
    border-top: 1px solid #e2e8f0;
    color: #64748b;
    font-size: 13px;
}}

.footer {{
    text-align: center;
    color: #64748b;
    padding: 20px;
    font-size: 13px;
}}

@media(max-width: 850px) {{
    .grid {{
        grid-template-columns: repeat(2, 1fr);
    }}
}}

@media(max-width: 550px) {{
    .container {{
        padding: 16px;
    }}

    .grid {{
        grid-template-columns: 1fr;
    }}
}}

</style>
</head>

<body>

<div class="container">

    <div class="hero">
        <h1>TestGenIQ</h1>
        <p>
            AI-Powered API Test Generation,
            Contract Validation & Failure Intelligence
        </p>
    </div>

    <div class="grid">

        <div class="card">
            <div class="label">Test Engines</div>
            <div class="metric">{total}</div>
        </div>

        <div class="card">
            <div class="label">Passed</div>
            <div class="metric">{passed}</div>
        </div>

        <div class="card">
            <div class="label">Failed</div>
            <div class="metric">{failed}</div>
        </div>

        <div class="card">
            <div class="label">Pass Rate</div>
            <div class="metric">{pass_percent}%</div>

            <div class="progress">
                <div class="progress-bar"></div>
            </div>
        </div>

    </div>

    <div class="section">

        <h2>Execution Summary</h2>

        <table>

            <thead>
                <tr>
                    <th>Engine</th>
                    <th>Status</th>
                    <th>Exit Code</th>
                    <th>Availability</th>
                    <th>Evidence</th>
                </tr>
            </thead>

            <tbody>
                {"".join(tool_rows)}
            </tbody>

        </table>

    </div>

    <div class="section">

        <h2>AI Failure Intelligence</h2>

        <p>
            TestGenIQ analyzes failed execution evidence and
            generates an evidence-based root-cause explanation
            without modifying or suppressing the underlying
            test result.
        </p>

        {"".join(rca_sections)}

    </div>

    <div class="section">

        <h2>Pipeline Architecture</h2>

        <p>
            OpenAPI Specification
            &rarr;
            AI Scenario Analysis
            &rarr;
            API Test Generation
            &rarr;
            Pytest / Schemathesis / Dredd / Newman
            &rarr;
            Result Aggregation
            &rarr;
            AI RCA
            &rarr;
            Unified Report
        </p>

    </div>

    <div class="footer">
        Generated by TestGenIQ automated API testing pipeline
    </div>

</div>

</body>
</html>
"""

    output_path.write_text(
        doc,
        encoding="utf-8",
    )

    return str(output_path)