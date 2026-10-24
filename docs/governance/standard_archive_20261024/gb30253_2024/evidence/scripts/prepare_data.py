import json,re,csv,ast,hashlib,collections
from pathlib import Path
import pdfplumber
ROOT=Path(__file__).resolve().parents[2]
T=json.loads((ROOT/'tmp/tables.json').read_text(encoding='utf8'))
M={ast.literal_eval(k):{int(c):v for c,v in m.items()} for k,m in json.loads((ROOT/'tmp/font_maps.json').read_text(encoding='utf8')).items()}
SRC=ROOT.parents[2]/'标准原文/4. GB 30253-2024 永磁同步电动机能效限定值及能效等级.pdf'
doc=pdfplumber.open(SRC)
cool=['IC81W、IC86W、IC71W(IC3W7)','IC411、IC416','IC511、IC611、IC616、IC516、IC666']
lv=['>1800～6000','>1200～1800','>900～1200','>600～900',500,375,300,250,200,150,100,75,60,45]
hv=[3000,1500,1000,750,600,500,375,300,250,200,150,100,75,60,45]
lift=['>750','>400～750','>250～400','>180～250','>140～180','>100～140','≤100']
routes={}
for no in range(1,30):
    kind='异步起动' if no<=7 else '变频调速' if no<=28 else '电梯用'
    voltage='≤1140 V' if no in [1,8,9,10,29] else '3 kV(3.3 kV)、6 kV' if 2<=no<=4 or 11<=no<=19 else '10 kV'
    cooling='未按冷却方法分表' if no in [1,8,9,10,29] else cool[(no-2)%3] if no<=7 else cool[((no-11)%9)//3]
    grades=[1,2,3] if no<=7 or no==29 else [(no-8)%3+1]
    axes=[2,4,6,8,10,12,16] if no==1 else [4,6,8,10,12] if no<=7 else lv if no<=10 else hv if no<=28 else lift
    routes[no]={'no':no,'sheet':f'表{no:02d}','kind':kind,'voltage':voltage,'cooling':cooling,'grades':grades,'axes':axes,'rows':[]}
parts={7:[1],8:[1,2],9:[2],10:[3],11:[4],12:[5],13:[6],14:[7],15:[8],16:[8,9],17:[9],18:[9,10],19:[10],20:[10,11],21:[11],22:[12],23:[12,13],24:[13],25:[13,14],26:[14],27:[15],28:[15,16],29:[16],30:[16,17],31:[17],32:[18],33:[18,19],34:[19],35:[19,20],36:[20],37:[21],38:[21,22],39:[22],40:[22,23],41:[23],42:[24],43:[24,25],44:[25],45:[25,26],46:[26],47:[27],48:[27,28],49:[28],50:[28,29],51:[29]}
def col(n):
    s=''
    while n: n,a=divmod(n-1,26);s=chr(65+a)+s
    return s
def decode_char(c):
    code={'’':39,'‘':96,'“':170,'”':186}.get(c['text'],ord(c['text']) if len(c['text'])==1 else -1)
    return M.get((c['page_number'],c['fontname']),{}).get(code) or c['text']
audit=[]; flat=[]; rowaudit=[]
for t in T:
    no=parts[t['page']][t['part']-1]; route=routes[no]
    skip=3 if no<=7 else 4 if no==29 else 2
    for ri,vals in enumerate(t['rows'][skip:],skip+1):
        raw=vals[0]
        if raw in ['400!1000']: power='400～1000'
        elif raw in ['315!1250','3151250!']: power='315～1250'
        elif raw=='"3150': power='≥3150'
        else: assert re.fullmatch(r'\d+(?:\.\d+)?',raw),raw;power=float(raw)
        rowno=len(route['rows'])+7
        row={'power':power,'values':[],'page':t['page'],'printed':t['page']-4,'source_row':ri,'part':t['part']}
        assert len(vals)-1==len(route['grades'])*len(route['axes'])
        rowaudit.append([no,route['sheet'],f'A{rowno}',power,t['page'],t['page']-4,t['part'],ri,raw])
        for ci,v in enumerate(vals[1:],1):
            assert v=='#' or re.fullmatch(r'\d+\.\d',v),(no,ri,ci,v)
            actual='—' if v=='#' else float(v)
            row['values'].append(actual)
            x0,y0,x1,y1=t['boxes'][ri-1][ci]
            # second read from unrotated original page; coordinate transform 90deg
            op=doc.pages[t['page']-1]; box=[y0,op.height-x1,y1,op.height-x0]
            chars=[c for c in op.chars if box[0]<=(c['x0']+c['x1'])/2<box[2] and box[1]<=(c['top']+c['bottom'])/2<box[3]]
            chars.sort(key=lambda c:-c['top'])
            reread=''.join(decode_char(c) for c in chars)
            assert reread==v,(no,ri,ci,v,reread)
            grade=route['grades'][(ci-1)//len(route['axes'])];axis=route['axes'][(ci-1)%len(route['axes'])]
            note='R1：原文0.0，需确认，不得自动用于判级' if no==1 and power==55 and grade==2 and axis==12 else ''
            audit.append([no,route['sheet'],f'{col(ci+1)}{rowno}',power,grade,axis,actual,t['page'],t['page']-4,t['part'],ri,ci+1,*[round(x,3) for x in box],v,reread,'MATCH',note])
            flat.append([no,route['kind'],route['voltage'],route['cooling'],power,grade,axis,'极' if no<=7 else 'r/min',actual,'%',route['sheet'],f'{col(ci+1)}{rowno}',t['page'],t['page']-4,note])
        route['rows'].append(row)
for no,r in routes.items():
    expected=27 if no==1 else 21 if no<=7 else 28 if no<=10 else 25 if no<=28 else 20
    assert len(r['rows'])==expected,(no,len(r['rows']))
    assert len(set(str(x['power']) for x in r['rows']))==expected
for folder in ['data','evidence']:(ROOT/folder).mkdir(exist_ok=True)
def csvwrite(path,headers,rows):
    with (ROOT/path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(rows)
csvwrite('evidence/cell_audit.csv',['table','sheet','cell','power_kW','grade','axis','source_value','pdf_page','printed_page','page_table_part','source_row','source_col','original_x0','original_top','original_x1','original_bottom','rotated_read','original_read','comparison','issue_request'],audit)
csvwrite('evidence/row_audit.csv',['table','sheet','power_cell','power_kW','pdf_page','printed_page','part','source_row','extracted_power_text'],rowaudit)
csvwrite('data/table_values.csv',['table','motor_kind','voltage','cooling','rated_power_kW','grade','pole_or_speed','axis_unit','efficiency','efficiency_unit','sheet','cell','pdf_page','printed_page','issue_request'],flat)
(ROOT/'tmp/workbook_data.json').write_text(json.dumps(list(routes.values()),ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'tables':len(routes),'rows':len(rowaudit),'value_positions':len(audit),'numeric':sum(isinstance(x[6],float) for x in audit),'dashes':sum(x[6]=='—' for x in audit),'mismatches':0},ensure_ascii=False))
