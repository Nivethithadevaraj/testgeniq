from pathlib import Path
import json
from engine.api_generator import build_postman_collection
from engine.contract_runner import run_all_contract_tests
from engine.reporting import build_report

def main():
    print("="*60)
    print("TestGenIQ - End-to-End API Test Pipeline")
    print("="*60)
    Path("artifacts").mkdir(exist_ok=True)
    print("\n[1/3] Generating API test collection...")
    build_postman_collection()
    print("[2/3] Running pytest + Schemathesis + Dredd + Newman...")
    results=run_all_contract_tests()
    print("[3/3] Building unified report...")
    build_report(results)
    passed=sum(1 for x in results.values() if x["passed"])
    print("\nPIPELINE COMPLETE")
    print(json.dumps({"total_tools":len(results),"passed_tools":passed,"failed_tools":len(results)-passed},indent=2))
    print("HTML report: artifacts/test-report.html")

if __name__=="__main__":
    main()
