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

Write-Output "EquipEffi headless核心已安装到：$target"
Write-Output "环境诊断：$python -m equipeffi --status"
Write-Output "正式Qt桌面需安装desktop extra：$python -m pip install 'equipeffi[desktop]'"
