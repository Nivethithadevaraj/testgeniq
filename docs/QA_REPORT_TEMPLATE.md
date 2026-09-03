# TestGenIQ QA Report

## 1. Scope
Engine QA + generated-test correctness + contract validation + CI reliability.

## 2. Test results
Record pytest count, pass/fail, duration and coverage.

## 3. Generated-test audit
Record:
- syntax validity
- positive/negative/edge distribution
- meaningful assertions
- no vacuous assertions
- source/contract traceability

## 4. Contract validation
Record Schemathesis and Dredd results and any real contract defects.

## 5. AI RCA validation
Document at least three intentionally created failures:
1. wrong expected status
2. invalid response schema
3. missing resource/path parameter

For each: actual cause, AI explanation, human verification.

## 6. CI/CD
Attach green GitHub Actions run and artifact links.

## 7. Coverage
Baseline vs generated coverage with measurable delta.

## 8. Evidence
Screenshots and links uploaded to Moodle.
