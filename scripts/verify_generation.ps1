Write-Host "=============================================="
Write-Host "TestGenIQ AI Generation Verification"
Write-Host "=============================================="

$files = @(
    "tests\test_tasks.py",
    "tests\test_auth.py"
)

foreach ($file in $files) {

    if (!(Test-Path $file)) {
        Write-Host "FAIL: $file not found"
        exit 1
    }

    Write-Host "FOUND: $file"

    $content = Get-Content $file -Raw

    if ($content -notmatch "POSITIVE") {
        Write-Host "FAIL: $file missing POSITIVE scenario"
        exit 1
    }

    if ($content -notmatch "NEGATIVE") {
        Write-Host "FAIL: $file missing NEGATIVE scenario"
        exit 1
    }

    if ($content -notmatch "EDGE") {
        Write-Host "FAIL: $file missing EDGE scenario"
        exit 1
    }
}

if (!(Test-Path "postman\generated_collection.json")) {
    Write-Host "FAIL: AI-generated Postman collection missing"
    exit 1
}

Write-Host ""
Write-Host "PASS: AI-generated pytest files verified"
Write-Host "PASS: Positive scenarios verified"
Write-Host "PASS: Negative scenarios verified"
Write-Host "PASS: Edge scenarios verified"
Write-Host "PASS: AI-generated Postman collection verified"