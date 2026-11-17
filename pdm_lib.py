"""드론 예측정비 공통 데이터 준비. 입력과 원본 파일을 수정하지 않는다."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "data"
ART = ROOT / "artifacts"
HISTORY_CSV = DATA / "drone_train.csv"
MONTH_CSV = DATA / "drone_this_month.csv"
TEST_CSV = DATA / "drone_test.csv"
MODEL_PATH = ART / "drone_model.joblib"
CARD_PATH = ART / "model_card.json"
TARGET = "failure_within_30days"
FAIL_TYPES = ["사후정비", "긴급정비"]
CAT_COLS = ["equipment_type", "maintenance_type", "fault_category"]
BASE_NUM = ["equipment_age_years", "severity", "downtime_hours", "repair_duration_hours",
            "parts_replaced_count", "maintenance_cost", "maintenance_success",
            "cumulative_operating_hours", "days_since_last_maintenance", "is_first_maintenance"]
TIME_COLS = ["fail_count_90d", "days_since_last_failure", "hours_since_last_pm"]
FEATURES = CAT_COLS + BASE_NUM + TIME_COLS
LEAK_COLS = ["availability_rate"]


def load_history(path=HISTORY_CSV):
    """정비 기록 CSV를 읽어 날짜를 날짜형으로 바꾸고 장비 · 날짜 순으로 정렬한다."""
    df = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["maintenance_date"])
    return df.sort_values(["equipment_id", "maintenance_date"]).reset_index(drop=True)

def clean(df):
    """이상치 · 결측을 처리한 새 DataFrame을 돌려준다 (블록 3). 원본 df는 바꾸지 않고, 행을 지우지 않는다.
    처리 방침은 AGENTS.md '데이터 처리' 규칙을 따른다. 결과에 is_first_maintenance(0/1) 열이 있어야 한다."""
    out = df.copy()
    out["downtime_hours"] = out["downtime_hours"].replace(999, np.nan)
    cost = out["maintenance_cost"].astype(float)
    out["maintenance_cost"] = cost.mask(cost > 10000, cost / 100)
    out[["fault_code", "fault_category"]] = out[["fault_code", "fault_category"]].fillna("N/A")
    out["is_first_maintenance"] = out["days_since_last_maintenance"].isna().astype(int)
    return out

def add_time_features(df):
    """장비마다 지난 기록을 보고 시간 피처 3개를 더한 새 DataFrame을 돌려준다 (블록 3).
    그 정비일까지의 기록만 쓴다(같은 날짜 포함, 뒤 날짜는 쓰지 않는다). 고장 정비 = maintenance_type이 FAIL_TYPES인 것.
      fail_count_90d          그 정비일 기준 최근 90일(90일 전 날짜 포함) 고장 정비 수. 이번 정비도 센다
      days_since_last_failure 가장 최근 고장 정비 뒤 경과일(이번이 고장 정비면 0). 고장 기록이 없으면 NaN
      hours_since_last_pm     가장 최근 예방정비 때의 cumulative_operating_hours와 지금 값의 차(이번이 예방정비면 0).
                              예방정비 기록이 없으면 NaN. 소수 첫째 자리로 반올림
    행 수와 인덱스는 그대로 둔다."""
    out = df.copy()
    fail_count = np.zeros(len(df), dtype=int)
    last_failure_days = np.full(len(df), np.nan)
    last_pm_hours = np.full(len(df), np.nan)

    # 계산용 인덱스는 행 위치로 둔다. 입력 인덱스가 중복되어도 결과를 같은 행에 돌려놓는다.
    history = df[["equipment_id", "maintenance_date", "maintenance_type",
                  "cumulative_operating_hours"]].reset_index(drop=True).copy()
    history["maintenance_date"] = pd.to_datetime(history["maintenance_date"])
    for _, records in history.groupby("equipment_id", sort=False, dropna=False):
        records = records.sort_values("maintenance_date", kind="stable")
        positions = records.index.to_numpy()
        dates = records["maintenance_date"].to_numpy(dtype="datetime64[ns]")
        failure_dates = dates[records["maintenance_type"].isin(FAIL_TYPES).to_numpy()]

        # 오른쪽 경계를 포함해 이번 정비와 같은 날짜의 고장 기록도 모두 센다.
        right = np.searchsorted(failure_dates, dates, side="right")
        left = np.searchsorted(failure_dates, dates - np.timedelta64(90, "D"), side="left")
        fail_count[positions] = right - left
        has_failure = right > 0
        last_failure_days[positions[has_failure]] = (
            dates[has_failure] - failure_dates[right[has_failure] - 1]
        ) / np.timedelta64(1, "D")

        is_pm = records["maintenance_type"].eq("예방정비").to_numpy()
        pm_dates = dates[is_pm]
        hours = records["cumulative_operating_hours"].to_numpy(dtype=float)
        pm_hours = hours[is_pm]
        pm_right = np.searchsorted(pm_dates, dates, side="right")
        has_pm = pm_right > 0
        last_pm_hours[positions[has_pm]] = np.round(
            hours[has_pm] - pm_hours[pm_right[has_pm] - 1], 1
        )
        last_pm_hours[positions[is_pm]] = 0.0

    out["fail_count_90d"] = fail_count
    out["days_since_last_failure"] = last_failure_days
    out["hours_since_last_pm"] = last_pm_hours
    return out

def prepare_data():
    """각 CSV를 원래 행 순서로 반환. 이력은 연결하되 정답은 피처 계산에 사용하지 않는다."""
    names = {"train": HISTORY_CSV, "test": TEST_CSV, "month": MONTH_CSV}
    parts = []
    source_dtypes = {}
    for name, path in names.items():
        part = pd.read_csv(path, encoding="utf-8-sig", parse_dates=["maintenance_date"])
        source_dtypes[name] = part.dtypes.to_dict()
        part["_source"] = name
        part["_row"] = np.arange(len(part))
        parts.append(part)
    combined = add_time_features(clean(pd.concat(parts, ignore_index=True)))
    result = {}
    for name in names:
        frame = combined.loc[combined["_source"].eq(name)].sort_values("_row")
        frame = frame.drop(columns=["_source", "_row"]).reset_index(drop=True)
        if name == "train":
            frame[TARGET] = frame[TARGET].astype(source_dtypes[name][TARGET])
        if name != "train":
            frame = frame.drop(columns=[TARGET], errors="ignore")
        result[name] = frame
    return result


def make_model(cat_cols=CAT_COLS):
    """범주형은 원-핫, 수치형은 그대로 LightGBM에 넣는 파이프라인 (결측은 LightGBM이 처리)."""
    from lightgbm import LGBMClassifier
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols)],
                            remainder="passthrough", verbose_feature_names_out=False).set_output(transform="pandas")
    lgbm = LGBMClassifier(n_estimators=300, learning_rate=0.03, num_leaves=4, min_child_samples=60, reg_lambda=5.0,
                          subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=42, verbose=-1)
    return Pipeline([("pre", pre), ("model", lgbm)])


TRAINING_PATH = ART / "training_run.joblib"


def latest_monthly(df):
    """월별 장비 최신 기록. 날짜 동률은 원래 행 순서의 마지막 기록."""
    out = df.copy()
    out["_month"] = out["maintenance_date"].dt.strftime("%Y-%m")
    return out.sort_values("maintenance_date", kind="stable").drop_duplicates(
        ["_month", "equipment_id"], keep="last")


def monthly_topk(df, score_col, k=20):
    """월별 최신 기록 후보 중 점수가 높은 장비 선정. 정답 있는 평가용."""
    rows = []
    for month, group in latest_monthly(df).groupby("_month", sort=True):
        selected = group.sort_values([score_col, "equipment_id"], ascending=[False, True], kind="stable").head(k)
        rows.append({"month": month, "picked": len(selected), "hits": int(selected[TARGET].sum())})
    return pd.DataFrame(rows, columns=["month", "picked", "hits"])


def make_card(df, threshold, test, back, capacity=20, cost=(300, 60)):
    """test 인자는 호환 이름이며 실제 입력은 정답 확정된 검증 후보다. 시험 성능을 만들지 않는다."""
    from sklearn.metrics import average_precision_score
    return {
        "model": "LightGBM (pdm_lib.make_model)",
        "target": "정비 뒤 30일 안 재고장(사후 · 긴급정비) 여부",
        "trained_on": f"{df.maintenance_date.min():%Y-%m-%d} ~ {df.maintenance_date.max():%Y-%m-%d} ({len(df):,}건)",
        "features": FEATURES,
        "threshold": float(threshold),
        "capacity_per_month": capacity,
        "threshold_rule": {"missed_cost_manwon": cost[0], "inspection_cost_manwon": cost[1], "scope": "검증 최신 장비 후보, 용량 적용 전 위험 표시 비용"},
        "validation": {
            "pr_auc": float(average_precision_score(test[TARGET], test["prob"])),
            "random_pr_auc": float(test[TARGET].mean()),
            "oldest_pr_auc": float(average_precision_score(test[TARGET], test.equipment_age_years)),
            "monthly": back.to_dict(orient="records"),
            "totals": {c: float(back[c].sum()) for c in ["model", "oldest", "random"]},
            "scope": "월별 장비 최신 기록 중 정답 관측창이 끝난 후보. 검증 기준 선택에 사용한 표본으로 독립 시험 성능이 아님.",
        },
        "test_2025_status": "정답 미제공: 시험 성능 미평가. 시험 자료는 모델 학습에 사용하지 않음.",
        "limits": ["교육용 가상 데이터로 학습했다. 실제 장비에 그대로 쓰지 않는다.",
                   "확률은 '정비 뒤 30일' 기준이다. 정비 기록이 없는 장비는 판단하지 않는다.",
                   "최종 판단은 정비 담당자가 한다. 모델은 점검 순서를 정하는 참고 자료다.",
                   "정답 확정일이 없어 정비일에 관측 기간을 더한 보수적 기준을 적용했다. 제공 정답의 생성·관측 완결성은 확인하지 못했다.",
                   "검증 말미의 미확정 후보를 제외했으므로 월별 비교의 마지막 달은 부분 평가 또는 미평가일 수 있다.",
                   "비용 기준은 위험 표시용이며 월 작업 용량을 적용한 운영 정책은 별도 검토가 필요하다."]
    }
