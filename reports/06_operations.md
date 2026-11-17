# 6단계 운영 기준

## 기준과 출처

모든 계산 수치의 출처는 `python scripts/operations.py --write` 실행과 아래 근거 JSON이다. 입력은 학습 번들의 검증 예측·비용 비교·모델 정보다. 이번 달 장비의 위험도·순위는 산출하지 않았다.

## 위험 표시 기준

| 누락 비용(만원) | 기준 | 검증 표시 비용(만원) |

| --- | --- | --- |

| 300 | 0.30 | 8760 |

| 600 | 0.30 | 13560 |

위 비교는 용량을 제한하지 않은 위험 표시 비용이다. 검증 후보에서 비용을 최소화하고, 비용 동점이면 낮은 기준을 선택했다. 이번 검증에서는 누락 비용을 높여도 선택된 기준이 같았다. 이를 다른 데이터에도 성립하는 결론으로 일반화하지 않는다.

## 실제 선정 정책

- 위험 표시는 확률이 0.30 이상일 때 적용한다. 기준과 같은 값도 포함한다.

- 월별 장비 최신 기록을 후보로 삼고 확률 상위 20대를 선정한다. 후보가 더 적으면 후보 전부만 선정한다.

- 위험 기준 이상이 용량보다 많으면 확률이 높은 장비부터 선정하고 나머지를 초과 대기로 표시한다. 같은 확률이면 장비 번호 오름차순으로 정한다.

- 기준 이상이 용량보다 적으면 나머지는 확률 순으로 예방 점검 대상으로 채우되, 기준 이상 장비와 별도 표시한다. 이는 비용 최소화 정책이 아니라 과제의 정해진 점검 용량을 사용하는 정책이다.

- 초과 대기는 안전 판정이 아니다. 담당자가 현장 상태에 따라 추가 용량 또는 조기 재점검을 판단한다. 다음 달로 자동 이월하거나 미래 기록이 없는 상태에서 일정을 확정하지 않는다.

- 같은 날짜의 복수 기록은 입력 순서의 마지막 기록을 사용한다. 월별 계획은 해당 월 기록이 준비된 시점의 최신 기록을 기준으로 한다.

## 검증 정책 비교

아래 JSON의 validation_monthly와 totals에서 모델·오래된 순·무작위 기대값에 동일한 최신 장비 후보와 용량을 적용했다. 비용은 미선정 재고장 기록의 누락 비용과 선정 장비의 점검 비용을 합산한 교육용 가정이며 실제 예방 효과를 입증한 값이 아니다. threshold_only 비용은 위험 표시만 수행했을 때의 별도 비교다.

| 월 | 평가 후보 | 선정 | 모델 적중 | 오래된 순 적중 | 무작위 기대 적중 | 부분 평가 |

| --- | --- | --- | --- | --- | --- | --- |

| 2024-07 | 77 | 20 | 6 | 4 | 2.338 | False |

| 2024-08 | 87 | 20 | 4 | 2 | 1.609 | False |

| 2024-09 | 79 | 20 | 10 | 6 | 3.544 | False |

| 2024-10 | 89 | 20 | 5 | 2 | 1.348 | False |

| 2024-11 | 78 | 20 | 5 | 2 | 2.051 | False |

| 2024-12 | 3 | 3 | 0 | 0 | 0.000 | True |

수치는 검증 자료에 한정된다. 마지막 달은 정답 확정 조건 때문에 부분 평가이며, 전체 월 또는 시험 성능으로 해석하지 않는다. 무작위는 실제 추첨 결과가 아닌 기대값이다.

## 적용 범위와 검증

기준은 검증 모델로 선택했으며 최종 모델에서는 확률 분포가 달라질 수 있다. 최종 모델의 기준 적합성 또는 실제 운영 효과를 시험으로 확인하지 못했다. 시험 데이터 정답이 없으므로 시험 성능을 보고하지 않는다. 기준은 유지하고 후속 정답이 확보되면 재검증한다.

운영 함수는 여러 달·장비 중복·동률·기준 경계·초과 대기·빈 후보·비정상 확률을 검사한다. 학습 번들과 원본을 수정하지 않는다.

## 운영 근거 원출력

<!-- OPERATIONS_FACTS -->

```json

{
  "policy": {
    "threshold": 0.3,
    "capacity_per_month": 20,
    "selection": "fixed_capacity_top_probability",
    "latest_record": "per_equipment_per_month",
    "tie_break": "equipment_id_ascending",
    "same_day_tie": "last_input_record",
    "comparison": ">=",
    "fill_below_threshold": true,
    "overflow_action": "담당자가 추가 용량·재점검 시기를 판단"
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
  "validation_monthly": [
    {
      "month": "2024-07",
      "eligible": 77,
      "partial_evaluation": false,
      "selected": 20,
      "model_hits": 6,
      "oldest_hits": 4,
      "random_hits_expected": 2.3376623376623376,
      "flagged": 13,
      "overflow": 0,
      "supplementary": 7,
      "model_cost_300": 2100,
      "oldest_cost_300": 2700,
      "random_cost_300_expected": 3198.7012987012986,
      "threshold_only_cost_300": 1680,
      "model_cost_600": 3000,
      "oldest_cost_600": 4200,
      "random_cost_600_expected": 5197.402597402597,
      "threshold_only_cost_600": 2580
    },
    {
      "month": "2024-08",
      "eligible": 87,
      "partial_evaluation": false,
      "selected": 20,
      "model_hits": 4,
      "oldest_hits": 2,
      "random_hits_expected": 1.6091954022988506,
      "flagged": 12,
      "overflow": 0,
      "supplementary": 8,
      "model_cost_300": 2100,
      "oldest_cost_300": 2700,
      "random_cost_300_expected": 2817.2413793103447,
      "threshold_only_cost_300": 1620,
      "model_cost_600": 3000,
      "oldest_cost_600": 4200,
      "random_cost_600_expected": 4434.482758620689,
      "threshold_only_cost_600": 2520
    },
    {
      "month": "2024-09",
      "eligible": 79,
      "partial_evaluation": false,
      "selected": 20,
      "model_hits": 10,
      "oldest_hits": 6,
      "random_hits_expected": 3.5443037974683547,
      "flagged": 12,
      "overflow": 0,
      "supplementary": 8,
      "model_cost_300": 2400,
      "oldest_cost_300": 3600,
      "random_cost_300_expected": 4336.708860759493,
      "threshold_only_cost_300": 2220,
      "model_cost_600": 3600,
      "oldest_cost_600": 6000,
      "random_cost_600_expected": 7473.417721518987,
      "threshold_only_cost_600": 3720
    },
    {
      "month": "2024-10",
      "eligible": 89,
      "partial_evaluation": false,
      "selected": 20,
      "model_hits": 5,
      "oldest_hits": 2,
      "random_hits_expected": 1.348314606741573,
      "flagged": 16,
      "overflow": 0,
      "supplementary": 4,
      "model_cost_300": 1500,
      "oldest_cost_300": 2400,
      "random_cost_300_expected": 2595.5056179775283,
      "threshold_only_cost_300": 1260,
      "model_cost_600": 1800,
      "oldest_cost_600": 3600,
      "random_cost_600_expected": 3991.0112359550562,
      "threshold_only_cost_600": 1560
    },
    {
      "month": "2024-11",
      "eligible": 78,
      "partial_evaluation": false,
      "selected": 20,
      "model_hits": 5,
      "oldest_hits": 2,
      "random_hits_expected": 2.051282051282051,
      "flagged": 13,
      "overflow": 0,
      "supplementary": 7,
      "model_cost_300": 2100,
      "oldest_cost_300": 3000,
      "random_cost_300_expected": 2984.6153846153848,
      "threshold_only_cost_300": 1980,
      "model_cost_600": 3000,
      "oldest_cost_600": 4800,
      "random_cost_600_expected": 4769.2307692307695,
      "threshold_only_cost_600": 3180
    },
    {
      "month": "2024-12",
      "eligible": 3,
      "partial_evaluation": true,
      "selected": 3,
      "model_hits": 0,
      "oldest_hits": 0,
      "random_hits_expected": 0.0,
      "flagged": 0,
      "overflow": 0,
      "supplementary": 3,
      "model_cost_300": 180,
      "oldest_cost_300": 180,
      "random_cost_300_expected": 180.0,
      "threshold_only_cost_300": 0,
      "model_cost_600": 180,
      "oldest_cost_600": 180,
      "random_cost_600_expected": 180.0,
      "threshold_only_cost_600": 0
    }
  ],
  "totals": {
    "eligible": 413.0,
    "selected": 103.0,
    "model_hits": 30.0,
    "oldest_hits": 16.0,
    "random_hits_expected": 10.890758195453166,
    "flagged": 66.0,
    "overflow": 0.0,
    "supplementary": 37.0,
    "model_cost_300": 10380.0,
    "oldest_cost_300": 14580.0,
    "random_cost_300_expected": 16112.77254136405,
    "threshold_only_cost_300": 8760.0,
    "model_cost_600": 14580.0,
    "oldest_cost_600": 22980.0,
    "random_cost_600_expected": 26045.5450827281,
    "threshold_only_cost_600": 13560.0
  },
  "provenance": {
    "command": "python scripts/operations.py --write",
    "training_sha256": "f4670c258f39090dbde61eff7c4ffff8276338f0183d8f7a5e42efa18e2917fa",
    "operations_sha256": "87c3b95f62112407c3f53909fb1ad795170904f0a4d8e98156fa463670cddccd",
    "input": "artifacts/training_run.joblib: validation_predictions, threshold_grid, model_card"
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

운영 정책 적용 후에도 최종 판단은 정비 담당자가 한다.
