# 드론 예측정비 분석 보고서

## 목적과 출처

교육용 드론 정비 직후 재고장 예측 실습이다. 모든 수치는 `python .agents/skills/pdm-risk/scripts/score.py --write-analysis`와 아래 ANALYSIS_FACTS 원출력에서 가져왔다. 분포·결측·계절별 세부 패턴은 reports/02_EDA.md를 함께 참조한다.

## 데이터 처리와 근거

| 항목 | 기록 수 | 처리 |
| --- | --- | --- |
| 가동중단 999 | 4 | 미입력 코드로 결측 처리; 행 보존 |
| 비용 >10000 | 5 | 기존 실습 자릿수 오류 규칙에 따라 100으로 나눔 |
| 고장 유형 결측 | 1707 | EDA에서 예방정비와 일치; 코드·유형을 N/A로 구분 |
| 직전 정비 경과일 결측 | 150 | 관측 내 첫 기록; 결측 유지·첫 정비 표시 추가 |
| 원본→처리 행 수 | 2346 → 2346 | 행 삭제 없음 |

출처: ANALYSIS_FACTS.cleaning. 시간 피처는 각 정비일까지의 이력만 사용하고 시험·이번 달 피처에는 앞 기간 기록을 연결한다. 원본 CSV는 수정하지 않았다.

## 입력 컬럼과 제외 이유

입력은 ANALYSIS_FACTS.features의 공통 FEATURES로 한정했다. availability_rate는 월 전체 가동률로 예측 시점 이후 정보를 포함할 수 있어 제외했다. equipment_id·unit_code는 식별자이며 maintenance_date는 기간 분할용이다. fault_code는 fault_category로 대신했다. 정답은 모델 입력에서 제외했다.

## 기간 분할과 정답 확정

학습 후보는 2024-06-30까지, 검증 후보는 2024년 하반기다. 정답 확정일 미제공에 따라 정비일에 관측창을 더한 값이 기준일보다 앞선 기록만 사용했다. 기준일·관측창은 ANALYSIS_FACTS.label_policy가 출처다. 원본을 삭제하지 않고 학습·평가 사용 여부만 구분했다.

| 구분 | 기록 수 |
| --- | --- |
| train | 1611 |
| valid_records | 643 |
| valid_latest | 497 |
| evaluation_candidates | 413 |
| final_train | 2223 |

출처: ANALYSIS_FACTS.split_counts. train은 학습, valid_records는 검증 원본, valid_latest는 월별 최신 후보, evaluation_candidates는 정답 확정 후 평가 후보, final_train은 최종 학습 기록이다.

최종 학습: 2023-01-01 ~ 2024-12-01 (2,223건). 출처: ANALYSIS_FACTS.trained_on. 전체 학습 모델을 검증 데이터에 다시 적용한 성능으로 대체하지 않았다.

## 검증 성능과 기준선

| 기준 | PR-AUC | 월별 선정 적중 합계 |
| --- | --- | --- |
| 모델 | 0.501276 | 30.0 |
| 오래된 순 | 0.152863 | 16.0 |
| 무작위 | 0.106538 | 10.890758 |

출처: ANALYSIS_FACTS.validation. PR-AUC는 Average Precision이다. 무작위 PR-AUC는 양성 비율 기준이고 적중은 추첨 결과가 아닌 기대값이다. 월별 최신 장비를 먼저 고른 뒤 정답 확정 조건을 적용해 평가 후보를 통일했다.

| 월 | 평가 후보 | 선정 | 모델 적중 | 오래된 순 | 무작위 기대 적중 | 부분 평가 |
| --- | --- | --- | --- | --- | --- | --- |
| 2024-07 | 77 | 20 | 6 | 4 | 2.337662 | False |
| 2024-08 | 87 | 20 | 4 | 2 | 1.609195 | False |
| 2024-09 | 79 | 20 | 10 | 6 | 3.544304 | False |
| 2024-10 | 89 | 20 | 5 | 2 | 1.348315 | False |
| 2024-11 | 78 | 20 | 5 | 2 | 2.051282 | False |
| 2024-12 | 3 | 3 | 0 | 0 | 0.000000 | True |

출처: ANALYSIS_FACTS.validation.monthly. 마지막 달은 부분 평가다. 검증 기준 선택에 사용한 표본이므로 독립 시험 성능이 아니다.

## 위험 기준과 비용 비교

| 놓친 재고장 비용(만원) | 선택 기준 | 검증 표시 비용(만원) |
| --- | --- | --- |
| 300 | 0.3 | 8760 |
| 600 | 0.3 | 13560 |

출처: ANALYSIS_FACTS.threshold_comparison. 위험 표시 비용과 실제 월 점검 용량 적용은 구분했다. 상위 장비 선정과 초과 대기 처리의 근거는 reports/06_operations.md다.

## 시험 예측 제출물

reports/test_predictions_2025.csv는 시험 원본의 모든 행을 원래 순서로 보존한다. equipment_id, maintenance_date, prob 열만 저장하며 장비별로 중복 제거하지 않는다. 날짜는 YYYY-MM-DD다. 해시 출처는 ANALYSIS_FACTS.provenance.test_predictions_sha256이다.

정답 미제공: 시험 성능 미평가. 시험 자료는 모델 학습에 사용하지 않음.

## 재현과 검증

환경은 python -m pip install -r requirements-app.txt, 검증은 python scripts/check.py로 실행한다. 기존 결과의 보존·버전 방식을 정한 뒤 학습을 재실행한다. 결과 생성기는 기존 파일을 덮어쓰지 않는다.

## 계산 원출력

<!-- ANALYSIS_FACTS -->

```json

{
  "split_counts": {
    "train": 1611,
    "valid_records": 643,
    "valid_latest": 497,
    "evaluation_candidates": 413,
    "final_train": 2223
  },
  "trained_on": "2023-01-01 ~ 2024-12-01 (2,223건)",
  "label_policy": {
    "horizon_days": 30,
    "validation_origin": "2024-07-01",
    "final_origin": "2025-01-01",
    "condition": "maintenance_date + 30 days < origin",
    "evaluation_cutoff": "2025-01-01",
    "note": "최종 모델에도 같은 정답 확정 조건 적용"
  },
  "validation": {
    "pr_auc": 0.5012756930579202,
    "random_pr_auc": 0.10653753026634383,
    "oldest_pr_auc": 0.15286326459525587,
    "monthly": [
      {
        "month": "2024-07",
        "picked": 20,
        "model": 6,
        "oldest": 4,
        "random": 2.3376623376623376,
        "eligible_candidates": 77,
        "latest_candidates": 77,
        "partial_evaluation": false
      },
      {
        "month": "2024-08",
        "picked": 20,
        "model": 4,
        "oldest": 2,
        "random": 1.6091954022988506,
        "eligible_candidates": 87,
        "latest_candidates": 87,
        "partial_evaluation": false
      },
      {
        "month": "2024-09",
        "picked": 20,
        "model": 10,
        "oldest": 6,
        "random": 3.5443037974683547,
        "eligible_candidates": 79,
        "latest_candidates": 79,
        "partial_evaluation": false
      },
      {
        "month": "2024-10",
        "picked": 20,
        "model": 5,
        "oldest": 2,
        "random": 1.348314606741573,
        "eligible_candidates": 89,
        "latest_candidates": 89,
        "partial_evaluation": false
      },
      {
        "month": "2024-11",
        "picked": 20,
        "model": 5,
        "oldest": 2,
        "random": 2.051282051282051,
        "eligible_candidates": 78,
        "latest_candidates": 78,
        "partial_evaluation": false
      },
      {
        "month": "2024-12",
        "picked": 3,
        "model": 0,
        "oldest": 0,
        "random": 0.0,
        "eligible_candidates": 3,
        "latest_candidates": 87,
        "partial_evaluation": true
      }
    ],
    "totals": {
      "model": 30.0,
      "oldest": 16.0,
      "random": 10.890758195453166
    },
    "scope": "월별 장비 최신 기록 중 정답 관측창이 끝난 후보. 검증 기준 선택에 사용한 표본으로 독립 시험 성능이 아님."
  },
  "threshold_comparison": [
    {
      "missed_cost_manwon": 300,
      "threshold": 0.3,
      "validation_cost_manwon": 8760
    },
    {
      "missed_cost_manwon": 600,
      "threshold": 0.3,
      "validation_cost_manwon": 13560
    }
  ],
  "cleaning": {
    "downtime_999": 4,
    "cost_over_10000": 5,
    "fault_missing": 1707,
    "first_maintenance": 150,
    "raw_rows": 2346,
    "clean_rows": 2346
  },
  "features": [
    "equipment_type",
    "maintenance_type",
    "fault_category",
    "equipment_age_years",
    "severity",
    "downtime_hours",
    "repair_duration_hours",
    "parts_replaced_count",
    "maintenance_cost",
    "maintenance_success",
    "cumulative_operating_hours",
    "days_since_last_maintenance",
    "is_first_maintenance",
    "fail_count_90d",
    "days_since_last_failure",
    "hours_since_last_pm"
  ],
  "test_status": "정답 미제공: 시험 성능 미평가. 시험 자료는 모델 학습에 사용하지 않음.",
  "provenance": {
    "command": "python .agents/skills/pdm-risk/scripts/score.py --write-analysis",
    "training_sha256": "f4670c258f39090dbde61eff7c4ffff8276338f0183d8f7a5e42efa18e2917fa",
    "test_predictions_sha256": "6c97152aa8e1c17ea7700385baaede94901d8339fb5f826aec5287ac5c786fa0",
    "score_script_sha256": "7dc084c67536ec76e4f3a0532971d9a61afbc656e6fbc8534ad992ac5f092153",
    "source": "training_run.joblib.model_card, operations.build_evidence, drone_train.csv"
  },
  "limits": [
    "교육용 가상 데이터로 학습했다. 실제 장비에 그대로 쓰지 않는다.",
    "확률은 '정비 뒤 30일' 기준이다. 정비 기록이 없는 장비는 판단하지 않는다.",
    "최종 판단은 정비 담당자가 한다. 모델은 점검 순서를 정하는 참고 자료다.",
    "정답 확정일이 없어 정비일에 관측 기간을 더한 보수적 기준을 적용했다. 제공 정답의 생성·관측 완결성은 확인하지 못했다.",
    "검증 말미의 미확정 후보를 제외했으므로 월별 비교의 마지막 달은 부분 평가 또는 미평가일 수 있다.",
    "비용 기준은 위험 표시용이며 월 작업 용량을 적용한 운영 정책은 별도 검토가 필요하다."
  ]
}

```

## 모델 한계 — 학습 번들 model_card.limits 원문

- 교육용 가상 데이터로 학습했다. 실제 장비에 그대로 쓰지 않는다.

- 확률은 '정비 뒤 30일' 기준이다. 정비 기록이 없는 장비는 판단하지 않는다.

- 최종 판단은 정비 담당자가 한다. 모델은 점검 순서를 정하는 참고 자료다.

- 정답 확정일이 없어 정비일에 관측 기간을 더한 보수적 기준을 적용했다. 제공 정답의 생성·관측 완결성은 확인하지 못했다.

- 검증 말미의 미확정 후보를 제외했으므로 월별 비교의 마지막 달은 부분 평가 또는 미평가일 수 있다.

- 비용 기준은 위험 표시용이며 월 작업 용량을 적용한 운영 정책은 별도 검토가 필요하다.

최종 판단은 정비 담당자가 한다.
