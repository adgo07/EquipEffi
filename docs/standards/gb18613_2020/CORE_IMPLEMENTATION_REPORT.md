# GB 18613 电机内核实施记录

2026-10-25。Stage C内核实现；不代表产品接通或SUPPORTED。

Owner授权设计收口后实施，效率1～100%为软件防呆，不改变映射。设计基线`e5aa673c1add75fdddb71360f11437a3d543f8b6`；产品基线`2adcef7eba2ff2930f2f5a237028558747cc5b97`。QA-MOTOR-001先登记后实现。

平台预检查：locked central SHA `ee5feb0cc34dbd99790500fadd0c4c932e202a20`；适用Architecture V2.1、Numeric Contract v1、Numeric Profiles v1及Conformance Vector v1。MUST保持Domain与UI/Excel/SQLite独立、十进制输入、全值比较、Profile及来源追溯；MUST NOT把二进制浮点或显示舍入用于正式判级、复制泵专用配置为平台默认、改历史快照。采用精确整数尺度/有理数为ALLOWED PROJECT DIFFERENCE；无需改中央Contract或锁。Standard Issues 001—005、007—008沿用已解决决定；006保持已批准的非阻断PROVISIONAL，不改变解释。

本次新增六类别共享输入契约、六表Calculator、从A.1源表单向派生的新运行包、Numeric Profile和Conformance向量。新包108功率行/1182限值格，其中1149数值、32横杠、1空白；原空白仍区别于横杠并按既有决定保留无指标语义。直接查表沿源精度，插值精确分数比较、仅显示两位小数；0.14kW四极二级限值2143/30%，输入71.43%仍为3级。表1最终315～1000kW区间不被误当成插值禁区，250～315kW以315为右端点。

验证：输入契约/Calculator/数值Conformance共20项通过（FAIL=0、ERROR=0、SKIP=0）；10条Conformance向量通过locked Common Core schema验证。主会话独立将新包与源工作簿比较1290格（108功率+1182限值），全部一致；未重新进行PDF逐格审计。builder重复生成成功，内容完整性SHA256为`506DDAD282F09F89CD5F467E34DC552010FABA41714F1AAB5B4DCBBDA0391A85`。正式业务标准源和已批准Golden未变。

Qt/Excel、历史、旧链退出与发布资源接通属于后一产品提交；本内核提交不替代其验证。原生包、WPS交互、干净Windows验收在本提交为NOT_RUN；不修改数据库、当前发布或支持状态。Knowledge capture：无。
