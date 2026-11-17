"""드론 재점검 관제. 실행: python -m streamlit run app.py"""
from pathlib import Path
import sys
from typing import cast
import altair as alt
import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts.app_data import file_signature, score_current_month

st.set_page_config(page_title="AERIS | 드론 재점검 관제", page_icon=":material/flight:", layout="wide")


@st.cache_resource(max_entries=1)
def load_model(model_digest):
    return joblib.load(ROOT / "artifacts/training_run.joblib")


@st.cache_data(max_entries=1)
def load_scored(signature):
    return score_current_month(load_model(signature[0][1]))


def reset_filters():
    for key in ["unit", "kind", "scope"]:
        st.session_state[key] = "전체"
    st.session_state["search"] = ""


def number(value, suffix=""):
    return "이력 없음" if pd.isna(value) else f"{value:g}{suffix}"


with st.sidebar:
    st.title("AERIS", icon=":material/flight:")
    st.caption("DRONE MAINTENANCE INTELLIGENCE")
    st.space("small")
    st.badge("재점검 관제", icon=":material/space_dashboard:", color="green")
    st.caption("정비 기록을 다음 점검의 근거로.")
    filters = st.container()
    st.space("medium")
    st.caption("분석 대상 · 2026년 1월")
    st.caption("교육용 가상 데이터\n\n최종 판단은 정비 담당자가 합니다.")

hero, export = st.columns([4, 1], vertical_alignment="bottom")
with hero:
    st.caption("AERIS  /  FLEET INTELLIGENCE")
    st.title("다음 점검의 기준.")
    st.caption("드론 재점검 관제 · 정비 직후 30일 내 재고장 예측")
with export:
    report = ROOT / "reports/2026-01_재점검계획.docx"
    if report.is_file():
        st.download_button("재점검 계획 Word", report.read_bytes(), file_name=report.name,
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           icon=":material/download:", width="stretch", key="download_plan")

try:
    scored, card, policy = load_scored(file_signature())
except Exception as exc:
    st.error(f"분석 자료를 불러오지 못했습니다: {exc}")
    st.info("터미널에서 python scripts/check.py로 데이터·모델·운영 기준을 확인하세요.")
    st.stop()

with st.container(horizontal=True):
    st.badge("2026년 1월", icon=":material/calendar_month:", color="blue")
    st.badge("모델 분석 완료", icon=":material/check_circle:", color="green")
    st.badge("교육용 가상 데이터", color="gray")

with filters:
    st.subheader("조회 조건")
    unit = st.selectbox("부대", ["전체"] + sorted(scored.unit_code.unique().tolist()), key="unit")
    kind = st.selectbox("드론 유형", ["전체"] + sorted(scored.equipment_type.unique().tolist()), key="kind")
    scope = st.selectbox("점검 구분", ["전체", "선정 대상", "초과 대기", "예방 점검", "기준 이상"], key="scope")
    search = st.text_input("드론 번호 검색", placeholder="예: DR-0115", key="search")
    st.button("조회 조건 초기화", on_click=reset_filters, icon=":material/restart_alt:", width="stretch")
    st.caption("필터는 조회만 변경합니다. 전체 순위와 점검 선정은 유지됩니다.")

view = scored.copy()
if unit != "전체": view = view.loc[view.unit_code.eq(unit)]
if kind != "전체": view = view.loc[view.equipment_type.eq(kind)]
if scope == "선정 대상": view = view.loc[view.selected]
elif scope == "초과 대기": view = view.loc[view.overflow]
elif scope == "예방 점검": view = view.loc[view.supplementary]
elif scope == "기준 이상": view = view.loc[view.flagged]
if search.strip(): view = view.loc[view.equipment_id.str.contains(search.strip(), case=False, regex=False)]

overview_tab, list_tab, detail_tab, model_tab = st.tabs([
    "① 관제 현황", "② 재점검 목록", "③ 장비별 근거", "④ 검증·모델 정보"
])

with overview_tab:
    with st.grid(4, gap="medium"):
        st.metric("전체 후보", f"{len(scored):,}대", border=True, help="이번 달 장비별 최신 정비 기록")
        st.metric("점검 선정", f"{int(scored.selected.sum()):,}대", border=True, help="전체 후보 중 확률 순으로 선정")
        st.metric("기준 이상", f"{int(scored.flagged.sum()):,}대", border=True, help=f"재고장 확률 {policy['threshold']:.0%} 이상")
        st.metric("초과 대기", f"{int(scored.overflow.sum()):,}대", border=True, help="기준 이상이지만 이번 점검 용량을 초과한 장비")

    if scored.overflow.any():
        st.warning(f"기준 이상 장비 중 {int(scored.overflow.sum())}대가 점검 용량을 초과했습니다. 담당자의 추가 점검 판단이 필요합니다.", icon=":material/pending_actions:")
    else:
        st.caption("현재 기준 이상 장비는 모두 점검 용량 안에 포함되어 있습니다.")

    st.space("small")
    chart_left, chart_right = st.columns([1, 1.35], gap="medium")
    with chart_left, st.container(border=True):
        st.subheader("확률 분포", icon=":material/monitoring:")
        st.caption("전체 후보 기준 · 점선은 위험 표시 기준")
        hist = cast(alt.Chart, alt.Chart(scored).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)).encode(
            x=alt.X('prob:Q', bin=alt.Bin(step=0.1, extent=[0,1]), title="재고장 확률", axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0,1])),
            y=alt.Y('count():Q', title="장비 수", axis=alt.Axis(tickMinStep=1)),
            tooltip=[alt.Tooltip('count():Q', title="장비 수")])
        threshold = cast(alt.Chart, alt.Chart(pd.DataFrame({'threshold':[policy['threshold']]})).mark_rule(strokeDash=[5,5],color='#D99630',strokeWidth=2)).encode(x='threshold:Q')
        st.altair_chart((hist + threshold).properties(height=235), key="risk_distribution", alt="드론 재고장 확률 분포와 위험 표시 기준")

    summary = scored.groupby('unit_code',sort=True).agg(후보=('equipment_id','size'),점검선정=('selected','sum'),기준이상=('flagged','sum'),초과대기=('overflow','sum'),예방점검=('supplementary','sum')).reset_index().rename(columns={'unit_code':'부대'})
    with chart_right, st.container(border=True):
        st.subheader("부대별 점검 현황", icon=":material/hub:")
        st.caption("전체 후보 기준 · 필터와 관계없이 유지됩니다")
        workloads=scored.groupby(['unit_code','status']).size().reset_index(name='장비 수').rename(columns={'unit_code':'부대','status':'점검 구분'})
        chart=cast(alt.Chart, alt.Chart(workloads).mark_bar(cornerRadiusTopLeft=3,cornerRadiusTopRight=3)).encode(
            x=alt.X('부대:N',title=None,axis=alt.Axis(labelAngle=-35)),
            y=alt.Y('장비 수:Q',title="장비 수",axis=alt.Axis(tickMinStep=1)),
            color=alt.Color('점검 구분:N',scale=alt.Scale(domain=['우선 점검','초과 대기','예방 점검','관찰']),legend=alt.Legend(orient='top',title=None)),
            tooltip=['부대:N','점검 구분:N','장비 수:Q'])
        st.altair_chart(chart.properties(height=235),key="fleet_workload",alt="부대별 점검 선정과 초과 대기 현황")


    with st.expander("부대별 상세 집계", icon=":material/table_chart:"):
        st.dataframe(summary,hide_index=True,key="unit_summary",alt="전체 후보 기준의 부대별 점검 집계")

with list_tab, st.container(border=True):
    st.subheader("재점검 우선순위", icon=":material/format_list_numbered:")
    st.caption(f"조회 {len(view)}대 / 전체 {len(scored)}대 · 표시 기준 {policy['threshold']:.0%} 이상 · 월 용량 {policy['capacity_per_month']}대")
    columns = ['rank', 'equipment_id', 'equipment_type', 'unit_code', 'maintenance_date', 'prob', 'status', 'reasons']
    labels = {'rank':'전체 순위','equipment_id':'드론','equipment_type':'유형','unit_code':'부대','maintenance_date':'정비일','prob':'재고장 확률','status':'점검 구분','reasons':'위험을 올린 요인'}
    if view.empty: st.info("조건에 맞는 장비가 없습니다. 조회 조건을 바꿔 주세요.")
    st.dataframe(view[columns].rename(columns=labels), hide_index=True, width="stretch", height=500,
        key="priority_table", alt="전체 순위를 유지한 드론 재점검 목록",
        column_config={
            "전체 순위":st.column_config.NumberColumn(width="small", format="%d", pinned=True),
            "드론":st.column_config.TextColumn(pinned=True),
            "재고장 확률":st.column_config.ProgressColumn(min_value=0.0, max_value=1.0, format="percent", width="medium"),
            "정비일":st.column_config.DateColumn(format="YYYY-MM-DD"),
            "위험을 올린 요인":st.column_config.TextColumn(width="large")})
    st.caption("확률은 점검 순서의 참고값입니다. 위험 요인은 모델의 기여도이며 고장 원인을 입증하지 않습니다.")


with detail_tab:
    st.subheader("장비별 근거", icon=":material/radar:")
    st.caption("조회 조건에 맞는 드론의 최신 정비 기록과 위험 요인을 확인합니다.")
    if view.empty:
        st.info("조건에 맞는 장비가 없습니다. 사이드바의 조회 조건을 바꿔 주세요.")
    else:
        detail_left, detail_right = st.columns([1, 1.4], gap="medium")
        with detail_left, st.container(border=True):
            equipment = st.selectbox("확인할 드론", view.equipment_id.tolist(), key="equipment")
            row = view.loc[view.equipment_id.eq(equipment)].iloc[0]
            st.badge(str(row.status), color="orange" if row.overflow else "green" if row.selected else "gray")
            st.metric("30일 내 재고장 확률", f"{row.prob:.1%}")
            st.caption(f"전체 {int(row['rank'])}위 · {row.equipment_type} · {row.unit_code}")
            st.progress(float(row.prob), text=f"위험 표시 기준 {policy['threshold']:.0%}")
            st.caption("확률은 점검 우선순위의 참고값이며 최종 판단은 정비 담당자가 합니다.")
        with detail_right, st.container(border=True):
            st.markdown("**위험을 올린 요인**")
            for reason in str(row.reasons).split(", "):
                st.markdown(f":orange-badge[{reason}]")
            st.caption("기여도가 큰 양의 요인 순서 · 인과관계 아님")
            st.markdown("**정비 이력**")
            st.table({"최신 정비":f"{row.maintenance_date:%Y-%m-%d}","정비 구분":str(row.maintenance_type),
                      "고장 유형":str(row.fault_category),"최근 고장 이력":number(row.fail_count_90d,"건 / 90일"),
                      "최근 고장 뒤 경과":number(row.days_since_last_failure,"일"),
                      "예방정비 뒤 비행":number(row.hours_since_last_pm,"시간")},
                     width="stretch",alt="선택한 드론의 최신 정비 기록")

with model_tab:
    st.subheader("검증 성능과 분석 출처", icon=":material/verified:")
    validation=card['validation']
    st.caption("검증 기간의 월별 최신 장비 중 정답 관측창이 끝난 후보에 대한 결과입니다. 마지막 달은 부분 평가이며 시험 성능은 미평가입니다.")
    st.table(pd.DataFrame({'선정 기준':['모델','오래된 순','무작위 기준'],'검증 PR-AUC':[validation['pr_auc'],validation['oldest_pr_auc'],validation['random_pr_auc']]}),alt="모델과 기준선의 검증 PR-AUC")
    st.caption("출처: artifacts/training_run.joblib의 최종 모델과 검증 정보, data/data 원본, reports/06_operations.md 운영 정책.")
    st.subheader("모델 한계와 판단 원칙", icon=":material/info:")
    for limit in card['limits']: st.caption(limit)

st.caption("AERIS · 교육용 드론 예측정비 · 최종 판단은 정비 담당자가 합니다.")
