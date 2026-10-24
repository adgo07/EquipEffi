from pathlib import Path
import re,json
O=Path('docs/governance/device_round3_review_20261013/fans_submersible');root=Path('STANDARD_ISSUES_REGISTER.md').read_text(encoding='utf8')
sets=[('gb19761_2020','GB19761',range(1,4)),('gb28381_2012','GB28381',range(7,13)),('gb28381_2026','GB28381',range(1,7)),('gb32030_2022','GB32030',range(1,2)),('gbt36561_2018','GBT36561',range(1,12))]
choices={
'GB19761-001':'决定同时双吸/暖通/进气箱时逐项累计、按组互斥或专用优先；建议保留单项原值，组合无批准不造阈值。',
'GB19761-002':'决定带扩散筒固定末行适用范围、无筒+2所基于行及动叶可调/可逆转优先级；备选固定基准或自身行，不能默认任选。',
'GB19761-003':'决定5.3总句“机组效率”与各分项ηr的优先解释；建议依具体表1～3ηr/表4ηe区分，但尚非批准。',
'GB28381-007':'决定直径300/801及连续比值空档路由：未规定返回待确认、经有源规则补端点或取整；禁止无证据插值。',
'GB28381-008':'决定提高5%/增加1%为相对或百分点，以及多级先修正后均值/先均值；建议逐项留原句。',
'GB28381-009':'决定“悬臂式单级双支撑”术语对应设备，不凭经验删词或扩范围；需JB/T2977等。',
'GB28381-010':'取得引用版本及低高速分类/最高多变效率工况、压力基准；用有效报告已明确身份或等待全文，不自造rpm边界。原文“转数”宜保留。',
'GB28381-011':'原印kJ/kW量纲疑误：备选按功比同尺度使用、或可信依据确定kJ/kg等；不能静改原文单位。',
'GB28381-012':'非单调/非固定差值是否需要发布方勘误？建议按原值保留（含表4 H18=73），只有证据后才改真值。',
'GB28381-001':'决定式1与GB/T25630的语义/适用条件；不采信第三方把htot当等熵头来证明近似正确。保留原等式，优先有效试验报告效率；是否从指数自主计算须有源核实。',
'GB28381-002':'决定统一J/kg+W或kJ/kg+kW及换算位置；原R为J单位而hpol标kJ、Ptot为kW事实保留。可实施换算不等于原文无不一致；是否改技术判断/类型由Owner定。',
'GB28381-003':'决定偏差减数顺序、相对或百分点、≤−2%的业务含义；备选保留字面/仅引用合格报告/取得官方解释，不擅改≥或绝对值。',
'GB28381-004':'决定大写P1/P2定义、单位/绝对压及理想等温项与实测输入功等号；若kPa则×1000得到J/m³，而左侧kW/(m³/s)为kJ/m³，未指定压力单位前不宣布错或无错。',
'GB28381-005':'决定表6浮动有效区、表4/5端部缺值的缺端点策略：建议四角缺任一不出阈值，不跨缺值补点；是否单独编号由协调定，既有005不算零登记。',
'GB28381-006':'决定全精度比较或示例显示值传递、最终舍入精度/模式；示例A2高端基点与低端权重代数一致，213.8可由显示212.2/218.4得213.75，禁止重引已撤回权重矛盾。',
'GB32030-001':'分别决定可信来源/日期差异、未注日期引用采用版本与追溯、缺GB/T2818/7021全文、外部ηDB/ηgr/容差/试验参数；S01未认证表7负5%与主表减Δη符号衔接须核实，备选有符号或幅值不得自动abs。绝对效率依赖未齐不等于主标准表达式转录错。',
'GBT36561-001':'7.2引表9但表9是燃料系数，备选表8或另有逻辑；待可信解释，不自动改表号。',
'GBT36561-002':'586 vs1400 kcal/m³及燃料油体积量纲待核：备选586原印、5861/5862等推测不得选定；影响燃料分支/系数。',
'GBT36561-003':'决定Soi/Sxi、Ki基准/等级分、单位能耗无三等、壳门多值合并；备选原达等级分或标准限值比，需完整评分口径。',
'GBT36561-004':'退火≥10与≥20重叠，决定最高满足档优先或给中档上界；不默加<20。',
'GBT36561-005':'A8/A11在500℃缺口：归低/归高/不评价待确认；不借A10≥500替代。',
'GBT36561-006':'决定通式乘积与A9加法的采用关系、K2/K3缺值、气氛发生器总能量边界；备选依专用式或统一式需证据，禁止默认系数1。',
'GBT36561-007':'决定重复序号、共用2分不重复计、引用GB/T27946及GB/T15735前缀、完全缺项零分母处理；分层记录结构事实与软件状态选择。',
'GBT36561-008':'决定相邻容积共享端点与表A4≤0.2～0.07逆序区间；备选符号化区间解释或待确认，不让通用解析器擅定。',
'GBT36561-009':'空炉损失比温度系数修正实测值或表指标？两者会反向影响结论，需Owner确定，不任选。',
'GBT36561-010':'光亮淬火无渗层K8分支，备选不适用因子1或缺依据待确认；原文没有自动1。',
'GBT36561-011':'表15 30829.4与2章/7.3/7.5 30839.4冲突：保留双事实，正式采用哪份需引用全文/可信勘误；本轮仅修转录，未获解释批准。'}
rows=[]
for st,p,ns in sets:
 for n in ns:
  short=f'{p}-{n:03}';id='EQP-STD-'+short;m=re.search(r'^### '+id+r'[^\n]*\n(.*?)(?=^### |\Z)',root,re.M|re.S);body=m.group(1);fields={}
  for line in body.splitlines():
   if line.startswith('|'):
    x=line.split('|')
    if len(x)>=4:fields[x[1]]=x[2]
  facts=[(k,v) for k,v in fields.items() if any(z in k for z in ['原文','定位','来源'])]
  rows.append({'standard':st,'existing_issue_id':id,'source_excerpt_and_location':facts,'root_record':fields,'question_and_options_recommendation':choices[short],'impact':next((v for k,v in fields.items() if '技术判断' in k),'见原记录及建议'),'evidence_strength':'本机主PDF原页已核；涉及外部引用/发布方解释部分未认证；不等于标准被证实错误','approval_status':'OPEN；未见Owner批准正式软件解释','owner_required':True,'priority':'P1','priority_reason':'正式实施前会影响适用、阈值、计算或评分；不意味着Stage A必须先解决'})
new=[{'candidate_id':'NEW-2012-SCOPE','existing_issue_id':None,'standard':'gb28381_2012','source_excerpt_and_location':'PDF3§1括注高速；PDF4/6表1/5标题含低速双进气单侧叶轮','question_and_options_recommendation':'正文范围窄读或表标题涵盖低速？建议先登记AMBIGUITY而不扩范围；协调分新号，勿照第三方冲突014','impact':'影响设备是否适用','evidence_strength':'原图直接确认','approval_status':'未批准','priority':'P1'},
{'candidate_id':'NEW-CROSS-EFFICIENCY','existing_issue_id':None,'standard':'gb28381_2012/2026','source_excerpt_and_location':'2012 PDF4§5.3.1/6§5.4.1 使用范围最高；2026 PDF20§7.1规定工况','question_and_options_recommendation':'不同版本测量点证据能否复用？建议默认按所选版试验口径，报告足以证明两者时另定，不泛称永不可折算','impact':'同名效率输入不可无条件复用','evidence_strength':'两原文直接；复用政策为软件选择','approval_status':'未批准','priority':'P1'},
{'candidate_id':'NEW-CROSS-INTERPOLATION','existing_issue_id':None,'standard':'gb19761_2020/gb28381_2026','source_excerpt_and_location':'19761无授权表内插值；28381-2026 PDF7第5章明确未列值插值','question_and_options_recommendation':'是否仅为2026建立插值策略；19761按离散档，不共用未经授权插值','impact':'跨标准共用算法会产生新阈值','evidence_strength':'原文有/无条文区别，非标准冲突','approval_status':'未批准','priority':'P1'},
{'candidate_id':'NEW-MULTISTAGE-ROOTS','existing_issue_id':None,'standard':'gb28381_2012/2026','source_excerpt_and_location':'2012适用离心；2026§1明确单级罗茨','question_and_options_recommendation':'多级罗茨应找其他适用标准或返回未支持，不能沿单级阈值；不据本组资料断言全球无标准','impact':'真实设备超出本组已证明适用范围','evidence_strength':'本组范围已核，全部行业标准未穷尽','approval_status':'未批准','priority':'P1'}]
(O/'owner_questions.json').write_text(json.dumps({'existing':rows,'additional_candidates':new,'coverage':{'existing_count':len(rows),'additional_count':len(new),'all_existing_issue_ids_unique':len(set(x['existing_issue_id'] for x in rows))==27}},ensure_ascii=False,indent=2),encoding='utf8')
lines=['# 五标准全部已登记未决口径与新增候选','', '27条根Issue全部覆盖，另4条候选。P1意为正式实现前需明确会影响业务的选择，非强迫Stage A关闭。所有建议均未批准；疑似标准错误一律留Owner。来源原页沿首轮全页阅读与本轮定向原图复读，外部标准未认证。','']
for x in rows:
 lines+=['## '+x['existing_issue_id']+' / '+x['standard'],'','原文与定位：'+str(x['source_excerpt_and_location']),'','疑点与影响：'+x['impact'],'','Owner需判、备选及建议：'+x['question_and_options_recommendation'],'','证据/批准：'+x['evidence_strength']+'；'+x['approval_status'],'']
for x in new:lines+=['## '+x['candidate_id']+'（尚无根ID）','',x['source_excerpt_and_location'],'',x['question_and_options_recommendation'],'',x['impact']+'；'+x['evidence_strength']+'；'+x['approval_status'],'']
(O/'OWNER_QUESTIONS.md').write_text('\n'.join(lines),encoding='utf8');print('owner existing',len(rows),'new',len(new))
