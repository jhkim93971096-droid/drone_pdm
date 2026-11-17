"""드론 위험 분석과 제출물 생성. 기본 동작은 읽기 전용 목록 조회."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import joblib
import pandas as pd

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
import pdm_lib as lib
from scripts.app_data import score_current_month
from scripts.operations import build_evidence
COMMAND='python .agents/skills/pdm-risk/scripts/score.py'
TEST_PATH=ROOT/'reports/test_predictions_2025.csv'
PLAN_PATH=ROOT/'reports/2026-01_재점검계획.md'
ANALYSIS_PATH=ROOT/'reports/08_analysis.md'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def bundle(): return joblib.load(lib.TRAINING_PATH)


def test_predictions(b):
    frame=lib.prepare_data()['test']
    raw=pd.read_csv(lib.TEST_CSV,encoding='utf-8-sig')
    assert len(frame)==len(raw)
    output=pd.DataFrame({'equipment_id':raw.equipment_id,'maintenance_date':frame.maintenance_date.dt.strftime('%Y-%m-%d'),'prob':b['model'].predict_proba(frame[lib.FEATURES])[:,1]})
    assert output.prob.between(0,1).all()
    return output


def recommendation(row):
    if row['status']=='예방 점검': return '예방 점검 배정 후 최근 정비 결과·운용 전 상태 확인'
    action={'배터리':'배터리·전원 연결','모터':'모터·추진부','통신':'통신 연결·설정','기체':'기체 손상·체결','센서':'센서 상태·설정'}.get(row['fault_category'],'정비 기록·운용 전 상태')
    if row['overflow']: return action+' 재확인 필요성을 알리고 담당자에게 추가 용량·시기 판단 요청'
    return action+' 및 최근 정비 조치 결과 재확인'


def score_facts():
    scored,card,policy=score_current_month(bundle())
    rows=[]
    for _,item in scored.iterrows():
        row={k:item[k] for k in ['equipment_id','equipment_type','unit_code','fault_category','reasons','status']}
        row.update({'rank':int(item['rank']),'prob':float(item['prob']),'maintenance_date':item.maintenance_date.strftime('%Y-%m-%d')})
        row.update({k:bool(item[k]) for k in ['selected','flagged','overflow','supplementary']})
        row['recommendation']=recommendation(row)
        rows.append(row)
    source_paths=[Path(__file__),ROOT/'scripts/app_data.py',ROOT/'scripts/operations.py',ROOT/'.agents/skills/pdm-risk/SKILL.md']
    return {'month':'2026-01','policy':policy,'summary':{'candidates':len(rows),**{k:int(scored[k].sum()) for k in ['selected','flagged','overflow','supplementary']}},'rows':rows,
        'provenance':{'command':COMMAND,'training_sha256':sha(lib.TRAINING_PATH),'input_sha256':{p.name:sha(p) for p in [lib.HISTORY_CSV,lib.TEST_CSV,lib.MONTH_CSV]},'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},'policy_sha256':sha(ROOT/'reports/06_operations.md')},'limits':card['limits']}


def table(columns,rows):
    def text(v): return str(v).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(columns)+' |','| '+' | '.join(['---']*len(columns))+' |']+['| '+' | '.join(text(v) for v in row)+' |' for row in rows])


def plan_table(rows):
    return table(['전체 순위','드론','유형','부대','최신 정비일','확률','구분','위험을 올린 요인','권고'],[[r['rank'],r['equipment_id'],r['equipment_type'],r['unit_code'],r['maintenance_date'],f"{r['prob']:.1%}",r['status'],r['reasons'],r['recommendation']] for r in rows])


def ending(facts,marker):
    return ['## 계산 원출력','<!-- '+marker+' -->','```json',json.dumps(facts,ensure_ascii=False,indent=2),'```','## 모델 한계 — 학습 번들 model_card.limits 원문']+['- '+v for v in facts['limits']]+['최종 판단은 정비 담당자가 한다.']


def render_plan(f):
    c=f['summary']; p=f['policy']
    lines=['# 2026-01 드론 재점검 계획','## 출처와 기준',
        f'수치 출처: `{COMMAND} --write-plan` 실행과 아래 SCORE_FACTS 원출력. 입력은 data/data 원본과 artifacts/training_run.joblib이며 운영 기준은 reports/06_operations.md다. 설명은 모델 기여도로 인과관계가 아니다.',
        '## 선정 현황',
        f"최신 기록 후보 {c['candidates']}대, 선정 {c['selected']}대, 기준 이상 {c['flagged']}대, 기준 이상 초과 대기 {c['overflow']}대, 기준 미만 예방 점검 {c['supplementary']}대다. 출처: SCORE_FACTS.summary.",
        f"위험 기준은 {p['threshold']:.0%} 이상, 월 점검 용량은 {p['capacity_per_month']}대다. 출처: SCORE_FACTS.policy. 같은 확률은 장비 번호 오름차순, 같은 날짜 복수 기록은 입력 순서상 마지막 기록을 사용한다.",
        '## 재점검 대상',plan_table([r for r in f['rows'] if r['selected']]),
        '표의 출처는 SCORE_FACTS.rows 중 selected=true인 행이다. 확률은 백분율 소수 첫째 자리로 반올림했다.',
        '## 용량 초과 대응',
        '초과 대기는 안전 판정이 아니다. 담당자가 현장 상태에 따라 추가 용량·조기 재점검을 판단한다. 다음 달 자동 이월은 하지 않으며 새 기록이 생기면 최신 기록으로 재평가한다. 아래 출처는 SCORE_FACTS.rows 중 overflow=true인 행이다.',
        plan_table([r for r in f['rows'] if r['overflow']]),
        '## 실행 순서','- 담당자가 정비 이력·현장 상태와 선정·대기 목록을 검토한다.','- 선정 순서로 점검을 배정하고 부품·정비 조치 결과를 재확인한다.','- 점검 결과를 기록하고 정답이 관측된 뒤 기준과 모델을 재검증한다.','- 권고는 교육용 점검 항목이며 확인되지 않은 결함·수리 효과를 단정하지 않는다.']
    return '\n\n'.join(lines+ending(f,'SCORE_FACTS'))+'\n'


def analysis_facts():
    b=bundle(); card=b['model_card']
    raw=pd.read_csv(lib.HISTORY_CSV,encoding='utf-8-sig'); clean=lib.clean(raw)
    return {'split_counts':card['split_counts'],'trained_on':card['trained_on'],'label_policy':card['label_policy'],'validation':card['validation'],
        'threshold_comparison':build_evidence()['threshold_comparison'],
        'cleaning':{'downtime_999':int(raw.downtime_hours.eq(999).sum()),'cost_over_10000':int(raw.maintenance_cost.gt(10000).sum()),'fault_missing':int(raw.fault_category.isna().sum()),'first_maintenance':int(clean.is_first_maintenance.sum()),'raw_rows':len(raw),'clean_rows':len(clean)},
        'features':card['features'],'test_status':card['test_2025_status'],
        'provenance':{'command':COMMAND+' --write-analysis','training_sha256':sha(lib.TRAINING_PATH),'test_predictions_sha256':sha(TEST_PATH),'score_script_sha256':sha(Path(__file__)),'source':'training_run.joblib.model_card, operations.build_evidence, drone_train.csv'},'limits':card['limits']}


def render_analysis(f):
    c=f['cleaning']; v=f['validation']; counts=f['split_counts']
    lines=['# 드론 예측정비 분석 보고서','## 목적과 출처',f'교육용 드론 정비 직후 재고장 예측 실습이다. 모든 수치는 `{COMMAND} --write-analysis`와 아래 ANALYSIS_FACTS 원출력에서 가져왔다. 분포·결측·계절별 세부 패턴은 reports/02_EDA.md를 함께 참조한다.',
        '## 데이터 처리와 근거',table(['항목','기록 수','처리'],[
        ['가동중단 999',c['downtime_999'],'미입력 코드로 결측 처리; 행 보존'],['비용 >10000',c['cost_over_10000'],'기존 실습 자릿수 오류 규칙에 따라 100으로 나눔'],['고장 유형 결측',c['fault_missing'],'EDA에서 예방정비와 일치; 코드·유형을 N/A로 구분'],['직전 정비 경과일 결측',c['first_maintenance'],'관측 내 첫 기록; 결측 유지·첫 정비 표시 추가'],['원본→처리 행 수',str(c['raw_rows'])+' → '+str(c['clean_rows']),'행 삭제 없음']]),
        '출처: ANALYSIS_FACTS.cleaning. 시간 피처는 각 정비일까지의 이력만 사용하고 시험·이번 달 피처에는 앞 기간 기록을 연결한다. 원본 CSV는 수정하지 않았다.',
        '## 입력 컬럼과 제외 이유','입력은 ANALYSIS_FACTS.features의 공통 FEATURES로 한정했다. availability_rate는 월 전체 가동률로 예측 시점 이후 정보를 포함할 수 있어 제외했다. equipment_id·unit_code는 식별자이며 maintenance_date는 기간 분할용이다. fault_code는 fault_category로 대신했다. 정답은 모델 입력에서 제외했다.',
        '## 기간 분할과 정답 확정','학습 후보는 2024-06-30까지, 검증 후보는 2024년 하반기다. 정답 확정일 미제공에 따라 정비일에 관측창을 더한 값이 기준일보다 앞선 기록만 사용했다. 기준일·관측창은 ANALYSIS_FACTS.label_policy가 출처다. 원본을 삭제하지 않고 학습·평가 사용 여부만 구분했다.',
        table(['구분','기록 수'],[[k,value] for k,value in counts.items()]),'출처: ANALYSIS_FACTS.split_counts. train은 학습, valid_records는 검증 원본, valid_latest는 월별 최신 후보, evaluation_candidates는 정답 확정 후 평가 후보, final_train은 최종 학습 기록이다.',
        '최종 학습: '+f['trained_on']+'. 출처: ANALYSIS_FACTS.trained_on. 전체 학습 모델을 검증 데이터에 다시 적용한 성능으로 대체하지 않았다.',
        '## 검증 성능과 기준선',table(['기준','PR-AUC','월별 선정 적중 합계'],[['모델',f"{v['pr_auc']:.6f}",v['totals']['model']],['오래된 순',f"{v['oldest_pr_auc']:.6f}",v['totals']['oldest']],['무작위',f"{v['random_pr_auc']:.6f}",f"{v['totals']['random']:.6f}"]]),
        '출처: ANALYSIS_FACTS.validation. PR-AUC는 Average Precision이다. 무작위 PR-AUC는 양성 비율 기준이고 적중은 추첨 결과가 아닌 기대값이다. 월별 최신 장비를 먼저 고른 뒤 정답 확정 조건을 적용해 평가 후보를 통일했다.',
        table(['월','평가 후보','선정','모델 적중','오래된 순','무작위 기대 적중','부분 평가'],[[r['month'],r['eligible_candidates'],r['picked'],r['model'],r['oldest'],f"{r['random']:.6f}",r['partial_evaluation']] for r in v['monthly']]),
        '출처: ANALYSIS_FACTS.validation.monthly. 마지막 달은 부분 평가다. 검증 기준 선택에 사용한 표본이므로 독립 시험 성능이 아니다.',
        '## 위험 기준과 비용 비교',table(['놓친 재고장 비용(만원)','선택 기준','검증 표시 비용(만원)'],[[r['missed_cost_manwon'],r['threshold'],r['validation_cost_manwon']] for r in f['threshold_comparison']]),
        '출처: ANALYSIS_FACTS.threshold_comparison. 위험 표시 비용과 실제 월 점검 용량 적용은 구분했다. 상위 장비 선정과 초과 대기 처리의 근거는 reports/06_operations.md다.',
        '## 시험 예측 제출물','reports/test_predictions_2025.csv는 시험 원본의 모든 행을 원래 순서로 보존한다. equipment_id, maintenance_date, prob 열만 저장하며 장비별로 중복 제거하지 않는다. 날짜는 YYYY-MM-DD다. 해시 출처는 ANALYSIS_FACTS.provenance.test_predictions_sha256이다.',f['test_status'],
        '## 재현과 검증','환경은 python -m pip install -r requirements-app.txt, 검증은 python scripts/check.py로 실행한다. 기존 결과의 보존·버전 방식을 정한 뒤 학습을 재실행한다. 결과 생성기는 기존 파일을 덮어쓰지 않는다.']
    return '\n\n'.join(lines+ending(f,'ANALYSIS_FACTS'))+'\n'


def save_new(path,text):
    if path.exists(): raise FileExistsError('기존 결과 보존: '+str(path))
    path.write_text(text,encoding='utf-8')
    assert path.read_text(encoding='utf-8')==text
    print('저장·재읽기 확인:',path)


def main():
    configure_output = getattr(sys.stdout, 'reconfigure', None)
    if callable(configure_output):
        configure_output(encoding='utf-8')
    parser=argparse.ArgumentParser()
    modes=parser.add_mutually_exclusive_group()
    for name in ['write-test','write-plan','write-analysis']: modes.add_argument('--'+name,action='store_true')
    modes.add_argument('--explain')
    parser.add_argument('--top',type=int,default=20)
    args=parser.parse_args()
    if args.top<1: parser.error('--top은 양의 정수여야 합니다')
    if args.write_test:
        if TEST_PATH.exists(): raise FileExistsError(str(TEST_PATH))
        output=test_predictions(bundle())
        output.to_csv(TEST_PATH,index=False,encoding='utf-8-sig',float_format='%.17g')
        print('시험 예측 저장:',TEST_PATH,'행 수:',len(output),'시험 성능: 미평가')
    elif args.write_analysis: save_new(ANALYSIS_PATH,render_analysis(analysis_facts()))
    else:
        facts=score_facts()
        if args.write_plan: save_new(PLAN_PATH,render_plan(facts))
        if args.explain:
            found=[r for r in facts['rows'] if r['equipment_id']==args.explain]
            if not found: raise ValueError('이번 달 기록에 없는 장비: '+args.explain)
            print(json.dumps(found[0],ensure_ascii=False,indent=2))
        else:
            print(json.dumps(facts['summary'],ensure_ascii=False))
            print(plan_table(facts['rows'][:args.top]))


if __name__=='__main__': main()
