"""실행: python -m streamlit run app.py"""
from pathlib import Path
import sys
import joblib
import pandas as pd
import streamlit as st

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts.app_data import file_signature, score_current_month

st.set_page_config(page_title="드론 재점검 우선순위",page_icon=":material/build:",layout="wide")
st.title("드론 재점검 우선순위")
st.caption("2026년 1월 · 교육용 가상 데이터 · 정비 직후 30일 내 재고장 예측")


@st.cache_resource(max_entries=1)
def load_model(model_digest):
    return joblib.load(ROOT/'artifacts/training_run.joblib')


@st.cache_data(max_entries=1)
def load_scored(signature):
    return score_current_month(load_model(signature[0][1]))


try:
    scored,card,policy=load_scored(file_signature())
except Exception as exc:
    st.error(f"분석 자료를 불러오지 못했습니다: {exc}")
    st.info("터미널에서 python scripts/check.py로 데이터·모델·운영 기준을 확인하세요.")
    st.stop()

st.info(f"위험 표시는 {policy['threshold']:.0%} 이상입니다. 점검은 전체 후보에서 확률 상위 {policy['capacity_per_month']}대를 선정하며, 기준 미만의 선정 대상은 예방 점검으로 구분합니다.")
with st.container(horizontal=True):
    st.metric("전체 후보",f"{len(scored):,}대",border=True)
    st.metric("점검 선정",f"{int(scored.selected.sum()):,}대",border=True)
    st.metric("기준 이상",f"{int(scored.flagged.sum()):,}대",border=True)
    st.metric("초과 대기",f"{int(scored.overflow.sum()):,}대",border=True)

with st.sidebar:
    st.header("목록 조회")
    unit=st.selectbox("부대",["전체"]+sorted(scored.unit_code.unique().tolist()),key="unit")
    kind=st.selectbox("드론 유형",["전체"]+sorted(scored.equipment_type.unique().tolist()),key="kind")
    scope=st.selectbox("점검 구분",["전체","선정 대상","초과 대기","예방 점검","기준 이상"],key="scope")
    st.caption("필터는 조회 범위만 바꿉니다. 전체 순위와 점검 선정은 유지됩니다.")

view=scored.copy()
if unit!="전체": view=view.loc[view.unit_code.eq(unit)]
if kind!="전체": view=view.loc[view.equipment_type.eq(kind)]
if scope=="선정 대상": view=view.loc[view.selected]
elif scope=="초과 대기": view=view.loc[view.overflow]
elif scope=="예방 점검": view=view.loc[view.supplementary]
elif scope=="기준 이상": view=view.loc[view.flagged]

st.subheader("재점검 목록")
st.caption("위험을 올린 요인은 모델의 양의 SHAP 기여도 기준이며, 고장의 원인이나 정비 효과를 입증하지 않습니다.")
columns=['rank','equipment_id','equipment_type','unit_code','maintenance_date','prob','status','reasons']
labels={'rank':'전체 순위','equipment_id':'드론','equipment_type':'유형','unit_code':'부대','maintenance_date':'정비일','prob':'재고장 확률','status':'점검 구분','reasons':'위험을 올린 요인'}
if view.empty:
    st.info("조건에 맞는 장비가 없습니다. 조회 조건을 바꿔 주세요.")
st.dataframe(view[columns].rename(columns=labels),hide_index=True,width="stretch",key="priority_table",alt="드론별 전체 순위와 점검 구분",
    column_config={"재고장 확률":st.column_config.ProgressColumn(min_value=0.0,max_value=1.0,format="percent")})

st.subheader("부대별 요약")
summary=scored.groupby('unit_code',sort=True).agg(후보=('equipment_id','size'),점검선정=('selected','sum'),기준이상=('flagged','sum'),초과대기=('overflow','sum'),예방점검=('supplementary','sum')).reset_index().rename(columns={'unit_code':'부대'})
st.caption("전체 후보 기준 요약입니다. 조회 필터와 관계없이 표시합니다.")
st.dataframe(summary,hide_index=True,key="unit_summary",alt="부대별 후보와 점검 선정 현황")

if not view.empty:
    st.subheader("장비별 정비 기록")
    equipment=st.selectbox("확인할 드론",view.equipment_id.tolist(),key="equipment")
    row=view.loc[view.equipment_id.eq(equipment)].iloc[0]
    details=pd.DataFrame({'항목':['정비 구분','고장 유형','심각도','최근 90일 고장 수','최근 고장 뒤 경과일','예방정비 뒤 비행시간'],'값':[str(row[c]) if pd.notna(row[c]) else '이력 없음' for c in ['maintenance_type','fault_category','severity','fail_count_90d','days_since_last_failure','hours_since_last_pm']]})
    st.dataframe(details,hide_index=True,alt="선택한 드론의 정비 기록과 이력 피처")
    st.caption(str(row.reasons))

with st.expander("검증 성능과 출처"):
    validation=card['validation']
    st.caption("검증 기간의 월별 최신 장비 중 정답이 확정된 후보에 대한 결과입니다. 마지막 달은 부분 평가이며 시험 성능은 미평가입니다.")
    st.table(pd.DataFrame({'선정 기준':['모델','오래된 순','무작위 기준'],'검증 PR-AUC':[validation['pr_auc'],validation['oldest_pr_auc'],validation['random_pr_auc']]}),alt="모델과 기준선의 검증 PR-AUC 비교")
    st.caption("출처: artifacts/training_run.joblib의 최종 모델과 검증 정보, data/data 원본, reports/06_operations.md 운영 정책. 학습·검증 이력은 python scripts/check.py로 확인할 수 있습니다.")
st.subheader("모델 한계")
for limit in card['limits']:
    st.caption(limit)
