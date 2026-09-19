param(
    [string]$WheelPath = "",
    [string]$InstallDir = "$env:LOCALAPPDATA\EquipEffi"
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WheelPath)) {
    $candidate = Get-ChildItem -Path (Join-Path $PSScriptRoot "..\dist") -Filter "equipeffi-*.whl" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -eq $candidate) {
        throw "未找到wheel，请使用 -WheelPath 指定 equipeffi-*.whl"
    }
    $WheelPath = $candidate.FullName
}

$wheel = (Resolve-Path -LiteralPath $WheelPath).Path
if ([IO.Path]::GetExtension($wheel) -ne ".whl") {
    throw "WheelPath必须指向.whl文件：$wheel"
}

$target = [IO.Path]::GetFullPath($InstallDir)
New-Item -ItemType Directory -Force -Path $target | Out-Null
$venv = Join-Path $target ".venv"
if (-not (Test-Path -LiteralPath (Join-Path $venv "Scripts\python.exe"))) {
    & python -m venv $venv
}
$python = Join-Path $venv "Scripts\python.exe"
& $python -m pip install --no-deps --no-index --upgrade $wheel

Write-Output "EquipEffi已安装到：$target"
Write-Output "启动窗口：$python -m equipeffi --gui"
Write-Output "命令行：$python -m equipeffi --list-device-types"
