"""可随wheel发布的Tk桌面启动器。

该模块只组装公共门面、V4适配器和窗口回调；判定内核本身不依赖Tk，
因此Linux服务或安卓桥接层可以绕过本模块复用同一套API。
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil

from ...application.bootstrap import create_application_api
from ...presentation.api.application_api import ApplicationApi
from ...infrastructure.excel.template_resource import V4TemplateResource
try:
    from .main_window import DesktopCallbacks, launch
    _DESKTOP_IMPORT_ERROR: Exception | None = None
except ImportError as exc:  # tkinter may be absent in a minimal Linux runtime.
    if "tkinter" not in str(exc).lower() and "_tkinter" not in str(exc).lower():
        raise
    DesktopCallbacks = None  # type: ignore[assignment,misc]
    launch = None  # type: ignore[assignment]
    _DESKTOP_IMPORT_ERROR = exc


def _run_web_fallback(
    api: ApplicationApi,
    template_resource: V4TemplateResource,
) -> None:
    """Run the presentation-independent Web window when Tk is unavailable."""

    from ..web.server import TemplateTransferPort, run_web

    transfer = TemplateTransferPort(
        download=lambda: (
            template_resource.template_path.name,
            template_resource.template_path.read_bytes(),
        )
    )
    host = os.environ.get("EQUIPEFFI_GUI_WEB_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("EQUIPEFFI_GUI_WEB_PORT", "8765"))
    except ValueError:
        port = 8765
    print("原生Tk窗口不可用，已切换到Web窗口。")
    run_web(api, host, port, open_browser=True, template_transfer=transfer)


def launch_packaged_gui() -> None:
    """启动不依赖仓库根目录的桌面窗口。"""
    package_root = Path(__file__).resolve().parents[2]
    # CLI、桌面和Web必须通过同一个应用工厂装配标准仓库、淘汰目录和V4契约。
    # ``resource_manager``与契约一起保留，确保从wheel/zip加载时模板临时文件
    # 在窗口生命周期内仍然有效；模板损坏时工厂会返回无契约回退表单。
    api, contract, resource_manager = create_application_api(
        project_root=package_root,
        load_template=True,
    )
    template_resource = resource_manager or V4TemplateResource()
    facade = api.facade
    # Excel读写本阶段严格只保留端口。V4 reader/writer 和批量编排器仍在
    # infrastructure/application 层维护，供未来宿主显式接入；启动器不再
    # 通过环境变量旁路启用试验实现，保证当前交付只依赖手工参数→判定闭环。

    def download_template(destination: Path) -> Path:
        configured = os.environ.get("EQUIPEFFI_V4_TEMPLATE", "")
        if configured and Path(configured).is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(configured, destination)
            return destination
        return template_resource.download_to(destination)

    if DesktopCallbacks is None or launch is None:
        _run_web_fallback(api, template_resource)
        return
    callbacks = DesktopCallbacks(
        download_template=download_template,
        upload_workbook=None,
        export_workbook=None,
    )
    try:
        launch(facade, contract=contract, callbacks=callbacks)
    except Exception as exc:
        # Some Python distributions ship tkinter but omit a usable Tcl/Tk
        # runtime (for example, ``init.tcl``).  Keep ``--gui`` useful in that
        # environment by falling back to the framework-free Web window.  Do
        # not hide unrelated application errors: only a Tk/Tcl initialization
        # failure is eligible for the fallback.
        if exc.__class__.__name__ != "TclError":
            raise
        _run_web_fallback(api, template_resource)
