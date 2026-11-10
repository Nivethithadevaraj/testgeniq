from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from engine.ai import (
    RCA_SOURCE_GEMINI,
    classify_failure,
    explain_failure_with_source,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def _status_label(result: dict) -> str:
    if not result.get("available", True):
        return "UNAVAILABLE"

    return (
        "PASS"
        if result.get("passed")
        else "FAIL"
    )


def _evidence(result: dict) -> str:
    stdout = result.get("stdout") or ""
    stderr = result.get("stderr") or ""

    return (
        stdout + "\n" + stderr
    ).strip()


def _source_label(rca: dict) -> tuple[str, str]:
    """
    Human-readable label and CSS class for where an RCA came from.
    """

    if rca.get("source") == RCA_SOURCE_GEMINI:
        model = rca.get("model") or "Gemini"
        return (
            f"AI-generated (Gemini: {model})",
            "source-ai",
        )

    reason = rca.get("reason") or "AI unavailable"

    return (
        f"Rule-based fallback ({reason})",
        "source-fallback",
    )


def build_report(
    results: dict,
    output_path: str | Path | None = None,
) -> Path:
    """
    Build the unified TestGenIQ HTML execution report.
    """

    if output_path is None:
        output_path = (
            ARTIFACTS
            / "test-report.html"
        )

    output_path = Path(output_path)

    passed = sum(
        1
        for result in results.values()
        if result.get("passed")
    )

    failed = sum(
        1
        for result in results.values()
        if result.get("available", True)
        and not result.get("passed")
    )

    total = len(results)

    pass_rate = (
        (passed / total) * 100
        if total
        else 0
    )

    rows = []

    rca_blocks = []

    ai_rca_count = 0

    for tool_name, result in results.items():

        status = _status_label(
            result
        )

        evidence = _evidence(
            result
        )

        rows.append(
            f"""
            <tr>
                <td>{html.escape(tool_name.title())}</td>
                <td>{html.escape(status)}</td>
                <td>{result.get("return_code")}</td>
                <td>{html.escape(str(result.get("log") or "N/A"))}</td>
            </tr>
            """
        )

        if (
            result.get("available", True)
            and not result.get("passed")
        ):

            category = classify_failure(
                evidence
            )

            try:
                rca = explain_failure_with_source(
                    evidence[-6000:]
                )
            except Exception as exc:
                rca = {
                    "text": (
                        "Failure analysis unavailable: "
                        f"{type(exc).__name__}"
                    ),
                    "source": "unavailable",
                    "reason": "analysis error",
                }

            ai_rca_count += (
                1
                if rca.get("source") == RCA_SOURCE_GEMINI
                else 0
            )

            source_text, source_class = _source_label(
                rca
            )

            rca_blocks.append(
                f"""
                <section class="rca">
                    <h3>{html.escape(tool_name.title())}</h3>
                    <p>
                        <strong>Classification:</strong>
                        {html.escape(category)}
                    </p>
                    <p>
                        <strong>Explanation source:</strong>
                        <span class="badge {source_class}">{html.escape(source_text)}</span>
                    </p>
                    <pre>{html.escape(str(rca.get("text", "")))}</pre>
                </section>
                """
            )

    manifest_html = ""

    manifest_path = (
        ARTIFACTS
        / "generation-manifest.json"
    )

    if manifest_path.exists():

        try:
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            manifest_html = (
                "<h2>Generation Manifest</h2>"
                f"<pre>{html.escape(json.dumps(manifest, indent=2))}</pre>"
            )

        except Exception:
            manifest_html = ""

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TestGenIQ Unified Test Report</title>

<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    background: #f7f7f7;
    color: #222;
}}

h1 {{
    margin-bottom: 4px;
}}

.subtitle {{
    color: #666;
}}

.cards {{
    display: flex;
    gap: 16px;
    margin: 24px 0;
}}

.card {{
    background: white;
    padding: 18px;
    border-radius: 8px;
    min-width: 150px;
    box-shadow: 0 1px 4px rgba(0,0,0,.12);
}}

.value {{
    font-size: 28px;
    font-weight: bold;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
}}

th, td {{
    border: 1px solid #ddd;
    padding: 10px;
    text-align: left;
}}

th {{
    background: #eee;
}}

.rca {{
    background: white;
    margin: 18px 0;
    padding: 18px;
    border-radius: 8px;
}}

.badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: bold;
}}

.source-ai {{
    background: #e3f4e8;
    color: #1d6b34;
}}

.source-fallback {{
    background: #fdf0d9;
    color: #8a5300;
}}

pre {{
    white-space: pre-wrap;
    word-break: break-word;
    background: #111;
    color: #eee;
    padding: 14px;
    border-radius: 6px;
}}
</style>
</head>

<body>

<h1>TestGenIQ Unified Test Report</h1>

<div class="subtitle">
Generated:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
</div>

<div class="cards">

<div class="card">
<div>Test Engines</div>
<div class="value">{total}</div>
</div>

<div class="card">
<div>Passed</div>
<div class="value">{passed}</div>
</div>

<div class="card">
<div>Failed</div>
<div class="value">{failed}</div>
</div>

<div class="card">
<div>Pass Rate</div>
<div class="value">{pass_rate:.1f}%</div>
</div>

</div>

<h2>Execution Summary</h2>

<table>
<thead>
<tr>
<th>Engine</th>
<th>Status</th>
<th>Return Code</th>
<th>Evidence Log</th>
</tr>
</thead>

<tbody>
{''.join(rows)}
</tbody>
</table>

<h2>AI Failure Intelligence</h2>

{f'<p>{ai_rca_count} of {len(rca_blocks)} failure explanations generated by Gemini; the rest used the rule-based fallback.</p>' if rca_blocks else ''}

{''.join(rca_blocks) if rca_blocks else '<p>No failed engines requiring RCA.</p>'}

{manifest_html}

</body>
</html>
"""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        document,
        encoding="utf-8",
    )

    return output_path


# Backward compatibility for any previous imports.
def generate_report(
    results: dict,
    output_path: str | Path | None = None,
):
    return build_report(
        results,
        output_path,
    )


def generate_html_report(
    results: dict,
    output_path: str | Path | None = None,
):
    return build_report(
        results,
        output_path,
    )