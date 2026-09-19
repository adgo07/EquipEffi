param(
    [Parameter(Mandatory = $false)]
    [string]$PackagePath = "",
    [string]$InstallDir = "$env:LOCALAPPDATA\EquipEffi\native",
    [switch]$CreateShortcut
)

$ErrorActionPreference = "Stop"

function Resolve-Package([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        $candidate = Get-ChildItem -Path (Join-Path $PSScriptRoot "..\outputs") -Recurse -Filter "equipeffi-windows-*.zip" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($null -eq $candidate) {
            throw "未找到Windows原生ZIP，请使用 -PackagePath 指定文件"
        }
        return $candidate.FullName
    }
    return (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
}

$package = Resolve-Package $PackagePath
if ([IO.Path]::GetExtension($package).ToLowerInvariant() -ne ".zip") {
    throw "PackagePath必须指向.zip文件：$package"
}

$target = [IO.Path]::GetFullPath($InstallDir)
if ([string]::IsNullOrWhiteSpace($target) -or $target -eq [IO.Path]::GetPathRoot($target)) {
    throw "InstallDir不能是磁盘根目录：$target"
}
New-Item -ItemType Directory -Force -Path $target | Out-Null

# 使用临时目录展开，再以文件复制方式切换，避免ZIP损坏时破坏已有安装。
$staging = Join-Path ([IO.Path]::GetTempPath()) ("equipeffi-native-" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $staging | Out-Null
try {
    Expand-Archive -LiteralPath $package -DestinationPath $staging -Force
    $root = Join-Path $staging "equipeffi"
    $exe = Join-Path $root "equipeffi.exe"
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
        throw "原生ZIP缺少 equipeffi/equipeffi.exe：$package"
    }
    # 只更新目标目录中的程序文件，不删除目标目录中用户保留的其他文件。
    # 逐项使用LiteralPath，避免通配符在LiteralPath下被当成普通字符。
    Get-ChildItem -LiteralPath $root -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $target $_.Name) -Recurse -Force
    }
}
finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$installed = Join-Path $target "equipeffi.exe"
if (-not (Test-Path -LiteralPath $installed -PathType Leaf)) {
    throw "安装后未找到启动文件：$installed"
}

if ($CreateShortcut) {
    $desktop = [Environment]::GetFolderPath("Desktop")
    $shortcutPath = Join-Path $desktop "EquipEffi.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $installed
    $shortcut.WorkingDirectory = $target
    $shortcut.Arguments = "--gui"
    $shortcut.Description = "EquipEffi设备能效分析（Tk不可用时自动回退Web窗口）"
    $shortcut.Save()
}

$statusText = & $installed --status | Out-String
if ($LASTEXITCODE -ne 0) {
    throw "安装后状态检查失败，退出码：$LASTEXITCODE"
}
Write-Output "EquipEffi Windows原生包已安装到：$target"
Write-Output "启动：$installed --gui"
Write-Output $statusText.Trim()
