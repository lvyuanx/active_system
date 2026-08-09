param(
    [ValidateSet("admin", "screen", "user", "all")]
    [string]$Target = "all",
    [string]$OpenApiUrl = "http://127.0.0.1:8000/openapi.json"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$targets = @{
    admin = "apps/admin-web/src/api/generated/schema.d.ts"
    screen = "apps/screen-web/src/api/generated/schema.d.ts"
    user = "apps/user-web/src/api/generated/schema.d.ts"
}

$selectedTargets = if ($Target -eq "all") { $targets.Keys } else { @($Target) }

foreach ($name in $selectedTargets) {
    $outputPath = Join-Path $projectRoot $targets[$name]
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outputPath) | Out-Null
    pnpm exec openapi-typescript $OpenApiUrl --output $outputPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to generate API types for $name."
    }
}

