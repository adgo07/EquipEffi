"""Read-only inventory of acceptance inputs. Does not save source workbooks."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
owners = {
 'gb18613_2020':'01a1332a-43b0-7c52-85f5-c77a65cb8859',
 'gb30254_2024':'01a1332a-6226-7d73-b5a9-202f6b632183',
 'gb30253_2024':'01a1332a-76c9-7e52-a6a5-ff3e509c5214',
 'gb19153_2019':'01a1332a-9377-7211-a591-898516ec7866',
 'gb24500_2020':'01a1332a-baa5-70d0-bec6-6da564a0bf0c',
 'gb29541_2013':'01a1332a-e003-7df3-b453-963510f843d8',
 'gb19761_2020':'01a13341-d23a-7340-b498-573ebe7b84a0',
 'gb28381_2012':'01a13341-ede0-7c01-94c9-d8ddcecd0f26',
 'gb28381_2026':'01a13342-0a50-7e42-8104-70665a4c5d35',
 'gb32030_2022':'01a13342-2805-7ba3-881c-e7899f66cee5',
 'gbt36561_2018':'01a13342-438a-7001-820e-ff5f2fbfc969',
 'gb19577_2024':'01a13342-5fb3-73d2-a1d2-c7b00360a341',
 'gb37479_2019':'01a13342-783c-74c0-9590-c9b161326ad1',
 'gb19576_2019':'01a13342-972e-7892-b0bd-357b7cf9d867',
 'gb21454_2021':'01a13342-adc3-7b12-b386-b5551c4bd43c',
 'gb19762_2025':None, 'gb20052_v21':None,
}
def git(*args):
 return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf-8').strip()
def entry(p):
 data=p.read_bytes()
 return {'absolute_path':str(p),'relative_path':p.relative_to(ROOT).as_posix(),
         'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
         'modified_bjt':datetime.fromtimestamp(p.stat().st_mtime,timezone(timedelta(hours=8))).isoformat()}
standards=[]
for key,owner in owners.items():
 directory=ROOT/'docs/standards'/key
 mapping=list(directory.glob('*映射*.md')) if key=='gb20052_v21' else [directory/'STANDARD_MAPPING.md']
 mapping += list((directory/'profiles').glob('*.md')) if (directory/'profiles').exists() else []
 workbooks=[p for p in directory.rglob('*.xlsx') if not any(x in p.parts for x in ('tmp','node_modules','preview'))]
 identifier='20052' if key=='gb20052_v21' else key.split('_')[0].lstrip('gbt')
 year='2024' if key=='gb20052_v21' else key.split('_')[1]
 pdfs=[p for p in (ROOT/'标准原文').glob('*.pdf') if identifier in p.name and year in p.name]
 standards.append({'key':key,'directory':str(directory),'author_thread_id':owner,
  'author_id_evidence':'docs/governance/SIX_STANDARD_MAPPING_COORDINATION_20261013.md' if owner else 'UNCONFIRMED',
  'mapping_files':[entry(p) for p in mapping], 'workbooks':[entry(p) for p in workbooks],
  'source_pdfs':[entry(p) for p in pdfs], 'acceptance':'PENDING_INDEPENDENT_FULL_REVIEW',
  'provenance': 'PR #21 merged f12b5f2; archived entry PR #22' if key=='gb20052_v21' else ('archive PR #22 merged 2c7807f' if key=='gb19762_2025' else 'uncommitted working files on codex/six-standard-mappings; no open PR returned by connector')})
result={'inventory_bjt':datetime.now(timezone(timedelta(hours=8))).isoformat(),
 'requested_scope_bjt':'2026-10-13','repository':git('remote','get-url','origin'),
 'root':str(ROOT),'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),
 'tracked_remote_master':git('rev-parse','origin/master'),
 'fetch':'FAILED: FETCH_HEAD denied in sandbox, approved retry failed TLS unexpected EOF',
 'thread_tools':'list_threads and read_thread both returned Codex app MCP request failed; no private-store workaround used',
 'model_evidence':'spawn_agent accepted gpt-6-astra with reasoning_effort=medium; no low-level model telemetry returned',
 'locked_central_sha':'ee5feb0cc34dbd99790500fadd0c4c932e202a20',
 'central_guides_read_at_local_origin_main':'854b544563260f9e79c73e714c85f6589e0f19b3',
 'standards':standards}
(OUT/'preflight_inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 设备类今日映射表清单与定位限制', '',
 '清单时间：'+result['inventory_bjt']+'。范围日：北京时间2026-10-13。',
 '本文件仅固定验收对象与来源，不是标准内容PASS报告；逐文件SHA和完整绝对路径见同目录preflight_inventory.json。',
 '', '## 平台预检查', '',
 '- 仓库身份：'+result['repository']+'；HEAD：'+result['head']+'。',
 '- 分支：'+result['branch']+'；15项新编映射主要未提交，不能只用HEAD复现。',
 '- fetch第一次受FETCH_HEAD写权限限制；已批准重试，但TLS EOF失败。远端新鲜度未确认。',
 '- 本地master比现有origin/master落后46提交；未切换、合并、提交、发布。',
 '- locked central SHA：'+result['locked_central_sha']+'；本任务不涉及中央公共 Contract。',
 '- 中央clone已核origin；读取本地origin/main '+result['central_guides_read_at_local_origin_main']+' 的GUIDE_INDEX、Standard Development Guide、Product Delivery Policy；中央远端最新性未刷新确认。',
 '- MUST：逐项标准定位、疑点登记、结构/数值分别留痕、事实/技术判断/软件决定区分；MUST NOT：静默修标准、修改冻结双文件/业务代码、自动提升支持状态。',
 '- 模型配置：子任务启动工具接受gpt-6-astra/medium；底层运行遥测不可见。',
 '- 会话定位：list_threads与read_thread均MCP失败；下列15个ID来自仓库协调记录，未冒称正文核实。',
 '- .agents目录实际不存在；无该目录技能可读。使用可用PDF/Spreadsheets技能进行只读验收。',
 '', '## 完整版本清单', '', '|标准目录|原编制会话|主映射 / 配套工作簿 / 源PDF|', '|---|---|---|']
for s in standards:
 paths=[x['relative_path'] for k in ('mapping_files','workbooks','source_pdfs') for x in s[k]]
 lines.append('|'+s['key']+'|'+(s['author_thread_id'] or '待定位；会话工具失败')+'|'+'<br>'.join(paths)+'|')
lines += ['', '共17个标准版本；泵含共同映射和两个Profile分支。变压器gb20052_2024入口指向gb20052_v21双文件，不重复计数。',
 '', '## 现存证据边界', '',
 '较早ACCEPTANCE_REPORT仅十套资料729位置抽样，不代表本次完整通过。15项新编原文、泵原文、变压器原文均已定位。本轮逐表结论由Astra独立验收组另行报告。变压器温度换算保持DEFERRED，发现问题仅出示证据，不修改批准决定。',
 'GitHub连接器查询本仓open PR返回空列表（查询时点）；今日PR #21/#22合并由Git历史确认。Knowledge capture：无。']
(OUT/'PREFLIGHT_INVENTORY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({'standards':len(standards),'mappings':sum(len(s['mapping_files']) for s in standards),'workbooks':sum(len(s['workbooks']) for s in standards),'pdfs':sum(len(s['source_pdfs']) for s in standards),'output':str(OUT)},ensure_ascii=False))
