from __future__ import annotations

import json

from generate_tests import main as generate_pytest_tests

from engine.api_generator import (
    generate_postman_collection,
)
from engine.contract_runner import (
    run_all_contract_tests,
)
from engine.reporting import (
    build_report,
)


def main():

    print("=" * 60)
    print(
        "TestGenIQ - End-to-End API Test Pipeline"
    )
    print("=" * 60)

    print()
    print(
        "[1/4] Generating pytest tests "
        "(Gemini + Groq with validated fallback)..."
    )

    generate_pytest_tests()

    print()
    print(
        "[2/4] Generating Postman collection "
        "with positive, negative and edge cases..."
    )

    collection_path = (
        generate_postman_collection()
    )

    print(
        f"Generated collection: {collection_path}"
    )

    print()
    print(
        "[3/4] Running Pytest + Schemathesis + "
        "Dredd + Newman + Playwright..."
    )

    results = (
        run_all_contract_tests()
    )

    print()
    print(
        "[4/4] Building unified report..."
    )

    report_path = build_report(
        results
    )

    summary = {
        "total_tools": len(results),

        "passed_tools": sum(
            1
            for result in results.values()
            if result.get("passed")
        ),

        "failed_tools": sum(
            1
            for result in results.values()
            if result.get(
                "available",
                True,
            )
            and not result.get("passed")
        ),
    }

    print()
    print("PIPELINE COMPLETE")

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    print(
        f"HTML report: {report_path}"
    )


if __name__ == "__main__":
    main()