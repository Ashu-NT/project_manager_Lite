param(
    [ValidateSet("up", "test", "down")]
    [string]$Action = "test",
    [switch]$KeepContainer
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root "src/tests/integration/postgresql/compose.yml"

if ($Action -eq "up") {
    docker compose -f $compose up -d --wait
    exit $LASTEXITCODE
}

if ($Action -eq "down") {
    docker compose -f $compose down -v --remove-orphans
    exit $LASTEXITCODE
}

try {
    docker compose -f $compose up -d --wait
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $env:PM_RUN_POSTGRES_INTEGRATION = "1"
    $conda = Get-Command conda -ErrorAction SilentlyContinue
    if ($null -eq $conda) {
        $condaPath = Join-Path $env:USERPROFILE "miniconda3/Scripts/conda.exe"
        if (-not (Test-Path $condaPath)) {
            throw "Conda was not found; the R5H.1 suite requires the existing pmenv environment."
        }
        $conda = $condaPath
    }
    & $conda run -n pmenv python -m pytest `
        src/tests/integration/postgresql `
        -m postgresql_integration -q
    exit $LASTEXITCODE
}
finally {
    if (-not $KeepContainer) {
        docker compose -f $compose down -v --remove-orphans
    }
}
