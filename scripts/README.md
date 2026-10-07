# 跨平台启动脚本

这些脚本是本地 wheel 的轻量安装引导，不下载网络依赖，也不删除已有目录。它们不改变判定内核与Excel适配器的边界。

可以把已构建的 wheel、脚本和运行说明打成离线便携包（不等同于原生安装程序）：

```powershell
python tools/build_portable_bundle.py `
  --wheel outputs/final_20260828_web_latest/equipeffi-0.2.1-py3-none-any.whl `
  --zipapp outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.pyz `
  --output outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.zip
```

也可以单独生成无需安装的跨平台 `.pyz`：

```powershell
python tools/build_zipapp.py --output outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.pyz
python outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.pyz --status
```

正式构建审计也支持在审计通过后追加生成便携包：

```powershell
python tools/build_release.py --output-dir dist `
  --portable-output outputs/final_20260828_web_latest/equipeffi-portable-20260828-web-latest.zip
```

指定`--portable-output`时，正式构建会自动在同目录生成同名`.pyz`并将其嵌入ZIP；如需指定路径，可追加`--zipapp-output`。
发布构建和大体量人工校对册生成共用项目级非阻塞锁；检测到已有任务时会立即退出，不排队启动第二个高CPU任务。

ZIP内含 `SHA256SUMS.txt` 和 `运行说明.txt`。目标系统需要 Python 3.12 或更高版本（项目正式运行时）；
Windows/Linux脚本会在指定目录创建或复用虚拟环境并以 `--no-index` 安装本地 wheel。

Windows PowerShell：

```powershell
.\scripts\install_windows.ps1 -WheelPath .\outputs\final_20260828_web_latest\equipeffi-0.2.1-py3-none-any.whl
```

已有Windows原生ZIP时，可使用独立安装入口（不删除原目录；先在临时目录校验启动文件，再复制到用户目录）：

```powershell
.\scripts\install_native_windows.ps1 -PackagePath .\outputs\final_20260829_trace16\equipeffi-windows-web-fallback.zip -CreateShortcut
```

该安装入口会在安装后执行`equipeffi.exe --status`。**正式桌面 Shell 为 PySide6 Qt**
（无参数 / `--gui` / `--qt` 同一入口），不存在 Tk 窗口或「Tk 不可用回退 Web 窗口」的行为。
构建报告中的 `presentation_mode`（`native_tk` / `web_fallback`）是历史 Tk 时代的构建诊断字段，
仅为兼容 `tools/audit_release.py` 的既有校验而保留，**不是当前 UI 入口的描述**；发行包裁剪属于 Phase 9。

正式MSI（需要目标Windows安装WiX v4）：

```powershell
python tools/build_msi.py `
  --native-dir .\outputs\native\dist\equipeffi `
  --output .\outputs\native\equipeffi.msi
```

没有WiX时可加`--dry-run`，只生成WXS源和报告，不会伪造或覆盖MSI。

Linux：

```bash
sh scripts/install_linux.sh outputs/final_20260828_web_latest/equipeffi-0.2.1-py3-none-any.whl
```

Linux桌面或服务器若启用systemd用户会话，可安装为用户服务（服务已存在时脚本会停止，不覆盖已有配置）：

```bash
sh scripts/install_linux_service.sh ./equipeffi-0.2.1-py3-none-any.whl "$HOME/.local/share/equipeffi" 127.0.0.1 8765
```

该服务只启动Web展示层，判定内核仍从同一wheel加载；没有systemd用户会话时继续使用`run_web_linux.sh`或JSONL入口。
安装前可只渲染服务单元而不写入任何用户目录：

```bash
sh scripts/install_linux_service.sh --dry-run "" "$HOME/.local/share/equipeffi" 127.0.0.1 8765
```

安装后，Linux服务或安卓桥接层只调用 `python -m equipeffi --list-device-types`、单条 `--json` 或批量 `--batch-json`；桌面窗口只是可替换的展示层（正式 Shell 为 PySide6 Qt）。
如果目标机未安装桌面依赖，可运行 `python -m equipeffi --web --open-browser` 使用标准库浏览器窗口；该窗口与正式桌面入口共享同一ApplicationApi（compatibility surface）。
需要长驻进程桥接时可调用 `python -m equipeffi --jsonl`，输入和输出均为逐行JSON，不依赖桌面窗口或Excel。
便携包也提供 `scripts/run_jsonl_windows.ps1` 和 `scripts/run_jsonl_linux.sh`：传入 `.pyz` 路径时直接运行zipapp，不传参数时调用已安装的 `equipeffi` 模块。

启动浏览器窗口：

```powershell
.\scripts\run_web_windows.ps1 -OpenBrowser
# 也可直接运行便携.pyz：
.\scripts\run_web_windows.ps1 -PyzPath .\equipeffi-portable.pyz -OpenBrowser
```

```bash
EQUIPEFFI_WEB_OPEN_BROWSER=1 sh scripts/run_web_linux.sh
# 也可直接运行便携.pyz：
sh scripts/run_web_linux.sh --pyz ./equipeffi-portable.pyz 127.0.0.1 8765
```

两个脚本只负责启动Web展示层，仍复用同一`ApplicationApi`，不读取或写回Excel。
