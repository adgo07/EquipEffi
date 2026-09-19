from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import json
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ...application.services.evaluation_facade import EvaluationFacade, EvaluationRequest
from ...application.services.evaluation_service import DEFAULT_EVALUATION_DATE
from ...application.services.schema_constraints import fallback_field_metadata
from ...application.services.v4_template_contract import CONDITIONAL_LIMITS, V4TemplateContract
from ...domain.common.enums import EliminationScope
from ...domain.common.models import EvaluationResult
from ...domain.evaluation.device_specs import ENUM_VALUES, get_device_spec
from ...domain.evaluation.device_types import PUBLIC_DEVICE_NAMES, PUBLIC_DEVICE_TYPES
from ...domain.evaluation.metadata import get_device_profile
from ...infrastructure.excel.template_resource import V4TemplateResource
from ..api.application_api import public_input_extensions
from ..metadata_projection import (
    MetadataProjectionError,
    metadata_fallback_input_payloads,
    project_input_payloads,
)


@dataclass(frozen=True)
class DesktopCallbacks:
    """窗口与模板/Excel适配器之间的端口；默认实现不读取或改写Excel。"""

    download_template: Callable[[Path], Path | None] | None = None
    upload_workbook: Callable[[Path], str | None] | None = None
    export_workbook: Callable[[Path], Path | None] | None = None


def _fallback_profile(public_device_type: str) -> str:
    return {
        "motor": "motor_lv",
        "centrifugal_pump": "pump_water",
        "centrifugal_fan": "fan",
        "axial_fan": "fan",
        "submersible_pump": "submersible",
        "industrial_boiler": "boiler",
    }.get(public_device_type, public_device_type)


def conclusion_field_label(public_device_type: str) -> str:
    """Return the V4 wording for the final result field.

    Most sheets call the result ``能效等级``.  The V4 workbook deliberately
    uses ``能效结论`` for blowers and ``评价等级`` for heat-treatment
    equipment, so the desktop presentation must not hard-code the common
    wording and accidentally contradict the sheet contract.
    """

    return {
        "blower": "能效结论",
        "heat_treatment": "评价等级",
    }.get(public_device_type, "能效等级")


def _fallback_common_fields() -> tuple[dict[str, Any], ...]:
    """Return the common V4 input prefix for the dependency-free form.

    The normal path reads these fields from the V4 workbook contract.  Keeping
    the same prefix in the fallback is important for portable/mobile builds:
    a missing workbook must not make model, quantity, category or the nameplate
    attachment disappear from the manual evaluation form.
    """

    definitions = (
        ("device_name", "设备名称", "文本", "-", "可选", "缺失时在自动备注中提示", None, None),
        ("model", "型号", "文本", "-", "可选", "用于标准匹配和淘汰目录匹配", None, None),
        ("quantity", "数量", "整数", "件", "必填", "应为正整数", 1, None),
        ("category", "设备类别", "文本", "-", "必填", "按标准枚举填写", None, None),
        ("location", "安装位置", "文本", "-", "可选", "可选", None, None),
        ("photo", "铭牌照片", "图片", "-", "可选", "使用置于单元格的铭牌照片", None, None),
    )
    return tuple(
        {
            "field_id": field_id,
            "display_name": display_name,
            "group": "基础信息",
            "data_type": data_type,
            "unit": unit,
            "required": required,
            "validation": validation,
            "minimum": minimum,
            "maximum": maximum,
            "enum_name": "",
            "enum_values": [],
        }
        for field_id, display_name, data_type, unit, required, validation, minimum, maximum in definitions
    )


def form_fields_for_public_type(
    public_device_type: str,
    contract: V4TemplateContract | None = None,
) -> tuple[dict[str, Any], ...]:
    """返回窗口参数字段。

    V4契约存在时优先使用其可编辑字段；开发期没有加载工作簿时才使用内部profile的
    最小兼容字段，便于先启动窗口和判定闭环。
    """

    if contract is not None:
        fields = contract.fields_for_public_type(public_device_type, editable_only=True)
        if fields:
            payloads = [{
                "field_id": field.field_id,
                "display_name": field.display_name,
                "group": field.group,
                "data_type": field.data_type,
                "unit": field.unit,
                "required": field.required,
                "validation": field.validation,
                "minimum": field.minimum,
                "maximum": field.maximum,
                "enum_name": field.enum_name,
                "enum_values": list(contract.enums.get(field.enum_name, ())),
                **(
                    {"conditional_limits": [dict(rule) for rule in CONDITIONAL_LIMITS.get((field.sheet, field.field_id), ())]}
                    if (field.sheet, field.field_id) in CONDITIONAL_LIMITS
                    else {}
                ),
            } for field in fields]
            try:
                payloads = project_input_payloads(
                    public_device_type,
                    payloads,
                    mode="v4",
                    context=f"{public_device_type}桌面V4",
                )
            except MetadataProjectionError as exc:
                raise ValueError(str(exc)) from exc
            seen = {item["field_id"] for item in payloads}
            for extension in public_input_extensions(public_device_type):
                if extension["field_id"] not in seen:
                    payloads.append(extension)
                    seen.add(extension["field_id"])
            return tuple(payloads)
    profile = _fallback_profile(public_device_type)
    spec = get_device_spec(profile)
    fields = list(_fallback_common_fields())
    # 回退窗口的枚举展示与自动备注校验共用领域元数据；当前只有已
    # 通过契约测试的规则族会返回非空枚举，其他设备保持原有输入形状。
    metadata_profile = get_device_profile(public_device_type)
    for payload in fields:
        metadata_field = metadata_profile.field(payload["field_id"])
        if metadata_field.enum_name and metadata_field.enum_values:
            payload["enum_name"] = metadata_field.enum_name
            payload["enum_values"] = list(metadata_field.enum_values)
    seen = {field["field_id"] for field in fields}
    for field in spec.get("fields", ()):
        field_id = field["name"]
        # The common prefix owns identity fields.  Production year is an
        # internal legacy input and is deliberately not exposed by the V4 UI.
        if field_id in seen or field_id == "production_year":
            continue
        seen.add(field_id)
        metadata = fallback_field_metadata(public_device_type, field_id)
        note = str(field.get("note", "") or "")
        validation = note
        if metadata["validation"] and metadata["validation"] not in note:
            validation = f"{note}；{metadata['validation']}" if note else metadata["validation"]
        data_type = "数值" if field["unit"] not in {"-", "No."} else "文本"
        metadata_field = metadata_profile.field(field_id) if metadata_profile is not None else None
        if metadata_field is not None:
            data_type = {
                "text": "文本",
                "number": "数值",
                "integer": "整数",
                "percentage": "数值",
                "image": "图片",
            }.get(metadata_field.data_type, data_type)
        payload = {
            "field_id": field_id,
            "display_name": field["label"],
            "group": "设备参数",
            "data_type": data_type,
            "unit": field["unit"],
            "required": "必填" if field.get("required", True) else "可选",
            "validation": validation,
            "minimum": metadata["minimum"],
            "maximum": metadata["maximum"],
            # 与公共API的回退schema保持同一枚举来源。V4契约不可读时，
            # 冷却方式等受限字段仍渲染为下拉框，避免回退窗口退化为可任意
            # 输入的文本框；未知枚举字段继续保持文本输入。
            "enum_name": (
                metadata_profile.field(field_id).enum_name
                if metadata_profile is not None and metadata_profile.field(field_id).enum_name
                else str(field.get("enum_name", "") or "")
            ),
            "enum_values": (
                list(metadata_profile.field(field_id).enum_values)
                if metadata_profile is not None and metadata_profile.field(field_id).enum_values
                else list(ENUM_VALUES.get(str(field.get("enum_name", "") or ""), ()))
            ),
        }
        if metadata.get("conditional_limits"):
            payload["conditional_limits"] = metadata["conditional_limits"]
        fields.append(payload)
    # Keep the dependency-free desktop form aligned with V4 columns that are
    # present only in the unified metadata profile, not in legacy specs.
    for payload in metadata_fallback_input_payloads(public_device_type, seen):
        fields.append(payload)
        seen.add(payload["field_id"])
    try:
        fields = project_input_payloads(
            public_device_type,
            fields,
            mode="fallback",
            context=f"{public_device_type}桌面回退",
        )
    except MetadataProjectionError as exc:
        raise ValueError(str(exc)) from exc
    return tuple(fields)


def elimination_scope_options() -> tuple[str, ...]:
    """返回窗口可选择的淘汰目录口径；不依赖Tk，供移动/网页外层复用。"""

    return tuple(item.value for item in EliminationScope)


def capability_status_text(facade: EvaluationFacade) -> str:
    """Format a compact capability snapshot for the desktop sidebar.

    The window reads the same repositories as the JSON ``status`` endpoint;
    this is presentation-only and does not duplicate any standard logic.
    """

    service = facade.evaluation_service
    packs = service.standards.list_packs() if hasattr(service.standards, "list_packs") else ()
    pmsm = next((item for item in packs if item.get("device_type") == "motor_pmsm"), {})
    pmsm_status = str(pmsm.get("status", "未知"))
    catalog_count = len(getattr(service.elimination, "entries", ()))
    if getattr(service.elimination, "has_industry_catalog", False):
        industry = "已加载（非全文）" if not getattr(service.elimination, "industry_catalog_complete", False) else "已加载"
    else:
        industry = "未导入"
    return f"标准包：{len(packs)}；PMSM：{pmsm_status}；淘汰目录规则：{catalog_count}条；产业目录：{industry}"


def download_builtin_template(destination: Path) -> Path:
    """将内置V4空白模板复制到用户选择的位置。

    这是窗口层的默认资源端口：下载不依赖Excel导入/回写适配器，也不覆盖
    软件内置模板。打包到wheel或移动端桥接层时仍由``V4TemplateResource``
    负责从文件系统或包资源物化模板。
    """

    return V4TemplateResource().download_to(Path(destination))


def result_summary(result: EvaluationResult | None) -> dict[str, str]:
    """Return a compact, presentation-only summary shared by the desktop view.

    The complete serialized result remains in the detail pane.  Keeping this
    helper independent of Tk makes the same display contract easy to reuse in
    a future native or mobile presentation layer without copying evaluation
    logic.
    """

    if result is None:
        return {
            "standard": "—",
            "reference": "—",
            "explanation": "—",
            "missing": "—",
            "quality": "—",
        }
    reference = result.reference_conclusion.value if result.reference_conclusion else "—"
    quality = "；".join(
        str(item.get("message") or item.get("code") or "")
        for item in result.data_quality_issues
        if item.get("message") or item.get("code")
    ) or "无"
    return {
        "standard": str(result.standard_reference.get("standard_code") or "—"),
        "reference": reference,
        "explanation": str(result.explanation or "—"),
        "missing": "、".join(str(item) for item in result.missing_fields) or "无",
        "quality": quality,
    }


class EquipmentEfficiencyWindow:
    """跨平台桌面窗口MVP。

    窗口只负责交互和展示；判定通过EvaluationFacade完成。模板下载和工作簿上传
    使用回调端口，后续可以替换为V4 OOXML适配器而不改窗口。
    """

    def __init__(
        self,
        facade: EvaluationFacade,
        *,
        contract: V4TemplateContract | None = None,
        callbacks: DesktopCallbacks | None = None,
        root: tk.Tk | None = None,
    ):
        self.facade = facade
        self.contract = contract
        self.callbacks = callbacks or DesktopCallbacks()
        self.root = root or tk.Tk()
        self.root.title("设备能效分析")
        self.root.geometry("1180x760")
        self.root.minsize(960, 620)
        self._variables: dict[str, tk.Variable] = {}
        self._field_widgets: list[tk.Widget] = []
        self._elimination_scope = tk.StringVar(value=EliminationScope.MOTOR_BATCHES_1_4.value)
        self._as_of = tk.StringVar(value=DEFAULT_EVALUATION_DATE.isoformat())
        self._build()

    def _build(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(12, 10))
        header.grid(row=0, column=0, columnspan=3, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="设备能效分析", font=("Microsoft YaHei", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="V4公共接口 · 出厂设计/额定/铭牌值").grid(row=1, column=0, sticky="w", pady=(3, 0))
        ttk.Button(header, text="下载空白模板", command=self._download_template).grid(row=0, column=1, rowspan=2, padx=4)
        ttk.Button(header, text="上传V4工作簿", command=self._upload_workbook).grid(row=0, column=2, rowspan=2, padx=4)
        ttk.Button(header, text="导出判定结果", command=self._export_workbook).grid(row=0, column=3, rowspan=2, padx=4)

        left = ttk.LabelFrame(self.root, text="设备类型", padding=10)
        left.grid(row=1, column=0, sticky="ns", padx=(12, 6), pady=(0, 12))
        ttk.Label(left, text="选择V4设备sheet").pack(anchor="w")
        self._device_combo = ttk.Combobox(left, state="readonly", width=20, values=[PUBLIC_DEVICE_NAMES[code] for code in PUBLIC_DEVICE_TYPES])
        self._device_combo.pack(anchor="w", pady=(8, 14))
        self._device_combo.bind("<<ComboboxSelected>>", self._on_device_change)
        self._device_combo.current(0)
        ttk.Label(left, text="公共类型数量：15").pack(anchor="w", pady=(12, 0))
        ttk.Label(left, text="内部标准差异由profile自动路由", wraplength=170).pack(anchor="w", pady=(5, 0))
        ttk.Label(left, text="判定基准日期（YYYY-MM-DD）").pack(anchor="w", pady=(18, 3))
        ttk.Entry(left, textvariable=self._as_of, width=18).pack(anchor="w", fill="x")
        ttk.Label(left, text="淘汰判定口径").pack(anchor="w", pady=(18, 3))
        ttk.Combobox(
            left,
            textvariable=self._elimination_scope,
            values=elimination_scope_options(),
            state="readonly",
            width=28,
        ).pack(anchor="w", fill="x")
        ttk.Label(
            left,
            text="产业目录仅覆盖已载入条目；未覆盖或条件不足时返回无法判定。",
            wraplength=210,
            foreground="#666666",
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(
            left,
            text=capability_status_text(self.facade),
            wraplength=230,
            foreground="#666666",
        ).pack(anchor="w", pady=(10, 0))

        center = ttk.LabelFrame(self.root, text="参数填写", padding=10)
        center.grid(row=1, column=1, sticky="nsew", padx=6, pady=(0, 12))
        center.columnconfigure(1, weight=1)
        center.rowconfigure(1, weight=1)
        self._form_canvas = tk.Canvas(center, highlightthickness=0)
        scroll = ttk.Scrollbar(center, orient="vertical", command=self._form_canvas.yview)
        self._form_frame = ttk.Frame(self._form_canvas)
        self._form_frame.columnconfigure(1, weight=1)
        self._form_canvas.configure(yscrollcommand=scroll.set)
        self._form_canvas.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")
        center.bind("<Configure>", lambda _event: self._form_canvas.configure(scrollregion=self._form_canvas.bbox("all")))
        self._form_window = self._form_canvas.create_window((0, 0), window=self._form_frame, anchor="nw")
        self._form_frame.bind("<Configure>", lambda _event: self._form_canvas.configure(scrollregion=self._form_canvas.bbox("all")))
        self._form_canvas.bind("<Configure>", lambda event: self._form_canvas.itemconfigure(self._form_window, width=event.width))
        self._render_form()
        ttk.Button(center, text="开始判定", command=self._evaluate).grid(row=2, column=0, columnspan=2, pady=(10, 0))

        right = ttk.LabelFrame(self.root, text="判定结果", padding=10)
        right.grid(row=1, column=2, sticky="nsew", padx=(6, 12), pady=(0, 12))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self._result_label = ttk.Label(right, text="尚未判定", font=("Microsoft YaHei", 14, "bold"))
        self._result_label.grid(row=0, column=0, sticky="w", pady=(0, 10))
        summary = ttk.Frame(right)
        summary.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        summary.columnconfigure(1, weight=1)
        self._summary_labels: dict[str, ttk.Label] = {}
        summary_names = {
            "standard": "采用标准",
            "reference": "参考能效等级",
            "explanation": "判定说明",
            "missing": "缺失信息",
            "quality": "数据质量",
        }
        for row, (key, label) in enumerate(summary_names.items()):
            ttk.Label(summary, text=label, foreground="#65727e").grid(row=row, column=0, sticky="nw", padx=(0, 8), pady=2)
            value = ttk.Label(summary, text="—", wraplength=330, justify="left")
            value.grid(row=row, column=1, sticky="ew", pady=2)
            self._summary_labels[key] = value
        self._result_text = tk.Text(right, width=42, height=32, wrap="word", state="disabled")
        self._result_text.grid(row=2, column=0, sticky="nsew")

    def _public_type(self) -> str:
        name = self._device_combo.get()
        return next(code for code in PUBLIC_DEVICE_TYPES if PUBLIC_DEVICE_NAMES[code] == name)

    def _render_form(self) -> None:
        for widget in self._field_widgets:
            widget.destroy()
        self._field_widgets.clear()
        self._variables.clear()
        for index, field in enumerate(form_fields_for_public_type(self._public_type(), self.contract)):
            label = f"{field['display_name']}" + (f" ({field['unit']})" if field["unit"] not in {"", "-"} else "")
            ttk.Label(self._form_frame, text=label).grid(row=index, column=0, sticky="w", padx=(0, 10), pady=5)
            variable = tk.StringVar()
            self._variables[field["field_id"]] = variable
            if field["data_type"] == "图片":
                entry = ttk.Entry(self._form_frame, textvariable=variable)
                entry.grid(row=index, column=1, sticky="ew", pady=5)
                button = ttk.Button(
                    self._form_frame,
                    text="选择图片",
                    command=lambda target=variable: self._choose_photo(target),
                )
                button.grid(row=index, column=2, sticky="w", padx=(6, 0), pady=5)
                self._field_widgets.extend((self._form_frame.grid_slaves(row=index, column=0)[0], entry, button))
            elif field.get("enum_values"):
                entry = ttk.Combobox(
                    self._form_frame,
                    textvariable=variable,
                    values=tuple(field["enum_values"]),
                    state="readonly",
                )
                entry.grid(row=index, column=1, sticky="ew", pady=5)
                self._field_widgets.extend((self._form_frame.grid_slaves(row=index, column=0)[0], entry))
            else:
                entry = ttk.Entry(self._form_frame, textvariable=variable)
                entry.grid(row=index, column=1, sticky="ew", pady=5)
                self._field_widgets.extend((self._form_frame.grid_slaves(row=index, column=0)[0], entry))

    def _on_device_change(self, _event: tk.Event) -> None:
        self._render_form()
        self._result_label.configure(text="尚未判定")
        self._set_summary(None)
        self._set_result_text("")

    @staticmethod
    def _choose_photo(variable: tk.StringVar) -> None:
        source = filedialog.askopenfilename(
            title="选择铭牌照片",
            filetypes=[("图片", "*.png;*.jpg;*.jpeg;*.bmp"), ("所有文件", "*.*")],
        )
        if source:
            variable.set(source)

    def _evaluate(self) -> None:
        values = {key: value.get() for key, value in self._variables.items() if value.get() != ""}
        try:
            scope = EliminationScope(self._elimination_scope.get())
        except ValueError:
            messagebox.showerror("判定失败", "淘汰判定口径无效，请重新选择。")
            return
        try:
            result = self.facade.evaluate(
                EvaluationRequest(
                    record_id="DESKTOP-001",
                    device_type=self._public_type(),
                    values=values,
                    source="desktop_manual",
                    template_id=self.contract.template_id if self.contract else "",
                    as_of=self._as_of.get().strip() or DEFAULT_EVALUATION_DATE.isoformat(),
                ),
                elimination_scope=scope,
            )
        except Exception as exc:
            # 参数/日期/标准门禁错误必须在窗口内反馈，不能把Tk主循环打崩。
            # 详细异常仍由API和判定轨迹负责；窗口只展示可读消息。
            messagebox.showerror("判定失败", str(exc))
            return
        self._result_label.configure(text=f"{conclusion_field_label(result.public_device_type or self._public_type())}：{result.conclusion.value}")
        self._set_summary(result)
        self._set_result_text(json.dumps(self.facade.to_record(result), ensure_ascii=False, indent=2))

    def _set_summary(self, result: EvaluationResult | None) -> None:
        for key, value in result_summary(result).items():
            label = self._summary_labels.get(key)
            if label is not None:
                label.configure(text=value)

    def _download_template(self) -> None:
        destination = filedialog.asksaveasfilename(
            title="保存V4空白模板",
            defaultextension=".xlsx",
            filetypes=[("Excel工作簿", "*.xlsx")],
        )
        if not destination:
            return
        target = Path(destination)
        try:
            downloader = self.callbacks.download_template or download_builtin_template
            output = downloader(target)
        except Exception as exc:
            messagebox.showerror("模板下载失败", str(exc))
            return
        if output:
            messagebox.showinfo("模板下载", f"已保存：{output}")

    def _upload_workbook(self) -> None:
        source = filedialog.askopenfilename(
            title="选择V4工作簿",
            filetypes=[("Excel工作簿", "*.xlsx")],
        )
        if not source:
            return
        if self.callbacks.upload_workbook is None:
            messagebox.showinfo("上传V4工作簿", "工作簿读取接口已预留，Excel导入器尚未接入。")
            return
        try:
            message = self.callbacks.upload_workbook(Path(source))
        except Exception as exc:
            messagebox.showerror("上传V4工作簿失败", str(exc))
            return
        if message:
            messagebox.showinfo("上传V4工作簿", message)

    def _export_workbook(self) -> None:
        destination = filedialog.asksaveasfilename(
            title="保存V4判定结果",
            defaultextension=".xlsx",
            filetypes=[("Excel工作簿", "*.xlsx")],
        )
        if not destination:
            return
        if self.callbacks.export_workbook is None:
            messagebox.showinfo("导出判定结果", "结果写回接口尚未配置，请先上传V4工作簿。")
            return
        try:
            output = self.callbacks.export_workbook(Path(destination))
        except Exception as exc:
            messagebox.showerror("导出判定结果失败", str(exc))
            return
        if output:
            messagebox.showinfo("导出判定结果", f"已保存：{output}")

    def _set_result_text(self, text: str) -> None:
        self._result_text.configure(state="normal")
        self._result_text.delete("1.0", tk.END)
        self._result_text.insert("1.0", text)
        self._result_text.configure(state="disabled")

    def run(self) -> None:
        self.root.mainloop()


def launch(facade: EvaluationFacade, *, contract: V4TemplateContract | None = None, callbacks: DesktopCallbacks | None = None) -> None:
    EquipmentEfficiencyWindow(facade, contract=contract, callbacks=callbacks).run()
