"""드론 프로젝트 중간점검. 파일을 수정하거나 모델을 학습하지 않는다."""
import hashlib
import importlib
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'data'


def read(path):
    return path.read_text(encoding='utf-8-sig') if path.is_file() else ''



def check_preparation():
    import numpy as np
    import pandas as pd
    from pandas.testing import assert_frame_equal
    sys.path.insert(0, str(ROOT))
    import pdm_lib as lib
    if Path(lib.__file__).resolve() != ROOT / 'pdm_lib.py':
        raise AssertionError('다른 프로젝트 공통 함수가 로드됨')
    if '## 데이터 처리 — 3단계' not in read(ROOT / 'AGENTS.md'):
        raise AssertionError('데이터 처리 규칙 누락')
    paths = [DATA / name for name in ['drone_train.csv','drone_test.csv','drone_this_month.csv']]
    before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    prepared = lib.prepare_data()
    summaries = []
    for name, path in zip(['train','test','month'],paths):
        raw = pd.read_csv(path,encoding='utf-8-sig',parse_dates=['maintenance_date'])
        snapshot = raw.copy(deep=True)
        cleaned = lib.clean(raw)
        assert_frame_equal(raw,snapshot)
        assert cleaned.index.equals(raw.index) and len(cleaned)==len(raw)
        assert cleaned.downtime_hours.isna().equals(raw.downtime_hours.isna() | raw.downtime_hours.eq(999))
        expected_cost = raw.maintenance_cost.where(raw.maintenance_cost.le(10000),raw.maintenance_cost/100)
        np.testing.assert_allclose(cleaned.maintenance_cost,expected_cost,equal_nan=True)
        for col in ['fault_code','fault_category']:
            assert cleaned[col].equals(raw[col].fillna('N/A'))
        assert cleaned.days_since_last_maintenance.equals(raw.days_since_last_maintenance)
        assert cleaned.is_first_maintenance.equals(raw.days_since_last_maintenance.isna().astype(int))
        result = prepared[name]
        assert len(result)==len(raw) and set(lib.FEATURES)<=set(result.columns)
        assert result.equipment_id.equals(raw.equipment_id)
        assert result.maintenance_date.equals(raw.maintenance_date)
        if name!='train': assert lib.TARGET not in result
        assert_frame_equal(result[cleaned.columns],cleaned)
        summaries.append(f'{name}: {len(result):,}행 보존·정제 확인')
    banned={lib.TARGET,'availability_rate','equipment_id','unit_code','maintenance_date','fault_code'}
    assert not banned.intersection(lib.FEATURES)
    # 수작업 기대값: 90일 경계, 같은 날 포함, 장비 분리, 이력 없음, 첫 정비.
    fixture=pd.DataFrame({
        'equipment_id':['A','A','A','A','B'],
        'maintenance_date':pd.to_datetime(['2024-01-01','2024-03-31','2024-04-01','2024-04-01','2024-02-01']),
        'maintenance_type':['사후정비','긴급정비','예방정비','사후정비','사후정비'],
        'cumulative_operating_hours':[100.,150.,180.,185.,20.]},index=[7,7,3,2,1])
    snap=fixture.copy(deep=True)
    actual=lib.add_time_features(fixture)
    assert_frame_equal(fixture,snap)
    assert actual.index.equals(fixture.index)
    np.testing.assert_array_equal(actual.fail_count_90d,[1,2,2,2,1])
    np.testing.assert_allclose(actual.days_since_last_failure,[0,0,0,0,0])
    np.testing.assert_allclose(actual.hours_since_last_pm,[np.nan,np.nan,0,5,np.nan],equal_nan=True)
    # 실제 데이터: 미래 기록 추가·정답 변경에 과거 피처가 불변인지 확인.
    combined=pd.concat([pd.read_csv(p,encoding='utf-8-sig',parse_dates=['maintenance_date']) for p in paths],ignore_index=True)
    clean=lib.clean(combined)
    full=lib.add_time_features(clean)
    for cutoff in ['2024-06-30','2024-12-31','2025-12-31']:
        past=clean.loc[clean.maintenance_date.le(cutoff)].copy()
        assert_frame_equal(lib.add_time_features(past)[lib.TIME_COLS],full.loc[past.index,lib.TIME_COLS])
    changed=clean.copy()
    changed[lib.TARGET]=0
    assert_frame_equal(lib.add_time_features(changed)[lib.TIME_COLS],full[lib.TIME_COLS])
    for name, part in zip(['train','test','month'], [full.iloc[:len(prepared['train'])], full.iloc[len(prepared['train']):len(prepared['train'])+len(prepared['test'])],full.iloc[-len(prepared['month']):]]):
        assert_frame_equal(prepared[name][lib.TIME_COLS],part[lib.TIME_COLS].reset_index(drop=True))
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    return summaries



def collect_audit():
    """사전 학습 코드·모델을 읽어 감사 근거를 수집. 학습·저장은 하지 않는다."""
    import ast
    import json
    import joblib
    import pandas as pd
    trainer = Path(r'C:\workspaces\pdm_ai_lab\reports\train_drone.py')
    oldlib = Path(r'C:\workspaces\pdm_ai_lab\pdm_lib.py')
    model_path = ROOT / 'artifacts' / 'drone_model.joblib'
    source = trainer.read_text(encoding='utf-8-sig')
    ast.parse(source)
    bundle = joblib.load(model_path)
    card = bundle['model_card']
    used = list(bundle['model'].feature_names_in_)
    sys.path.insert(0, str(ROOT))
    import pdm_lib
    banned = {'availability_rate','equipment_id','unit_code','maintenance_date','fault_code',pdm_lib.TARGET}
    df = pd.read_csv(DATA / 'drone_train.csv',parse_dates=['maintenance_date'])
    boundary = pd.Timestamp('2024-07-01')
    window_overlap = int(((df.maintenance_date < boundary) & (df.maintenance_date + pd.Timedelta(days=30) >= boundary)).sum())
    repeated = int(df.assign(month=df.maintenance_date.dt.to_period('M')).duplicated(['equipment_id','month']).sum())
    checked = [trainer,oldlib,ROOT/'pdm_lib.py',model_path]+[DATA/name for name in ['drone_train.csv','drone_test.csv','drone_this_month.csv']]
    return {
        'sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checked},
        'model_features': used,
        'feature_match': used == pdm_lib.FEATURES and used == card['features'],
        'banned_features': sorted(set(used)&banned),
        'validation_metrics_separate': 'validation_2024_h2' in card and 'test_2025' not in card,
        'test_status': card.get('test_2025_status'),
        'validation_note': card.get('evaluation_note'),
        'external_trainer': str(trainer),
        'local_training_script_exists': (ROOT/'scripts/train.py').is_file(),
        'local_model_factory_exists': hasattr(pdm_lib,'make_model'),
        'local_model_card_factory_exists': hasattr(pdm_lib,'make_card'),
        'boundary_window_overlap_records': window_overlap,
        'equipment_month_repeated_records': repeated,
        'code_evidence': {
            'train_period': 'dates <= "2024-06-30"' in source,
            'validation_period': 'dates.between("2024-07-01", "2024-12-31")' in source,
            'uses_features_only': 'model.fit(train[pdm_lib.FEATURES], train[pdm_lib.TARGET])' in source,
            'validation_threshold': 'flagged = valid.prob >= threshold' in source,
            'row_based_topk': 'pdm_lib.monthly_topk(valid, "prob", 20)' in source,
            'final_fit_all_labeled': 'final.fit(df[pdm_lib.FEATURES], df[pdm_lib.TARGET])' in source,
            'external_import': 'sys.path.insert(0, str(Path(__file__).resolve().parents[1]))' in source,
        },
        'limits':card['limits'],
    }


def check_audit():
    import json
    report = read(ROOT / 'reports' / '04_model_audit.md')
    match = re.search(r'<!-- AUDIT_FACTS -->\s*```json\s*(.*?)\s*```',report,re.S)
    if not match:
        raise AssertionError('감사 보고서 또는 근거 JSON 없음')
    recorded = json.loads(match.group(1))
    # 과거 감사는 당시 상태의 기록. 후속 구현의 로컬 코드 변경과 구분한다.
    immutable = {'drone_model.joblib': ROOT/'artifacts/drone_model.joblib'}
    immutable.update({name:DATA/name for name in ['drone_train.csv','drone_test.csv','drone_this_month.csv']})
    for name, path in immutable.items():
        saved = [value for key,value in recorded['sha256'].items() if Path(key).name==name]
        if len(saved)!=1 or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=saved[0]:
            raise AssertionError('사전 학습 감사의 보존 대상 변경: '+name)
    current = recorded
    for heading in ['감사 결론','확인된 사항','개선할 사항','후속 조치','감사 범위와 한계']:
        if heading not in report:
            raise AssertionError('감사 보고서 필수 항목 누락: '+heading)
    return current



def check_training():
    import json
    import importlib.metadata
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.metrics import average_precision_score
    sys.path.insert(0,str(ROOT))
    import pdm_lib as lib
    bundle=joblib.load(lib.TRAINING_PATH)
    card=bundle['model_card']
    for name,digest in card['provenance']['input_sha256'].items():
        assert hashlib.sha256((DATA/name).read_bytes()).hexdigest()==digest, '학습 원본 변경: '+name
    for name,digest in card['provenance']['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest, '학습 코드 변경: '+name
    for name,version in card['provenance']['packages'].items():
        assert importlib.metadata.version(name)==version, '패키지 버전 변경: '+name
    full=lib.add_time_features(lib.clean(lib.load_history()))
    horizon=full.maintenance_date+pd.Timedelta(days=30)
    train=full.loc[(full.maintenance_date<='2024-06-30') & (horizon<'2024-07-01')]
    final=full.loc[horizon<'2025-01-01']
    assert train.index.tolist()==bundle['training_indices']
    assert final.index.tolist()==bundle['final_training_indices']
    valid=bundle['validation_predictions']
    expected=full.loc[full.maintenance_date.between('2024-07-01','2024-12-31')]
    pd.testing.assert_frame_equal(valid[expected.columns],expected)
    assert not train.index.intersection(valid.index).size
    for key in ['model','validation_model']:
        assert list(bundle[key].feature_names_in_)==lib.FEATURES
    banned={'availability_rate','equipment_id','unit_code','maintenance_date','fault_code',lib.TARGET}
    assert not banned.intersection(lib.FEATURES)
    prob=bundle['validation_model'].predict_proba(valid[lib.FEATURES])[:,1]
    np.testing.assert_allclose(prob,valid.prob,rtol=1e-12,atol=1e-12)
    assert valid.prob.between(0,1).all()
    latest=valid.assign(month=valid.maintenance_date.dt.strftime('%Y-%m')).sort_values('maintenance_date',kind='stable').groupby(['month','equipment_id'],sort=False).tail(1)
    candidate=latest.loc[latest.maintenance_date+pd.Timedelta(days=30)<'2025-01-01']
    assert set(valid.index[valid.is_monthly_latest])==set(latest.index)
    assert valid.label_mature.equals(valid.maintenance_date.add(pd.Timedelta(days=30)).lt('2025-01-01'))
    np.testing.assert_allclose(card['validation']['pr_auc'],average_precision_score(candidate[lib.TARGET],candidate.prob))
    np.testing.assert_allclose(card['validation']['oldest_pr_auc'],average_precision_score(candidate[lib.TARGET],candidate.equipment_age_years))
    np.testing.assert_allclose(card['validation']['random_pr_auc'],candidate[lib.TARGET].mean())
    for row in card['validation']['monthly']:
        g=candidate.loc[candidate.month.eq(row['month'])]
        assert row['eligible_candidates']==len(g)
        assert row['latest_candidates']==int(latest.month.eq(row['month']).sum())
        assert row['picked']==min(20,len(g))
        for score,key in [('prob','model'),('equipment_age_years','oldest')]:
            selected=g.sort_values([score,'equipment_id'],ascending=[False,True],kind='stable').head(20)
            assert not selected.equipment_id.duplicated().any()
            assert row[key]==int(selected[lib.TARGET].sum())
        random=min(20,len(g))*g[lib.TARGET].mean() if len(g) else 0
        np.testing.assert_allclose(row['random'],random)
    for missed_cost in [300,600]:
        grid=[]
        for step in range(5,95):
            flag=candidate.prob.ge(step/100)
            cost=int((candidate[lib.TARGET].eq(1)&~flag).sum()*missed_cost+flag.sum()*60)
            grid.append((cost,step/100))
        cost,t=min(grid)
        assert card['threshold_comparison'][str(missed_cost)]=={'threshold':t,'cost_manwon':cost}
        saved=bundle['threshold_grid'].loc[bundle['threshold_grid'].missed_cost.eq(missed_cost)]
        assert list(zip(saved.cost,saved.threshold))==grid
    assert card['threshold']==card['threshold_comparison']['300']['threshold']
    assert 'test_2025' not in card and '미평가' in card['test_2025_status']
    assert card['split_counts']['final_train']==len(final)
    skill=read(ROOT/'.agents/skills/drone-train/SKILL.md')
    assert skill.startswith('---\nname: drone-train\n') and 'description:' in skill
    return card



def check_operations():
    import json
    import numpy as np
    import pandas as pd
    from pandas.testing import assert_frame_equal
    from operations import apply_policy, build_evidence
    report=read(ROOT/'reports/06_operations.md')
    match=re.search(r'<!-- OPERATIONS_FACTS -->\s*```json\s*(.*?)\s*```',report,re.S)
    assert match, '운영 보고서 근거 없음'
    saved=json.loads(match.group(1))
    assert saved==build_evidence(), '운영 근거·학습 결과·실행 코드 변경'
    p=saved['policy']
    assert p['threshold']==saved['threshold_comparison'][0]['threshold']
    assert p['capacity_per_month']==20 and p['comparison']=='>='
    assert '## 운영 기준 — 6단계' in read(ROOT/'AGENTS.md')
    fixture=pd.DataFrame({
        'equipment_id':['A','A','B','C','D','E','F'],
        'maintenance_date':pd.to_datetime(['2026-01-01','2026-01-02','2026-01-01','2026-01-01','2026-01-01','2026-02-01','2026-01-01']),
        'prob':[0.99,0.1,0.3,0.3,0.2,0.8,0.5]})
    snapshot=fixture.copy(deep=True)
    result=apply_policy(fixture,0.3,2)
    assert_frame_equal(fixture,snapshot)
    january=result.loc[result.month.eq('2026-01')]
    assert january.equipment_id.tolist()==['F','B','C','D','A']
    assert january.loc[january.selected,'equipment_id'].tolist()==['F','B']
    assert january.loc[january.overflow,'equipment_id'].tolist()==['C']
    assert january.loc[january.flagged,'equipment_id'].tolist()==['F','B','C']
    assert result.loc[result.month.eq('2026-02'),'selected'].all()
    filled=apply_policy(fixture,0.9,2)
    assert filled.loc[filled.selected,'supplementary'].all()
    assert len(apply_policy(fixture.iloc[:0],0.3,2))==0
    tie=fixture.iloc[[2,2]].copy()
    tie['prob']=[0.9,0.1]
    assert apply_policy(tie,0.3,2).prob.tolist()==[0.1]
    for value in [np.nan,np.inf,-0.1,1.1]:
        bad=fixture.copy()
        bad.loc[0,'prob']=value
        try: apply_policy(bad,0.3,2)
        except ValueError: pass
        else: raise AssertionError('유효하지 않은 확률 허용')
    for capacity in [0,-1,True,1.5]:
        try: apply_policy(fixture,0.3,capacity)
        except ValueError: pass
        else: raise AssertionError('유효하지 않은 용량 허용')
    # 실제 검증자료: 근거의 선정·대기·보충 수와 비용을 별도로 재계산한다.
    import joblib
    bundle=joblib.load(ROOT/'artifacts/training_run.joblib')
    valid=bundle['validation_predictions']
    candidates=valid.loc[valid.is_monthly_latest & valid.label_mature]
    for row in saved['validation_monthly']:
        group=candidates.loc[candidates.maintenance_date.dt.strftime('%Y-%m').eq(row['month'])]
        latest=group.sort_values('maintenance_date',kind='stable').drop_duplicates('equipment_id',keep='last')
        ranked=latest.sort_values(['prob','equipment_id'],ascending=[False,True],kind='stable')
        top=ranked.head(20)
        assert row['selected']==min(20,len(latest))
        assert row['model_hits']==int(top.failure_within_30days.sum())
        assert row['flagged']==int(latest.prob.ge(p['threshold']).sum())
        assert row['overflow']==int(ranked.iloc[20:].prob.ge(p['threshold']).sum())
        assert row['supplementary']==int(top.prob.lt(p['threshold']).sum())
        for cost in [300,600]:
            missed=int(latest.failure_within_30days.sum()-top.failure_within_30days.sum())
            assert row[f'model_cost_{cost}']==missed*cost+len(top)*60
    return saved



def check_app():
    import logging
    import joblib
    import pandas as pd
    from pandas.testing import assert_frame_equal
    from streamlit.testing.v1 import AppTest
    from scripts.app_data import score_current_month
    from scripts.operations import apply_policy
    import pdm_lib as lib
    paths=[lib.HISTORY_CSV,lib.TEST_CSV,lib.MONTH_CSV,lib.TRAINING_PATH,ROOT/'reports/06_operations.md']
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    bundle=joblib.load(lib.TRAINING_PATH)
    scored,card,policy=score_current_month(bundle)
    raw=lib.prepare_data()['month']
    latest=raw.sort_values('maintenance_date',kind='stable').drop_duplicates('equipment_id',keep='last').copy()
    latest['prob']=bundle['model'].predict_proba(latest[lib.FEATURES])[:,1]
    expected=apply_policy(latest,policy['threshold'],policy['capacity_per_month'])
    assert_frame_equal(scored[['equipment_id','rank','prob','selected','overflow','supplementary']],expected[['equipment_id','rank','prob','selected','overflow','supplementary']])
    assert not scored.equipment_id.duplicated().any()
    assert scored.reasons.notna().all()
    previous=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=45).run()
        assert not app.exception, str(app.exception)
        assert not app.error, '앱 데이터 로딩 오류'
        table=app.dataframe[0].value
        assert table['드론'].tolist()==scored.equipment_id.tolist()
        assert table['전체 순위'].tolist()==scored['rank'].tolist()
        assert app.metric[1].value==f'{int(scored.selected.sum()):,}대'
        summary=app.dataframe[1].value
        assert int(summary['후보'].sum())==len(scored)
        assert int(summary['점검선정'].sum())==int(scored.selected.sum())
        unit=sorted(scored.unit_code.unique())[0]
        app.selectbox(key='unit').select(unit).run()
        assert not app.exception
        filtered=app.dataframe[0].value
        target=scored.loc[scored.unit_code.eq(unit)]
        assert filtered['드론'].tolist()==target.equipment_id.tolist()
        assert filtered['전체 순위'].tolist()==target['rank'].tolist()
        assert_frame_equal(app.dataframe[1].value,summary)
        app.selectbox(key='unit').select('전체').run()
        kind=sorted(scored.equipment_type.unique())[0]
        app.selectbox(key='kind').select(kind).run()
        assert not app.exception
        assert app.dataframe[0].value['드론'].tolist()==scored.loc[scored.equipment_type.eq(kind),'equipment_id'].tolist()
        app.selectbox(key='kind').select('전체').run()
        for scope,mask in [('선정 대상',scored.selected),('초과 대기',scored.overflow),('예방 점검',scored.supplementary),('기준 이상',scored.flagged)]:
            app.selectbox(key='scope').select(scope).run()
            assert not app.exception and not app.error
            assert app.dataframe[0].value['드론'].tolist()==scored.loc[mask,'equipment_id'].tolist()
        app.selectbox(key='scope').select('전체').run()
        first=scored.equipment_id.iloc[0]
        app.text_input(key='search').set_value(first.lower()).run()
        assert not app.exception
        assert app.dataframe[0].value['드론'].tolist()==[first]
        app.text_input(key='search').set_value('NO-SUCH-DRONE').run()
        assert not app.exception and app.dataframe[0].value.empty
        app.button[0].click().run()
        assert not app.exception
        assert app.text_input(key='search').value==''
        assert app.dataframe[0].value['드론'].tolist()==scored.equipment_id.tolist()
        assert len(app.get('vega_lite_chart'))==2
        assert len(app.get('download_button'))==1
        assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    finally:
        logging.disable(previous)



def check_deliverables():
    import importlib.util
    import json
    import joblib
    import numpy as np
    import pandas as pd
    import pdm_lib as lib
    score_path=ROOT/'.agents/skills/pdm-risk/scripts/score.py'
    spec=importlib.util.spec_from_file_location('drone_risk_score',score_path)
    score=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(score)
    protected=[lib.HISTORY_CSV,lib.TEST_CSV,lib.MONTH_CSV,lib.TRAINING_PATH]
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    b=joblib.load(lib.TRAINING_PATH)
    # 시험 파일: 원본 모든 행·순서·날짜·열, 확률을 모델로 독립 재계산.
    submitted=pd.read_csv(score.TEST_PATH,encoding='utf-8-sig')
    raw=pd.read_csv(lib.TEST_CSV,encoding='utf-8-sig')
    assert list(submitted.columns)==['equipment_id','maintenance_date','prob']
    assert len(submitted)==len(raw) and submitted.equipment_id.tolist()==raw.equipment_id.tolist()
    dates=pd.to_datetime(raw.maintenance_date).dt.strftime('%Y-%m-%d')
    assert submitted.maintenance_date.tolist()==dates.tolist()
    assert submitted.maintenance_date.str.fullmatch(r'\d{4}-\d{2}-\d{2}').all()
    assert submitted.prob.notna().all() and np.isfinite(submitted.prob).all() and submitted.prob.between(0,1).all()
    prepared=lib.prepare_data()
    expected=b['model'].predict_proba(prepared['test'][lib.FEATURES])[:,1]
    np.testing.assert_allclose(submitted.prob,expected,rtol=1e-12,atol=1e-12)
    # 계획의 화면 표시 표와 계산 근거를 함께 확인.
    plan=read(score.PLAN_PATH)
    match=re.search(r'<!-- SCORE_FACTS -->\s*```json\s*(.*?)\s*```',plan,re.S)
    assert match, '계획 계산 근거 없음'
    saved=json.loads(match.group(1))
    facts=score.score_facts()
    assert saved==facts, '계획 수치·설명·출처가 실행 결과와 다름'
    assert plan==score.render_plan(facts), '계획 본문의 표·대수·설명 불일치'
    selected=[r for r in facts['rows'] if r['selected']]
    assert len(selected)==min(facts['policy']['capacity_per_month'],facts['summary']['candidates'])
    assert len({r['equipment_id'] for r in facts['rows']})==len(facts['rows'])
    assert [r['rank'] for r in facts['rows']]==list(range(1,len(facts['rows'])+1))
    section=plan.split('## 재점검 대상',1)[1].split('## 용량 초과 대응',1)[0]
    visible=re.findall(r'^\| (\d+) \| (DR-\d+) \|.*?\| ([\d.]+)% \|',section,re.M)
    assert [(int(rank),equipment,float(prob)) for rank,equipment,prob in visible]==[(r['rank'],r['equipment_id'],float(f"{r['prob']*100:.1f}")) for r in selected]
    # 앱과 공유한 결과를 별도 모델 예측·최신 일자로 재대조.
    from scripts.app_data import score_current_month
    scored,card,policy=score_current_month(b)
    assert scored.equipment_id.tolist()==[r['equipment_id'] for r in facts['rows']]
    np.testing.assert_allclose(scored.prob,[r['prob'] for r in facts['rows']],rtol=1e-12,atol=1e-12)
    month=prepared['month'].sort_values('maintenance_date',kind='stable').drop_duplicates('equipment_id',keep='last').set_index('equipment_id')
    for row in facts['rows']:
        latest=month.loc[row['equipment_id']]
        assert row['maintenance_date']==latest.maintenance_date.strftime('%Y-%m-%d')
    # 기여도의 합이 모델 확률을 재현하는지 확인.
    x=month[lib.FEATURES]
    transformed=b['model']['pre'].transform(x)
    raw_contrib=b['model']['model'].booster_.predict(transformed,pred_contrib=True)
    reconstructed=1/(1+np.exp(-raw_contrib.sum(axis=1)))
    np.testing.assert_allclose(reconstructed,b['model'].predict_proba(x)[:,1],rtol=1e-10,atol=1e-12)
    analysis=read(score.ANALYSIS_PATH)
    match=re.search(r'<!-- ANALYSIS_FACTS -->\s*```json\s*(.*?)\s*```',analysis,re.S)
    assert match, '분석 보고서 근거 없음'
    saved_analysis=json.loads(match.group(1))
    current=score.analysis_facts()
    assert saved_analysis==current and analysis==score.render_analysis(current), '분석 보고서와 실행 결과 불일치'
    for content in [plan,analysis]:
        for limit in card['limits']: assert '- '+limit in content
        assert content.rstrip().endswith('최종 판단은 정비 담당자가 한다.')
    skill=read(ROOT/'.agents/skills/pdm-risk/SKILL.md')
    assert skill.startswith('---\nname: pdm-risk\n') and 'description:' in skill
    assert '## 보고 · 제출물 검수 — 8단계' in read(ROOT/'AGENTS.md')
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    return len(submitted),len(selected)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print('드론 예측정비 실습 중간점검')
    print(f'프로젝트: {ROOT}')
    print(f'Python: {sys.executable}')
    print('-' * 66)
    missing = []
    for name in ['pandas', 'numpy', 'sklearn', 'lightgbm', 'joblib']:
        try:
            importlib.import_module(name)
        except Exception as exc:
            missing.append(f'{name}: {type(exc).__name__}: {exc}')
    files = ['drone_train.csv', 'drone_test.csv', 'drone_this_month.csv']
    errors = [f'라이브러리 오류: {x}' for x in missing]
    rules = read(ROOT / 'AGENTS.md')
    if '## 기본 규칙' not in rules or '## 단계별 진행' not in rules:
        errors.append('AGENTS.md 기본 규칙·단계별 진행 확인 필요')
    if not (ROOT / '.git').exists():
        errors.append('Git 저장소 확인 필요')
    if sys.prefix == sys.base_prefix:
        errors.append('가상환경 미활성화: .\\.venv\\Scripts\\Activate.ps1 실행 필요')
    tables = {}
    for name in files:
        path = DATA / name
        if not path.is_file():
            errors.append(f'데이터 없음: {path.relative_to(ROOT)}')
            continue
        if not missing:
            try:
                import pandas as pd
                pd.options.mode.string_storage = 'python'
                frame = pd.read_csv(path, encoding='utf-8-sig')
                required = {'equipment_id', 'maintenance_date', 'maintenance_type', 'fault_category'}
                if not required.issubset(frame.columns) or frame.empty:
                    raise ValueError('필수 컬럼 누락 또는 빈 데이터')
                dates = pd.to_datetime(frame.maintenance_date, errors='raise')
                if dates.isna().any():
                    raise ValueError('정비일 결측')
                target = 'failure_within_30days'
                if name == 'drone_train.csv':
                    if target not in frame or frame[target].isna().any() or not set(frame[target].unique()) <= {0, 1}:
                        raise ValueError('학습 정답 컬럼 확인 필요')
                elif target in frame:
                    raise ValueError('정답 미제공 파일에 정답 컬럼이 있음: 구성 재확인 필요')
                tables[name] = frame
            except Exception as exc:
                errors.append(f'{name}: {type(exc).__name__}: {exc}')
    if errors:
        print('[확인 필요] 1단계 준비 · 기본 규칙')
        for error in errors:
            print('  - ' + error)
    else:
        print('[확인 통과] 1단계 준비 · 기본 규칙')
        print('  가상환경·라이브러리·Git·기본 규칙·입력 데이터 구조 확인')
    for name, frame in tables.items():
        print(f'  {name}: {len(frame):,}행, {len(frame.columns)}열')

    report = read(ROOT / 'reports' / '02_EDA.md')
    eda_errors = []
    for heading in ['입력 파일 확인', '컬럼별 자료형과 결측', '수치형 원본 분포',
                    '결측 의미와 이상치 후보', '드론 유형별', '계절별', '고장 유형별',
                    '재현용 실행 코드', '원본 보존 확인']:
        if heading not in report:
            eda_errors.append(f'보고서 항목 누락: {heading}')
    for name in files:
        path = DATA / name
        match = re.search(re.escape(name) + r'\s*\|\s*([a-f0-9]{64})\s*\|', report)
        if not match:
            eda_errors.append(f'기준 해시 없음: {name}')
        elif not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != match.group(1):
            eda_errors.append(f'EDA 당시와 원본 해시가 다름: {name}')
    if eda_errors:
        print('[확인 필요] 2단계 데이터 탐색(EDA)')
        for error in eda_errors:
            print('  - ' + error)
    else:
        print('[기본 확인 통과] 2단계 데이터 탐색(EDA)')
        print('  보고서 필수 항목·原본 해시 일치 확인'.replace('原', '원'))
        print('  제한: 표의 모든 수치 재계산·해석의 타당성 검증은 포함하지 않음')

    prep_errors = []
    try:
        details = check_preparation()
        print('[확인 통과] 3단계 데이터 준비')
        for detail in details:
            print('  ' + detail)
        print('  수작업 기대값·90일 경계·같은 날짜·장비 분리·인덱스 보존 확인')
        print('  미래 기록 불변성·정답 비참조·파일 간 이력 연결·원본 해시 확인')
    except Exception as exc:
        prep_errors.append(f'{type(exc).__name__}: {exc}')
        print('[확인 필요] 3단계 데이터 준비')
        print('  ' + prep_errors[0])

    audit_errors = []
    try:
        check_audit()
        print('[감사 기록 확인 통과] 4단계 규칙 없는 모델 감사')
        print('  과거 보고서·사전 모델·원본 해시 확인(당시 코드 상태는 기록으로 보존)')
        print('  개선 필요: 저장소 독립 재현·장비별 월 선정·기간 경계·검증 증적')
        print('  감사 완료는 모델 승인이나 시험 성능 검증을 뜻하지 않음')
    except Exception as exc:
        audit_errors.append(f'{type(exc).__name__}: {exc}')
        print('[확인 필요] 4단계 규칙 없는 모델 감사')
        print('  ' + audit_errors[0])

    training_errors = []
    try:
        check_training()
        print('[확인 통과] 5단계 규칙 · 스킬로 다시 학습')
        print('  입력·코드 해시·환경 버전·금지 피처·정답 확정 기간 확인')
        print('  검증 모델 재예측·PR-AUC·월별 장비 중복 제거·기준선·비용 기준 재계산 일치')
        print('  검증 말미의 부분·미평가 및 시험 성능 미평가를 모델 정보에 기록')
    except Exception as exc:
        training_errors.append(f'{type(exc).__name__}: {exc}')
        print('[확인 필요] 5단계 규칙 · 스킬로 다시 학습')
        print('  ' + training_errors[0])

    operations_errors=[]
    try:
        check_operations()
        print('[확인 통과] 6단계 운영 기준')
        print('  비용별 기준·월별 최신 기록·용량·초과 대기·예방 점검 구분 확인')
        print('  동률·기준 경계·빈 후보·잘못된 확률·검증 비용 재계산 확인')
        print('  운영 보고서와 학습 번들·실행 코드 근거 일치')
    except Exception as exc:
        operations_errors.append(f'{type(exc).__name__}: {exc}')
        print('[확인 필요] 6단계 운영 기준')
        print('  '+operations_errors[0])

    app_errors=[]
    try:
        check_app()
        print('[확인 통과] 7단계 앱')
        print('  앱 실행·최신 장비 선정·모델 확률·부대별 합계 확인')
        print('  부대·유형·상태·검색·초기화·차트·다운로드·순위/원본 보존 확인')
        print('  시각적 배치 검사는 포함하지 않음')
    except Exception as exc:
        app_errors.append(f'{type(exc).__name__}: {exc}')
        print('[확인 필요] 7단계 앱')
        print('  '+app_errors[0])

    final_errors=[]
    try:
        test_rows,selected_rows=check_deliverables()
        print('[확인 통과] 8단계 스킬 · 보고서 검수')
        print(f'  시험 {test_rows:,}행 전체·순서·날짜 형식·확률 재예측 일치')
        print(f'  재점검 {selected_rows}대·최신 기록·앱 순위·설명·기여도 합 확인')
        print('  분석/계획 보고서 본문·수치·출처·한계 문구·원본/모델 보존 확인')
        print('  시험 정답 미제공: 시험 성능은 미평가')
    except Exception as exc:
        final_errors.append(f'{type(exc).__name__}: {exc}')
        print('[확인 필요] 8단계 스킬 · 보고서 검수')
        print('  '+final_errors[0])
    if (ROOT / 'artifacts' / 'drone_model.joblib').is_file():
        print('참고: 사전 학습 모델은 있음. 재현성·학습 검증 완료를 뜻하지 않음.')
    print('-' * 66)
    print('이 점검은 현재 프로젝트만 검사하며 파일을 생성·수정하지 않습니다.')
    print('다음 할 일:', '위 확인 필요 항목 해결' if errors or eda_errors or prep_errors or audit_errors or training_errors or operations_errors or app_errors or final_errors else '1~8단계 구현·자동점검 완료(표시한 검증 범위·한계 참조)')
    return 1 if errors or eda_errors or prep_errors or audit_errors or training_errors or operations_errors or app_errors or final_errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
