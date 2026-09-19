param(
    [string]$PythonPath = "python",
    [string]$Host = "127.0.0.1",
    [int]$Port = 8765,
    [string]$PyzPath = "",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"

$arguments = @()
if (-not [string]::IsNullOrWhiteSpace($PyzPath)) {
    $resolved = (Resolve-Path -LiteralPath $PyzPath -ErrorAction Stop).Path
    if ([IO.Path]::GetExtension($resolved).ToLowerInvariant() -ne ".pyz") {
        throw "PyzPath必须指向.pyz文件：$resolved"
    }
    $arguments += @($resolved)
} else {
    $arguments += @("-m", "equipeffi")
}
$arguments += @("--web", "--host", $Host, "--port", "$Port")
if ($OpenBrowser) { $arguments += "--open-browser" }
& $PythonPath @arguments
exit $LASTEXITCODE
