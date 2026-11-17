"""검증 기반 운영 기준. 작성: python scripts/operations.py --write"""
import argparse
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "06_operations.md"
TRAINING_PATH = ROOT / "artifacts" / "training_run.joblib"


def apply_policy(scored, threshold, capacity):
    """월별 장비 최신 기록을 위험 표시하고 확률 상위 capacity개를 선정한다."""
    if not 0 <= threshold <= 1 or not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
        raise ValueError("유효한 임계값과 양의 정수 용량이 필요합니다")
    out = scored.copy()
    required = {"equipment_id", "maintenance_date", "prob"}
    if not required.issubset(out.columns):
        raise ValueError("필수 컬럼 누락")
    out["maintenance_date"] = pd.to_datetime(out["maintenance_date"], errors="raise")
    if out.equipment_id.isna().any() or out.maintenance_date.isna().any():
        raise ValueError("장비 번호·정비일 결측")
    out["prob"] = pd.to_numeric(out["prob"], errors="raise")
    if not np.isfinite(out.prob.to_numpy(dtype=float)).all() or not out.prob.between(0, 1).all():
        raise ValueError("확률은 유한한 0~1 값이어야 합니다")
    out["month"] = out.maintenance_date.dt.strftime("%Y-%m")
    out = out.sort_values("maintenance_date", kind="stable").drop_duplicates(["month", "equipment_id"], keep="last")
    out = out.sort_values(["month", "prob", "equipment_id"], ascending=[True, False, True], kind="stable")
    out["rank"] = out.groupby("month").cumcount() + 1
    out["flagged"] = out.prob.ge(threshold)
    out["selected"] = out["rank"].le(capacity)
    out["overflow"] = out.flagged & ~out.selected
    out["supplementary"] = out.selected & ~out.flagged
    return out.reset_index(drop=True)


def build_evidence():
    bundle = joblib.load(TRAINING_PATH)
    card = bundle["model_card"]
    valid = bundle["validation_predictions"]
    candidates = valid.loc[valid.is_monthly_latest & valid.label_mature].copy()
    comparisons = []
    grid = bundle["threshold_grid"]
    for missed_cost in [300, 600]:
        best = grid.loc[grid.missed_cost.eq(missed_cost)].sort_values(["cost", "threshold"]).iloc[0]
        saved = card["threshold_comparison"][str(missed_cost)]
        assert saved["threshold"] == best.threshold and saved["cost_manwon"] == best.cost
        comparisons.append({"missed_cost_manwon": missed_cost, "threshold": float(best.threshold), "validation_cost_manwon": int(best.cost)})
    policy = {"threshold": comparisons[0]["threshold"], "capacity_per_month": int(card["capacity_per_month"]),
              "selection": "fixed_capacity_top_probability", "latest_record": "per_equipment_per_month",
              "tie_break": "equipment_id_ascending", "same_day_tie": "last_input_record",
              "comparison": ">=", "fill_below_threshold": True,
              "overflow_action": "담당자가 추가 용량·재점검 시기를 판단"}
    rows = []
    labels = "failure_within_30days"
    for entry in card["validation"]["monthly"]:
        month = entry["month"]
        group = candidates.loc[candidates.maintenance_date.dt.strftime("%Y-%m").eq(month)]
        assigned = apply_policy(group, policy["threshold"], policy["capacity_per_month"])
        old = group.sort_values(["equipment_age_years", "equipment_id"], ascending=[False, True], kind="stable").head(policy["capacity_per_month"])
        positives = int(group[labels].sum())
        selected = assigned.selected
        hit = int(assigned.loc[selected, labels].sum())
        flagged_hits = int(assigned.loc[assigned.flagged, labels].sum())
        picked = int(selected.sum())
        random_hits = picked * group[labels].mean() if len(group) else 0.0
        row = {"month": month, "eligible": len(group), "partial_evaluation": bool(entry["partial_evaluation"]),
               "selected": picked, "model_hits": hit, "oldest_hits": int(old[labels].sum()), "random_hits_expected": float(random_hits),
               "flagged": int(assigned.flagged.sum()), "overflow": int(assigned.overflow.sum()), "supplementary": int(assigned.supplementary.sum())}
        for cost in [300, 600]:
            row[f"model_cost_{cost}"] = (positives-hit)*cost + picked*60
            row[f"oldest_cost_{cost}"] = (positives-row["oldest_hits"])*cost + len(old)*60
            row[f"random_cost_{cost}_expected"] = (positives-random_hits)*cost + picked*60
            row[f"threshold_only_cost_{cost}"] = (positives-flagged_hits)*cost + int(assigned.flagged.sum())*60
        rows.append(row)
    return {"policy": policy, "threshold_comparison": comparisons, "validation_monthly": rows,
            "totals": {key: float(sum(row[key] for row in rows)) for key in rows[0] if key not in ["month", "partial_evaluation"]},
            "provenance": {"command": "python scripts/operations.py --write", "training_sha256": hashlib.sha256(TRAINING_PATH.read_bytes()).hexdigest(),
                           "operations_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           "input": "artifacts/training_run.joblib: validation_predictions, threshold_grid, model_card"},
            "limits": card["limits"]}


def render(evidence):
    p = evidence["policy"]
    compare = evidence["threshold_comparison"]
    lines = ["# 6단계 운영 기준", "## 기준과 출처",
        "모든 계산 수치의 출처는 `python scripts/operations.py --write` 실행과 아래 근거 JSON이다. 입력은 학습 번들의 검증 예측·비용 비교·모델 정보다. 이번 달 장비의 위험도·순위는 산출하지 않았다.",
        "## 위험 표시 기준",
        "| 누락 비용(만원) | 기준 | 검증 표시 비용(만원) |", "| --- | --- | --- |"]
    for row in compare:
        lines.append(f"| {row['missed_cost_manwon']} | {row['threshold']:.2f} | {row['validation_cost_manwon']} |")
    lines += ["위 비교는 용량을 제한하지 않은 위험 표시 비용이다. 검증 후보에서 비용을 최소화하고, 비용 동점이면 낮은 기준을 선택했다. 이번 검증에서는 누락 비용을 높여도 선택된 기준이 같았다. 이를 다른 데이터에도 성립하는 결론으로 일반화하지 않는다.",
        "## 실제 선정 정책",
        f"- 위험 표시는 확률이 {p['threshold']:.2f} 이상일 때 적용한다. 기준과 같은 값도 포함한다.",
        f"- 월별 장비 최신 기록을 후보로 삼고 확률 상위 {p['capacity_per_month']}대를 선정한다. 후보가 더 적으면 후보 전부만 선정한다.",
        "- 위험 기준 이상이 용량보다 많으면 확률이 높은 장비부터 선정하고 나머지를 초과 대기로 표시한다. 같은 확률이면 장비 번호 오름차순으로 정한다.",
        "- 기준 이상이 용량보다 적으면 나머지는 확률 순으로 예방 점검 대상으로 채우되, 기준 이상 장비와 별도 표시한다. 이는 비용 최소화 정책이 아니라 과제의 정해진 점검 용량을 사용하는 정책이다.",
        "- 초과 대기는 안전 판정이 아니다. 담당자가 현장 상태에 따라 추가 용량 또는 조기 재점검을 판단한다. 다음 달로 자동 이월하거나 미래 기록이 없는 상태에서 일정을 확정하지 않는다.",
        "- 같은 날짜의 복수 기록은 입력 순서의 마지막 기록을 사용한다. 월별 계획은 해당 월 기록이 준비된 시점의 최신 기록을 기준으로 한다.",
        "## 검증 정책 비교",
        "아래 JSON의 validation_monthly와 totals에서 모델·오래된 순·무작위 기대값에 동일한 최신 장비 후보와 용량을 적용했다. 비용은 미선정 재고장 기록의 누락 비용과 선정 장비의 점검 비용을 합산한 교육용 가정이며 실제 예방 효과를 입증한 값이 아니다. threshold_only 비용은 위험 표시만 수행했을 때의 별도 비교다.",
        "| 월 | 평가 후보 | 선정 | 모델 적중 | 오래된 순 적중 | 무작위 기대 적중 | 부분 평가 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in evidence["validation_monthly"]:
        lines.append(f"| {row['month']} | {row['eligible']} | {row['selected']} | {row['model_hits']} | {row['oldest_hits']} | {row['random_hits_expected']:.3f} | {row['partial_evaluation']} |")
    lines += ["수치는 검증 자료에 한정된다. 마지막 달은 정답 확정 조건 때문에 부분 평가이며, 전체 월 또는 시험 성능으로 해석하지 않는다. 무작위는 실제 추첨 결과가 아닌 기대값이다.",
        "## 적용 범위와 검증",
        "기준은 검증 모델로 선택했으며 최종 모델에서는 확률 분포가 달라질 수 있다. 최종 모델의 기준 적합성 또는 실제 운영 효과를 시험으로 확인하지 못했다. 시험 데이터 정답이 없으므로 시험 성능을 보고하지 않는다. 기준은 유지하고 후속 정답이 확보되면 재검증한다.",
        "운영 함수는 여러 달·장비 중복·동률·기준 경계·초과 대기·빈 후보·비정상 확률을 검사한다. 학습 번들과 원본을 수정하지 않는다.",
        "## 운영 근거 원출력", "<!-- OPERATIONS_FACTS -->", "```json", json.dumps(evidence, ensure_ascii=False, indent=2), "```",
        "## 모델 한계 — 학습 번들 model_card.limits 원문"]
    lines += ["- " + item for item in evidence["limits"]]
    lines += ["운영 정책 적용 후에도 최종 판단은 정비 담당자가 한다."]
    return "\n\n".join(lines) + "\n"


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    evidence = build_evidence()
    if args.write:
        if REPORT_PATH.exists():
            raise FileExistsError("기존 운영 보고서를 덮어쓰지 않습니다")
        REPORT_PATH.write_text(render(evidence), encoding="utf-8")
        print("운영 기준 보고서:", REPORT_PATH)
    print(json.dumps({"policy": evidence["policy"], "threshold_comparison": evidence["threshold_comparison"], "validation_totals": evidence["totals"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
