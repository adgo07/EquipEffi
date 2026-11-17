"""PR46复核：历史独立逐格证据回读、固定边界和受保护资产；不改源。"""
from pathlib import Path
from fractions import Fraction
from hashlib import sha256
import csv
import json
import subprocess
import sys
from equipeffi.infrastructure.standards.compressor_repository import load_compressor_pack
from equipeffi.domain.devices.compressor.calculator import Gb19153CompressorCalculator

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

def main():
    pack, raw_hash = load_compressor_pack()
    evidence_path=ROOT/'docs/governance/device_full_acceptance_20261013/compressor_boiler/independent_cells.csv'
    with evidence_path.open(encoding='utf-8-sig',newline='') as stream:
        evidence=[r for r in csv.DictReader(stream) if r['standard']=='GB19153-2019' and r['table'] in {'1','2','3','4','5','6'}]
    expected={f"{r['sheet']}!{r['cell']}":r for r in evidence}
    assert len(expected)==len(evidence)==2919
    actual=[r for t in pack['tables'] for r in t['rows']]
    assert len(actual)==2919
    for item in actual:
        source=expected[item['source_cell']]
        assert source['result']=='PASS'
        if source['source']=='—': assert item['value'] is None
        else: assert Fraction(item['value'])==Fraction(source['source'])
    calc=Gb19153CompressorCalculator()
    # 独立设计候选及其邻点；期望不从待测运行包计算。
    cases=[
      ('oil_injected_rotary','1.5','0.3','AIR','5.8','1级'),
      ('oil_injected_rotary','1.5','0.3','AIR','5.800000000000000000000001','2级'),
      ('oil_injected_rotary','1.5','0.3','AIR','6.5','2级'),
      ('oil_injected_rotary','1.5','0.3','AIR','7.4','3级'),
      ('oil_injected_rotary','1.5','0.3','AIR','7.401','未达3级'),
      ('oil_injected_rotary','1.5','0.3','LIQUID','5.8','无法判定'),
      ('oil_injected_rotary','1.5','0.25','AIR','5.8','无法判定'),
      ('oil_injected_rotary','1.5','1.3','AIR','5.8','无法判定'),
      ('oil_injected_rotary','1.49','0.3','AIR','5.8','不在范围'),
      ('variable_speed_oil_injected_rotary','2.2','0.3','AIR','6.1','1级'),
      ('reciprocating','2.2','0.25','AIR','6.9','3级'),
      ('reciprocating','2.2','0.25','LIQUID','6.9','无法判定'),
      ('oil_free_reciprocating','18.5','0.7','LIQUID','6.7','1级'),
      ('portable_lubricated','0.25','0.2',None,'5.2','1级'),
      ('portable_oil_free','0.25','0.2',None,'5.5','1级'),
    ]
    for category,p,q,c,e,conclusion in cases:
        values=dict(category_id=category,rated_discharge_pressure_mpa=q,specific_power_kw_per_m3_min=e)
        values['rated_input_power_kw' if category.startswith('portable_') else 'rated_motor_output_power_kw']=p
        if c is not None: values['cooling_method']=c
        assert calc.evaluate(values,pack).ui_conclusion==conclusion,(category,p,q,c,e)
    prior=json.loads((HERE/'IMPLEMENTATION_VERIFICATION_20261112.json').read_text(encoding='utf-8'))
    for item in prior['evidence_files']:
        path=HERE/'evidence-implementation-20261112'/item['filename']
        assert sha256(path.read_bytes()).hexdigest()==item['sha256'],path
    unchanged=['platform-lock.json','docs/standards/gb19153_2019/data',
               'src/equipeffi/infrastructure/persistence/records_migrations.py',
               'src/equipeffi/infrastructure/persistence/migrations.py','specs/equipment_efficiency/golden']
    for path in unchanged: assert (ROOT/path).exists(),path
    changes=subprocess.check_output(['git','diff','--name-only','35b19815','987e9562','--',*unchanged],cwd=ROOT,text=True).strip()
    assert not changes,changes
    result=dict(date='2026-11-17',reviewed_head='987e9562e8eba448ebce4a477ed67c6295c96075',
       source_identity_comparisons=dict(pass_count=2919,fail=0,error=0,skip=0),
       independent_fixed_cases=dict(pass_count=len(cases),fail=0,error=0,skip=0),
       inherited_evidence_files_hash_verified=len(prior['evidence_files']),
       local_python=sys.version,candidate_file_sha256=raw_hash,evidence_csv_sha256=sha256(evidence_path.read_bytes()).hexdigest(),
       protected_paths=unchanged,protected_diff='EMPTY',
       original_pdf_reaudit='NOT_RUN; reused prior independent original-page transcription',
       replay_scope='2919 source cells, 15 fixed cases and 27 inherited evidence-file hashes only',
       historical_observations='Test rounds and EXE observations below are recorded constants, not executed or reverified by this script; EXE identity has one repository delivery source, not independent build evidence',
       local_test_rounds=[dict(tests=27,seconds=125.691,fail=0,error=0,skip=0,exit_code=0,scope='core/product/architecture before UI wording fix'),
                          dict(tests=15,seconds=40.301,fail=0,error=0,skip=0,exit_code=0,scope='compressor product and motor flow after wording fix')],
       native_exe_sha256='a8b238af4e1eadf587f7da5868a5d9112eff9664029f85c11ed44031d4e5a3a4',
       native_observed='hash matches; isolated launch and accessible home-page tree observed',
       native_interaction='NOT_COMPLETED: capture timed out; click coordinate input geometry unavailable; no successful business input claimed',
       excel_wps_native='NOT_RUN',clean_windows='NOT_RUN',dpi_125='NOT_RUN',
       ci_url='https://github.com/adgo07/EquipEffi/actions/runs/44053395900',
       ci_status='See final acceptance record and live checks; not asserted by this verifier',
       formal_support_promoted=False,release_created=False,phase8_changed=False)
    (HERE/'REVIEW_VERIFICATION_20261117.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_cells':2919,'fixed_cases':len(cases),'evidence_files':len(prior['evidence_files'])}))

if __name__=='__main__': main()
