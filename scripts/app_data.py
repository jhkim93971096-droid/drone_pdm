"""앱과 후속 위험 분석에서 공유할 읽기 전용 이번 달 점수 계산."""
import hashlib
import json
import re
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pdm_lib as lib
from scripts.operations import apply_policy

ROOT = Path(__file__).resolve().parents[1]
LABELS = {"equipment_type":"드론 유형", "maintenance_type":"정비 구분", "fault_category":"고장 유형",
          "equipment_age_years":"경과연수", "severity":"고장 심각도", "downtime_hours":"운용중단 시간",
          "repair_duration_hours":"수리 시간", "parts_replaced_count":"교체 부품 수", "maintenance_cost":"정비 비용",
          "maintenance_success":"정비 성공 여부", "cumulative_operating_hours":"누적 비행시간",
          "days_since_last_maintenance":"직전 정비 뒤 경과일", "is_first_maintenance":"첫 정비 여부",
          "fail_count_90d":"최근 90일 고장 수", "days_since_last_failure":"최근 고장 뒤 경과일",
          "hours_since_last_pm":"예방정비 뒤 비행시간"}


def file_signature():
    paths=[lib.TRAINING_PATH,lib.HISTORY_CSV,lib.TEST_CSV,lib.MONTH_CSV,ROOT/'reports/06_operations.md',ROOT/'scripts/operations.py']
    return tuple((str(p),hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths)


def load_policy():
    report=(ROOT/'reports/06_operations.md').read_text(encoding='utf-8-sig')
    match=re.search(r'<!-- OPERATIONS_FACTS -->\s*```json\s*(.*?)\s*```',report,re.S)
    if not match: raise ValueError('운영 기준 근거가 없습니다. 6단계를 확인하세요.')
    facts=json.loads(match.group(1))
    if facts['provenance']['training_sha256']!=hashlib.sha256(lib.TRAINING_PATH.read_bytes()).hexdigest():
        raise ValueError('운영 기준과 학습 모델이 다릅니다. 재검증이 필요합니다.')
    if facts['provenance']['operations_sha256']!=hashlib.sha256((ROOT/'scripts/operations.py').read_bytes()).hexdigest():
        raise ValueError('운영 코드가 변경되었습니다. 재검증이 필요합니다.')
    return facts['policy']


def explain(model, frame):
    transformed=model['pre'].transform(frame[lib.FEATURES])
    raw=model['model'].booster_.predict(transformed,pred_contrib=True)
    contributions=pd.DataFrame(raw[:,:-1],columns=transformed.columns,index=frame.index)
    grouped={col:next((name for name in lib.CAT_COLS if col.startswith(name+'_')),col) for col in transformed.columns}
    values=contributions.T.groupby(grouped,sort=False).sum().T
    descriptions=[]
    for index in frame.index:
        positive=values.loc[index].loc[values.loc[index].gt(0)].nlargest(3)
        parts=[]
        for feature in positive.index:
            value=frame.at[index,feature]
            text='결측' if pd.isna(value) else f'{value:g}' if isinstance(value,(float,np.floating)) else str(value)
            parts.append(f'{LABELS.get(feature,feature)}({text})')
        descriptions.append(', '.join(parts) if parts else '양의 기여 요인 없음')
    return descriptions


def score_current_month(bundle):
    card=bundle['model_card']
    for name,digest in card['provenance']['input_sha256'].items():
        if hashlib.sha256((lib.DATA/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('학습 이후 입력 데이터 변경: '+name)
    policy=load_policy()
    month=lib.prepare_data()['month']
    if month.empty: raise ValueError('이번 달 정비 기록이 없습니다.')
    if set(month.maintenance_date.dt.strftime('%Y-%m'))!={'2026-01'}:
        raise ValueError('실습 대상 월과 데이터 기간이 다릅니다.')
    month=month.sort_values('maintenance_date',kind='stable').drop_duplicates('equipment_id',keep='last').copy()
    model=bundle['model']
    if list(model.feature_names_in_)!=lib.FEATURES: raise ValueError('모델 입력 피처 불일치')
    month['prob']=model.predict_proba(month[lib.FEATURES])[:,1]
    month['reasons']=explain(model,month)
    scored=apply_policy(month,policy['threshold'],policy['capacity_per_month'])
    scored['status']=np.select([scored.overflow,scored.supplementary,scored.selected],['초과 대기','예방 점검','우선 점검'],default='관찰')
    return scored,card,policy
