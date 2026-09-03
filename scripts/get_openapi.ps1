$ErrorActionPreference = "Stop"

$url = "http://127.0.0.1:8000/openapi.json"
$output = "openapi.json"

Write-Host "Fetching OpenAPI specification..."

$response = Invoke-RestMethod $url

$json = $response | ConvertTo-Json -Depth 100

# Write UTF-8 WITHOUT BOM so Schemathesis can parse it.
[System.IO.File]::WriteAllText(
    (Join-Path (Get-Location) $output),
    $json,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "OpenAPI specification written to $output"
Write-Host "Encoding: UTF-8 without BOM"