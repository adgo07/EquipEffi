param(
    [string]$PyzPath = "",
    [string]$PythonPath = "python"
)

$ErrorActionPreference = "Stop"

if (-not [string]::IsNullOrWhiteSpace($PyzPath)) {
    $resolved = (Resolve-Path -LiteralPath $PyzPath -ErrorAction Stop).Path
    if ([IO.Path]::GetExtension($resolved).ToLowerInvariant() -ne ".pyz") {
        throw "PyzPath必须指向.pyz文件：$resolved"
    }
    & $PythonPath $resolved --jsonl
    exit $LASTEXITCODE
}

& $PythonPath -m equipeffi --jsonl
exit $LASTEXITCODE
