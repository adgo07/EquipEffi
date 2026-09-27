from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any, Callable
import urllib.parse
import webbrowser

from ..api.application_api import ApiRequestError, ApplicationApi


# JSON requests are deliberately bounded, while an Excel workbook may contain
# embedded images and substantially exceed 1 MiB.  Keep the limits separate so
# the adapter boundary remains usable for the planned 1,500-row validation.
MAX_JSON_BODY_BYTES = 4 * 1_048_576
MAX_UPLOAD_BYTES = 50 * 1_048_576
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True)
class TemplateTransferPort:
    """可选的模板传输端口。

    Web层不解析Excel。宿主可以注入下载/上传回调，桌面端、服务端或移动端
    适配器各自决定文件来源和保存方式；未注入时接口仍可达但明确返回501。
    """

    download: Callable[[], tuple[str, bytes]] | None = None
    upload: Callable[[str, bytes], Any] | None = None


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")


INDEX_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>设备能效分析</title>
<style>
body{font-family:system-ui,"Microsoft YaHei",sans-serif;margin:0;background:#f4f6f8;color:#202124}
header{background:#145da0;color:#fff;padding:16px 24px} main{display:grid;grid-template-columns:220px minmax(360px,1fr) minmax(320px,1fr);gap:16px;padding:16px;max-width:1500px;margin:auto}
section{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 4px #0002} label{display:block;margin:10px 0 4px;font-size:13px;color:#555} input,select,button{box-sizing:border-box;width:100%;padding:8px;border:1px solid #c8d0d8;border-radius:4px;font:inherit}button{background:#145da0;color:white;border:0;cursor:pointer;margin-top:14px}button.secondary{background:#5f6b76}.field{border-bottom:1px solid #edf0f2;padding-bottom:4px}.unit{color:#777;font-size:12px} pre{white-space:pre-wrap;word-break:break-word;font-size:12px;max-height:650px;overflow:auto}.grade{font-size:22px;font-weight:600;color:#145da0}.summary{margin:12px 0;padding:10px;background:#f7f9fb;border-left:3px solid #145da0}.summary div{display:grid;grid-template-columns:100px 1fr;gap:8px;margin:5px 0;font-size:13px}.summary span{color:#65727e}.summary b{font-weight:500;word-break:break-word}
@media(max-width:900px){main{display:block}section{margin-bottom:12px}}
</style></head><body>
<header><strong>设备能效分析</strong><div>V4公共接口 · 出厂设计/额定/铭牌值</div></header>
<main><section><label>设备类型</label><select id="device"></select><label>判定基准日期</label><input id="asof" value="2026-08-23"><label>淘汰判定口径</label><select id="scope"><option>高耗能落后机电设备淘汰目录第一至第四批</option><option>仅产业结构调整指导目录</option><option>产业结构调整指导目录+高耗能落后机电设备淘汰目录第一至第四批</option></select><button class="secondary" onclick="downloadTemplate()">下载空白模板</button><label>上传V4工作簿（接口预留）</label><input id="templateFile" type="file" accept=".xlsx"><button class="secondary" onclick="uploadTemplate();return false">上传V4工作簿</button><p id="status" class="unit"></p></section>
<section><h3>参数填写</h3><form id="form"></form><button onclick="evaluateDevice();return false">开始判定</button></section>
<section><h3>判定结果</h3><div id="grade" class="grade">尚未判定</div><div id="summary" class="summary"><div><span>采用标准</span><b id="summaryStandard">—</b></div><div><span>参考能效等级</span><b id="summaryReference">—</b></div><div><span>判定说明</span><b id="summaryExplanation">—</b></div><div><span>缺失信息</span><b id="summaryMissing">—</b></div><div><span>数据质量</span><b id="summaryQuality">—</b></div></div><pre id="result"></pre></section></main>
<script>
const $=id=>document.getElementById(id), device=$('device'); let schema=null;
async function getJSON(url,opts){const r=await fetch(url,opts);const d=await r.json();if(!r.ok)throw new Error(d.error||('HTTP '+r.status));return d}
async function init(){const types=await getJSON('/api/device-types');types.forEach(x=>{const o=document.createElement('option');o.value=x.code;o.textContent=x.name;device.append(o)});device.onchange=loadSchema;await loadSchema();try{const s=await getJSON('/api/status');const scopes=s.elimination.scope_options||[];if(scopes.length){const sel=$('scope');sel.innerHTML='';scopes.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;sel.append(o)});sel.value=s.elimination.default_scope||scopes[0]}$('status').textContent=`标准包${s.standard_packs.length}个；淘汰目录已启用${s.elimination.entry_count}/${s.elimination.source_entry_count}条；产业目录${s.elimination.industry_catalog_complete?'完整':'用户条目非全文'}；PMSM状态${(s.standard_packs.find(x=>x.device_type==='motor_pmsm')||{}).status||'未知'}`}catch(e){$('status').textContent=e.message}}
function applyDynamicLimits(){const category=document.querySelector('#form [data-field="category"]')?.value||'';document.querySelectorAll('#form [data-conditional-limits]').forEach(input=>{let rules=[];try{rules=JSON.parse(input.dataset.conditionalLimits||'[]')}catch(_e){return}const match=rules.find(r=>r.when&&r.when.field==='category'&&r.when.equals===category)||rules.find(r=>r.when==='otherwise');if(match){if(match.minimum!==undefined)input.min=match.minimum;if(match.maximum!==undefined)input.max=match.maximum;}})}
async function loadSchema(){schema=await getJSON('/api/schema?device_type='+encodeURIComponent(device.value));const f=$('form');f.innerHTML='';const seenFields=new Set();[...(schema.fields||[]),...(schema.extensions||[])].filter(x=>x.editable!==false).filter(x=>{if(!x.field_id||!seenFields.has(x.field_id)){if(x.field_id)seenFields.add(x.field_id);return true}return false}).forEach(x=>{const w=document.createElement('div');w.className='field';const required=x.required&&x.required!=='可选';const l=document.createElement('label');l.textContent=x.display_name+(x.unit&&x.unit!=='-'?' ('+x.unit+')':'')+(required?' *':'');l.title=x.validation||'';w.append(l);let input;if(x.data_type==='图片'){input=document.createElement('input');input.type='file';input.accept='image/*'}else if(x.enum_values&&x.enum_values.length){input=document.createElement('select');const empty=document.createElement('option');empty.value='';empty.textContent='请选择';input.append(empty);x.enum_values.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;input.append(o)})}else{input=document.createElement('input');input.type=(x.data_type==='数值'||x.data_type==='整数')?'number':'text';if(x.data_type==='数值')input.step='any';if(x.data_type==='整数')input.step='1'}if(x.minimum!==''&&x.minimum!==null&&x.minimum!==undefined)input.min=x.minimum;if(x.maximum!==''&&x.maximum!==null&&x.maximum!==undefined)input.max=x.maximum;if(x.conditional_limits){input.dataset.conditionalLimits=JSON.stringify(x.conditional_limits)}if(required)input.required=true;input.title=x.validation||'';input.dataset.field=x.field_id;if(x.field_id==='category')input.addEventListener('change',applyDynamicLimits);w.append(input);f.append(w)});applyDynamicLimits()}
async function evaluateDevice(){const values={};document.querySelectorAll('#form [data-field]').forEach(x=>{if(x.type==='file'){if(x.files[0])values[x.dataset.field]={name:x.files[0].name,size:x.files[0].size,type:x.files[0].type||'application/octet-stream'}}else if(x.value!=='')values[x.dataset.field]=x.type==='number'&&device.value!=='centrifugal_pump'?Number(x.value):x.value});try{const r=await getJSON('/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_type:device.value,values,as_of:$('asof').value,elimination_scope:$('scope').value})});$('grade').textContent=(schema&&schema.conclusion_field||'能效等级')+'：'+r.conclusion;$('summaryStandard').textContent=(r.standard_reference||{}).standard_code||'—';$('summaryReference').textContent=r.reference_conclusion||'—';$('summaryExplanation').textContent=r.explanation||'—';$('summaryMissing').textContent=(r.missing_fields||[]).join('、')||'无';$('summaryQuality').textContent=(r.data_quality_issues||[]).map(x=>x.message||x.code||'').filter(Boolean).join('；')||'无';$('result').textContent=JSON.stringify(r,null,2)}catch(e){$('grade').textContent='判定失败';$('summaryExplanation').textContent=e.message;$('result').textContent=e.message}}
async function downloadTemplate(){try{const r=await fetch('/api/template');if(!r.ok){let d={};try{d=await r.json()}catch(_e){}throw new Error(d.error||'下载失败')}const blob=await r.blob();const href=URL.createObjectURL(blob);const a=document.createElement('a');a.href=href;a.download='设备能效分析空白模板_重构版V4.xlsx';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1000);$('status').textContent='模板已下载'}catch(e){$('status').textContent=e.message}}
async function uploadTemplate(){const f=$('templateFile').files[0];if(!f){$('status').textContent='请先选择.xlsx文件';return}try{const result=await getJSON('/api/template/upload',{method:'POST',headers:{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','X-Filename':encodeURIComponent(f.name)},body:await f.arrayBuffer()});$('status').textContent=result.message||'上传接口已接收'}catch(e){$('status').textContent=e.message}}
init().catch(e=>{$('result').textContent=e.message});
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    server: "_ApiServer"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # 保持CLI启动输出干净；宿主应用可自行配置HTTP日志。
        return

    def _send(self, status: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._send(status, _json_bytes({"error": message}))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send(HTTPStatus.OK, INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        try:
            if parsed.path == "/api/device-types":
                payload = self.server.api.device_types()
            elif parsed.path == "/api/status":
                payload = self.server.api.status()
            elif parsed.path == "/api/schema":
                query = urllib.parse.parse_qs(parsed.query)
                device_type = query.get("device_type", [""])[0]
                if not device_type:
                    raise ApiRequestError("缺少device_type")
                payload = self.server.api.schema(device_type)
            elif parsed.path == "/api/template":
                transfer = self.server.template_transfer
                if transfer.download is None:
                    # 模板下载仍是独立端口；这里返回说明，避免Web层直接依赖Excel库。
                    self._send(HTTPStatus.NOT_IMPLEMENTED, _json_bytes({"error": "模板下载接口已预留，请由宿主适配器提供文件响应"}))
                    return
                filename, content = transfer.download()
                if not isinstance(content, bytes):
                    raise ValueError("模板下载适配器必须返回bytes")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", XLSX_CONTENT_TYPE)
                self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{urllib.parse.quote(str(filename))}")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self._error(HTTPStatus.NOT_FOUND, "路径不存在")
                return
            self._send(HTTPStatus.OK, _json_bytes(payload))
        except (ApiRequestError, ValueError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/template/upload":
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._error(HTTPStatus.BAD_REQUEST, "Content-Length无效")
                return
            if length <= 0 or length > MAX_UPLOAD_BYTES:
                self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "上传文件为空或超过50MiB限制")
                return
            content = self.rfile.read(length)
            transfer = self.server.template_transfer
            if transfer.upload is None:
                # Excel读写属于独立适配器；本阶段只确认接口可达，不保存或解析文件。
                self._send(HTTPStatus.NOT_IMPLEMENTED, _json_bytes({"error": "V4工作簿上传接口已预留，请由Excel适配器接入"}))
                return
            filename = urllib.parse.unquote(self.headers.get("X-Filename", "上传工作簿.xlsx"))
            result = transfer.upload(filename, content)
            self._send(HTTPStatus.OK, _json_bytes(result if result is not None else {"uploaded": True, "filename": filename}))
            return
        if path not in {"/api/evaluate", "/api/evaluate-batch"}:
            self._error(HTTPStatus.NOT_FOUND, "路径不存在")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._error(HTTPStatus.BAD_REQUEST, "Content-Length无效")
            return
        if length <= 0 or length > MAX_JSON_BODY_BYTES:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "请求体为空或超过4MiB限制")
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ApiRequestError("判定请求必须是对象")
            if path == "/api/evaluate-batch":
                result = self.server.api.evaluate_batch(payload)
            else:
                result = self.server.api.evaluate(payload)
            self._send(HTTPStatus.OK, _json_bytes(result))
        except (UnicodeDecodeError, json.JSONDecodeError, ApiRequestError, ValueError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))


class _ApiServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], api: ApplicationApi, template_transfer: TemplateTransferPort | None = None):
        self.api = api
        self.template_transfer = template_transfer or TemplateTransferPort()
        super().__init__(address, _Handler)


def create_server(
    api: ApplicationApi,
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    template_transfer: TemplateTransferPort | None = None,
) -> ThreadingHTTPServer:
    """创建可嵌入宿主程序的Web API服务器；调用者负责serve_forever/shutdown。"""

    return _ApiServer((host, int(port)), api, template_transfer)


def run_web(
    api: ApplicationApi,
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    open_browser: bool = False,
    template_transfer: TemplateTransferPort | None = None,
) -> None:
    server = create_server(api, host, port, template_transfer=template_transfer)
    url = f"http://{host}:{server.server_port}/"
    print(f"设备能效Web窗口：{url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    finally:
        server.server_close()
