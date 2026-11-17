"""프로젝트 전용 기간 검증 학습. 실행: python scripts/train.py"""
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pdm_lib as lib


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if lib.TRAINING_PATH.exists():
        raise FileExistsError("기존 training_run.joblib 보존: 재실행 전 결과 보관 또는 출력 버전 지정 필요")
    input_paths = [lib.HISTORY_CSV, lib.TEST_CSV, lib.MONTH_CSV]
    original_hash = {p.name: sha(p) for p in input_paths}
    # 모델 학습은 정답 있는 파일만 읽는다. 시험·이번 달 값은 학습에 쓰지 않는다.
    full = lib.add_time_features(lib.clean(lib.load_history()))
    label_end = full.maintenance_date + pd.Timedelta(days=30)
    train = full.loc[(full.maintenance_date <= "2024-06-30") & (label_end < "2024-07-01")].copy()
    valid = full.loc[full.maintenance_date.between("2024-07-01", "2024-12-31")].copy()
    final_data = full.loc[label_end < "2025-01-01"].copy()
    for name, frame in [("학습",train),("검증",valid),("최종 학습",final_data)]:
        if frame.empty or frame[lib.TARGET].nunique()!=2:
            raise ValueError(name+"에 두 정답 클래스가 필요합니다")
        print(f"{name}: {frame.maintenance_date.min():%Y-%m-%d} ~ {frame.maintenance_date.max():%Y-%m-%d}, {len(frame):,}기록")
    validation_model = lib.make_model()
    validation_model.fit(train[lib.FEATURES],train[lib.TARGET])
    valid["prob"] = validation_model.predict_proba(valid[lib.FEATURES])[:,1]
    latest = lib.latest_monthly(valid)
    candidates = latest.loc[latest.maintenance_date + pd.Timedelta(days=30) < "2025-01-01"].copy()
    if candidates[lib.TARGET].nunique()!=2: raise ValueError("검증 후보에 두 클래스 필요")
    latest_index = latest.index
    valid["is_monthly_latest"] = valid.index.isin(latest_index)
    valid["label_mature"] = valid.maintenance_date + pd.Timedelta(days=30) < "2025-01-01"
    grid=[]
    thresholds={}
    for missed_cost in [300,600]:
        options=[]
        for step in range(5,95):
            threshold=step/100
            flag=candidates.prob.ge(threshold)
            missed=int((candidates[lib.TARGET].eq(1)&~flag).sum())
            cost=int(missed*missed_cost+flag.sum()*60)
            grid.append({"missed_cost":missed_cost,"threshold":threshold,"cost":cost})
            options.append((cost,threshold))
        cost,threshold=min(options)
        thresholds[str(missed_cost)]={"threshold":threshold,"cost_manwon":cost}
    back=lib.monthly_topk(candidates,"prob",20).rename(columns={"hits":"model"})
    oldest=lib.monthly_topk(candidates,"equipment_age_years",20).rename(columns={"hits":"oldest"})
    back=back.merge(oldest[["month","oldest"]],on="month",validate="one_to_one")
    base={str(m):min(20,len(g))*g[lib.TARGET].mean() for m,g in candidates.groupby("_month")}
    back["random"]=back.month.map(base)
    all_months=pd.DataFrame({"month":sorted(valid.maintenance_date.dt.strftime("%Y-%m").unique())})
    back=all_months.merge(back,on="month",how="left")
    for c in ["picked","model","oldest","random"]: back[c]=back[c].fillna(0)
    back["eligible_candidates"]=back.month.map(candidates.groupby("_month").size()).fillna(0).astype(int)
    back["latest_candidates"]=back.month.map(latest.groupby("_month").size()).astype(int)
    back["partial_evaluation"]=back.eligible_candidates < back.latest_candidates
    final_model=lib.make_model()
    final_model.fit(final_data[lib.FEATURES],final_data[lib.TARGET])
    card=lib.make_card(final_data,thresholds["300"]["threshold"],candidates,back)
    card["threshold_comparison"]=thresholds
    card["label_policy"]={"horizon_days":30,"validation_origin":"2024-07-01","final_origin":"2025-01-01","condition":"maintenance_date + 30 days < origin","evaluation_cutoff":"2025-01-01","note":"최종 모델에도 같은 정답 확정 조건 적용"}
    card["split_counts"]={"train":len(train),"valid_records":len(valid),"valid_latest":len(latest),"evaluation_candidates":len(candidates),"final_train":len(final_data)}
    card["provenance"]={"input_sha256":original_hash,"source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/"pdm_lib.py",Path(__file__),ROOT/".agents/skills/drone-train/SKILL.md",ROOT/"requirements.txt"]},"python":platform.python_version(),"packages":{p:importlib.metadata.version(p) for p in ["numpy","pandas","scikit-learn","lightgbm","joblib"]},"model_parameters":final_model["model"].get_params(),"command":"python scripts/train.py"}
    assert original_hash=={p.name:sha(p) for p in input_paths},"원본 해시 변경"
    bundle={"model":final_model,"model_card":card,"validation_model":validation_model,"validation_predictions":valid,"threshold_grid":pd.DataFrame(grid),"training_indices":train.index.tolist(),"final_training_indices":final_data.index.tolist()}
    lib.ART.mkdir(exist_ok=True)
    joblib.dump(bundle,lib.TRAINING_PATH)
    loaded=joblib.load(lib.TRAINING_PATH)
    np.testing.assert_allclose(loaded["validation_model"].predict_proba(valid[lib.FEATURES])[:,1],valid.prob,rtol=1e-12,atol=1e-12)
    print("검증 PR-AUC 및 기준선:", json.dumps({k:card["validation"][k] for k in ["pr_auc","oldest_pr_auc","random_pr_auc"]}))
    print("월별 최신 장비 후보 평가(무작위는 기대값):")
    print(back.to_string(index=False))
    print("검증 합계:",card["validation"]["totals"])
    print("검증 위험 기준(운영 확정 전):",thresholds)
    print("시험 성능: 미평가(정답 없음)")
    print("저장·재읽기 검증:",lib.TRAINING_PATH)
    for limit in card["limits"]: print(limit)


if __name__=="__main__":
    main()
