<#
.SYNOPSIS
  EquipEffi Windows 开发入口（M1）：定位 Python 3.12、创建/复用项目 .venv、
  安装正式开发依赖，并打印当前解释器与关键包版本。

.DESCRIPTION
  单人维护的唯一推荐开发环境入口，目标是「一条命令得到可用的 3.12 环境」：
    1. 查找 Python 3.12（显式参数 -> 现有 .venv -> py 启动器 -> PATH）；
    2. 不存在则用 `python -m venv .venv` 创建，存在且版本正确则直接复用；
    3. 缺 pip 时用 `ensurepip` 补齐（只写入 .venv，不触碰全局 Python）；
    4. 按 CI 同一套命令安装正式开发依赖；
    5. 输出 Python / PySide6 / jsonschema / equipeffi 版本。

  边界：
    - 只写项目内 `.venv/`，不修改全局 Python、不升级系统解释器；
    - 不引入 Conda / Docker / 任何环境管理框架；
    - 可重复运行（幂等）；删除重建必须显式指定 -Recreate；
    - 项目正式运行时固定为 Python 3.12（pyproject.toml: requires-python = ">=3.12,<3.13"），
      **不升级到 3.13**。

  实现注意：所有外部命令都经 `Invoke-Native` 调用。PowerShell 5.1 在
  `$ErrorActionPreference = 'Stop'` 下，只要对原生命令做了 `2>$null`/`2>&1` 重定向，
  它的 stderr 就会变成终止错误——那样本脚本会在「检测 pip 是否存在」这一步误报失败。
  因此原生调用统一临时切到 `Continue`，只按退出码判定成败。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_dev.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_dev.ps1 -Python "C:\...\python3.12.exe"

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\setup_dev.ps1 -Recreate
#>
[CmdletBinding()]
param(
    # 显式指定的 Python 3.12 可执行文件；留空则自动查找
    [string]$Python = "",
    # 删除并重建项目 .venv（默认不删除）
    [switch]$Recreate,
    # 只定位/创建环境，不安装依赖
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'

function Write-Step([string]$Message) {
    Write-Host "[setup_dev] $Message"
}

# 统一的原生命令调用：返回退出码，绝不因 stderr 抛终止错误。
#   -Quiet      ：吞掉 stdout/stderr（用于探测）
#   -Capture    ：把 stdout 捕获为字符串返回（结果放在 -Result）
function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$File,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$Quiet,
        [switch]$Capture,
        [string]$Result = ''
    )
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $code = -1
    $output = @()
    try {
        if ($Quiet) {
            $output = @(& $File @Arguments 2>$null)
        } else {
            $output = @(& $File @Arguments 2>&1)
            foreach ($line in $output) { Write-Host $line }
        }
        $code = $LASTEXITCODE
    } catch {
        $code = -1
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($Result) {
        Set-Variable -Name $Result -Value (($output | ForEach-Object { "$_" }) -join "`n") -Scope 1
    }
    return $code
}

function Get-PythonMinor([string]$Executable) {
    if (-not $Executable) { return $null }
    $captured = ''
    $code = Invoke-Native -File $Executable -Arguments @('-c', "import sys; print('%d.%d' % sys.version_info[:2])") -Quiet -Capture -Result 'captured'
    if ($code -ne 0) { return $null }
    $value = $captured.Trim()
    if ($value -match '^\d+\.\d+$') { return $value }
    return $null
}

function Find-BasePython {
    # 1) 显式参数
    if ($Python) {
        if (-not (Test-Path $Python)) { throw "指定的 Python 不存在：$Python" }
        if ((Get-PythonMinor $Python) -ne '3.12') {
            throw "指定的 Python 不是 3.12：$Python（项目正式运行时固定 3.12，不升级 3.13）"
        }
        return $Python
    }

    # 2) 现有 .venv 且为 3.12 —— 复用，不重建
    if (Test-Path $venvPython) {
        $existing = Get-PythonMinor $venvPython
        if ($existing -eq '3.12') { return $venvPython }
        Write-Step "现有 .venv 不是 Python 3.12（当前 $existing）；确认后用 -Recreate 重建"
    }

    # 3) py 启动器：直接向启动器询问 3.12 解释器路径，避免解析本地化输出
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $probe = ''
        $code = Invoke-Native -File $pyLauncher.Source -Arguments @('-3.12', '-c', 'import sys; print(sys.executable)') -Quiet -Capture -Result 'probe'
        if ($code -eq 0) {
            $path = $probe.Trim()
            if ((Get-PythonMinor $path) -eq '3.12') { return $path }
        }
    }

    # 4) PATH 上的 python3.12 / python
    foreach ($name in @('python3.12', 'python')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and ((Get-PythonMinor $cmd.Source) -eq '3.12')) { return $cmd.Source }
    }

    throw "未找到 Python 3.12。请安装 3.12，或用 -Python 指定可执行文件路径。（项目不升级 3.13）"
}

function Ensure-Venv([string]$BasePython) {
    if (Test-Path $venvPython) {
        $version = Get-PythonMinor $venvPython
        if ($version -eq '3.12') {
            Write-Step "复用已有 .venv（Python 3.12）"
            return
        }
        throw ".venv 存在但不是 Python 3.12（当前 $version）。确认后用 -Recreate 重建。"
    }
    Write-Step "创建 .venv（$BasePython）"
    $code = Invoke-Native -File $BasePython -Arguments @('-m', 'venv', $venvDir)
    if ($code -ne 0 -or -not (Test-Path $venvPython)) {
        throw "创建 .venv 失败（exit=$code）"
    }
}

function Install-Dependencies {
    # pip 是否存在：按退出码判定，不看输出（uv 建的 venv 默认没有 pip）
    $code = Invoke-Native -File $venvPython -Arguments @('-m', 'pip', '--version') -Quiet
    if ($code -ne 0) {
        Write-Step "venv 缺少 pip，用 ensurepip 补齐（仅写入 .venv）"
        $code = Invoke-Native -File $venvPython -Arguments @('-m', 'ensurepip', '--upgrade')
        if ($code -ne 0) { throw "ensurepip 失败（exit=$code）" }
    }
    # 与 .github/workflows/windows-core.yml 完全相同的依赖集合
    Write-Step "安装正式开发依赖（.[tools,desktop] + jsonschema==4.26.0）"
    $code = Invoke-Native -File $venvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
    if ($code -ne 0) { throw "pip 升级失败（exit=$code）" }
    $code = Invoke-Native -File $venvPython -Arguments @('-m', 'pip', 'install', '-e', '.[tools,desktop]', 'jsonschema==4.26.0')
    if ($code -ne 0) { throw "依赖安装失败（exit=$code）" }
}

function Show-Versions {
    Write-Step "当前环境"
    $probe = @'
import sys
print("  python     :", sys.version.split()[0], sys.executable)
for name, label in (("PySide6", "PySide6"), ("jsonschema", "jsonschema"), ("equipeffi", "equipeffi")):
    try:
        module = __import__(name)
    except Exception as exc:
        print("  %-11s:" % label, "(未安装：%s)" % type(exc).__name__)
        continue
    try:
        from importlib.metadata import version as _pkg_version
        print("  %-11s:" % label, _pkg_version(name))
    except Exception:
        print("  %-11s:" % label, getattr(module, "__version__", "?"))
'@
    # 经 stdin 传递探测脚本，故不走 Invoke-Native（避免捕获输出丢失），只临时放宽 EAP
    $code = -1
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $probe | & $venvPython -
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
    if ($code -ne 0) { throw "环境自检失败（exit=$code）" }
    Write-Step "完成。后续测试请用：`"$venvPython`" -m unittest ..."
}

try {
    Push-Location $repoRoot

    if ($Recreate -and (Test-Path $venvDir)) {
        Write-Step "-Recreate：删除现有 .venv"
        Remove-Item -Recurse -Force $venvDir
    }

    $basePython = Find-BasePython
    Write-Step "基准 Python 3.12：$basePython"
    Ensure-Venv $basePython

    if (-not $SkipInstall) {
        Install-Dependencies
    } else {
        Write-Step "已指定 -SkipInstall，跳过依赖安装"
    }

    Show-Versions
    Pop-Location
    exit 0
} catch {
    Write-Host "[setup_dev] 失败：$($_.Exception.Message)" -ForegroundColor Red
    if ((Get-Location).Path -eq $repoRoot) { Pop-Location }
    exit 1
}
