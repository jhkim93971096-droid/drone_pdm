# 4단계 사전 학습 모델 감사

## 감사 결론
사전 학습 모델은 참고 결과로 유지한다. 즉시 운영에 사용할 모델로 승인하지 않는다. 금지 피처 제외와 기간별 학습·검증 구성은 확인했지만, 저장소 안에서의 독립 재현, 장비별 월 선정, 정답 확정 시점, 검증 증적 보존을 보완한 후 다음 단계에서 재학습한다. 의도적으로 잘못된 모델을 추가로 만들거나 기존 모델을 덮어쓰지 않았다.

## 감사 대상과 출처
- 학습 코드: `C:/workspaces/pdm_ai_lab/reports/train_drone.py`
- 학습 당시 참조하는 공통 코드: `C:/workspaces/pdm_ai_lab/pdm_lib.py`
- 모델과 내장 모델 정보: 이 저장소의 `artifacts/drone_model.joblib`에서 `model`과 `model_card`를 읽음.
- 현재 데이터 준비 코드: 이 저장소의 `pdm_lib.py`.
- 입력 데이터: `data/data/drone_train.csv`, `drone_test.csv`, `drone_this_month.csv`.
- 실행 근거: `scripts/check.py`의 `collect_audit()`를 이 저장소 가상환경에서 호출. 아래 JSON은 해당 호출의 원출력이며 코드·모델·입력 파일의 SHA-256을 포함한다.
- 재점검 장비의 순위·확률·대수는 산출하지 않았다. 저장된 검증 성능 수치를 재계산한 감사도 아니다.

## 확인된 사항
| 항목 | 판단 | 근거 |
| --- | --- | --- |
| 모델 입력 | 현재 공통 코드의 FEATURES 및 내장 정보와 일치하며, 정답·가동률·식별자·정비일·고장 코드 제외 | collect_audit의 feature_match, banned_features, model_features |
| 기간 분할 | 학습과 검증을 정비일로 분리하는 코드 확인 | 학습 코드의 train_period, validation_period 근거 |
| 위험 기준 | 검증 예측과 정답으로 비용을 비교하는 코드 확인 | validation_threshold 코드 근거 |
| 시험 성능 구분 | 내장 정보에서 검증 성능을 별도로 기록하고 시험 정답 미제공을 명시 | validation_metrics_separate, test_status, validation_note |
| 최종 학습 | 정답 있는 학습 파일 전체로 최종 학습하는 코드 확인 | final_fit_all_labeled 코드 근거 |
| 시간 피처 | 현재 데이터 준비의 미래 기록 불변성·정답 비참조 등은 중간점검에서 검증 | python scripts/check.py의 데이터 준비 검사. 저장된 과거 모델의 실행 이력을 보증하지는 않음 |

## 개선할 사항
### 저장소 안에서 독립 재현할 수 없음
사전 학습 스크립트가 다른 저장소에 있고 절대 경로를 사용한다. 현재 저장소 공통 코드에는 데이터 준비 함수만 있으며 모델·모델 정보 생성 함수가 아직 없다. 새 컴퓨터에서 이 저장소만 복제해 사전 학습을 재현할 수 없다. 다음 학습 단계에서 로컬 학습 진입점과 모델 생성·정보 생성 함수를 마련하고 패키지 버전·입력 해시·학습 구성을 남겨야 한다.

### 월별 선정의 평가 단위가 업무와 다름
기존 monthly_topk는 월별 상위 정비 기록을 뽑는다. 같은 드론이 월중 여러 번 정비되면 중복 선정될 수 있다. 반면 실제 재점검 계획은 드론별 최신 기록을 기준으로 한다. 월별 적중 평가는 먼저 장비별 최신 기록을 선택한 뒤 모델·오래된 순·무작위 기준선에 동일한 후보 집합을 적용해야 한다. 원본에서 같은 장비·월 반복 기록이 있는지는 아래 equipment_month_repeated_records에 보존했다. 이 값은 후보 중복 점검 결과이며 선정 장비 수나 위험 대수가 아니다.

### 정답 확정 시점에 대한 기간 경계 점검이 없음
정답은 정비 이후 관측으로 결정되므로 학습 종료 직전 기록의 정답은 검증 시작 시점에 확정되지 않을 수 있다. 코드는 정비일로만 학습 행을 나누며 정답 확정 시점을 검증하지 않는다. 아래 boundary_window_overlap_records는 학습 기간 정비 중 정답 관측창이 검증 시작에 걸치는 기록 수다. 이것만으로 실제 누수가 발생했다고 단정할 수 없다. 정답 확정일 정보를 확인하거나 보수적인 학습 경계 제외 방안을 정해, 고정 기간 분할 안에서 사용 가능한 학습 정답만 사용해야 한다. 학습 파일 말미 정답의 관측 완결성도 제공자 확인 또는 명시적인 한계 기록이 필요하다.

### 검증 모델과 행별 예측이 저장되지 않음
사전 학습 스크립트는 검증용 모델을 메모리에서 사용한 뒤 전체 학습 모델을 저장한다. 제출된 모델만으로 당시 검증 예측·임계값 비용·월별 적중을 독립적으로 재현할 수 없다. 최종 모델을 같은 학습 데이터에 다시 예측한 성능으로 검증 성능을 대체해서는 안 된다. 재학습 단계에서 검증용 예측과 기간·모델 구성을 증적으로 보존해야 한다.

### 비용 기준과 월별 작업 용량의 연결이 아직 없음
기존 비용식의 위험 표시 건수에는 월별 작업 용량 제한이 직접 들어가지 않는다. 위험 기준 이상인 모든 기록이 실제 재점검되는 것으로 해석하면 업무 용량과 충돌할 수 있다. 운영 기준 단계에서 위험 표시와 실제 장비 선정 정책, 초과 대상 처리 방법을 구분해 결정해야 한다. 검증 기간에서 고른 기준을 전체 학습 모델에 적용할 때도 확률 분포 변화 가능성을 기록한다.

## 후속 조치
- 다음 학습 단계: 저장소 전용 학습 스킬과 실행 코드, 모델·모델 정보 생성 함수를 마련한다.
- 검증 설계: 날짜 분할을 유지하고 정답 확정 시점을 고려하는 방법을 명시한다.
- 평가: 장비별 월 최신 기록으로 후보를 통일한 뒤 PR-AUC 및 월별 적중을 동일한 기준선과 비교한다.
- 증적: 검증용 행별 예측, 입력 해시, 패키지 버전과 학습 구성의 출처를 남긴다.
- 운영 기준: 비용과 용량의 관계, 위험 표시 초과 시 대응을 확정한다.
- 시험 데이터: 정답이 없으므로 예측 제출만 수행하고 시험 성능은 미평가로 남긴다.

## 감사 범위와 한계
이 감사는 현재 남아 있는 코드·모델 정보·입력 구조를 검사한 것이다. 과거 학습 시점의 파일 버전이 보존되지 않았으므로 현재 코드가 실제 당시 실행본과 동일하다고 확정할 수 없다. 해시는 감사 시점의 상태를 고정한 것이며 과거 실행 이력의 증명이 아니다. 이 단계에서 모델을 재학습하거나 검증 성능을 재계산하지 않았다.

중간점검의 감사 통과는 보고서의 근거가 현재 파일과 일치한다는 뜻이다. 개선 사항 해결이나 모델 운영 승인을 의미하지 않는다. 코드·데이터·모델 변경 뒤에는 감사 근거가 달라지므로 재감사 또는 후속 모델에 대한 별도 검증이 필요하다.

## 감사 원출력
<!-- AUDIT_FACTS -->
```json
{
  "sha256": {
    "C:\\workspaces\\pdm_ai_lab\\reports\\train_drone.py": "fb50901b8c72e4f98abb088d29eb7aa3dd1a1ec45b2876cee804a8f691d8afc6",
    "C:\\workspaces\\pdm_ai_lab\\pdm_lib.py": "53e3081972ab2104f07c5fddee0005232cbe224a75e98a41a677ffde5cce1d6a",
    "C:\\workspaces\\drone_pdm_new\\pdm_lib.py": "c5eff6f1d9004537516200791feaaae8229a3dedc24663b61048670fcd44c1d7",
    "C:\\workspaces\\drone_pdm_new\\artifacts\\drone_model.joblib": "5e0869bc7ed10c5af6a42c4623c24f89d21209a6b39e15b20f54e0430c600be7",
    "C:\\workspaces\\drone_pdm_new\\data\\data\\drone_train.csv": "26c4d3711fd5c91dc183815af83ba5af6107b6470ae2d3660da2a50586136121",
    "C:\\workspaces\\drone_pdm_new\\data\\data\\drone_test.csv": "5fa789dd8111ce5c3303e9a5c9f0694aec409a1c3a504574cc2ab2386ece7a7e",
    "C:\\workspaces\\drone_pdm_new\\data\\data\\drone_this_month.csv": "379631f03af5139d8a0c5c7278d812b7892da022a4d7650488eafe5ff564e346"
  },
  "model_features": [
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
  "feature_match": true,
  "banned_features": [],
  "validation_metrics_separate": true,
  "test_status": "정답 미제공: 시험 성능 미평가. 시험 자료로 학습하지 않음.",
  "validation_note": "임계값 선택과 동일한 검증 기간 성능이며 독립 시험 성능이 아님. 월별 적중은 정비 기록 단위. 무작위는 기대값.",
  "external_trainer": "C:\\workspaces\\pdm_ai_lab\\reports\\train_drone.py",
  "local_training_script_exists": false,
  "local_model_factory_exists": false,
  "local_model_card_factory_exists": false,
  "boundary_window_overlap_records": 92,
  "equipment_month_repeated_records": 424,
  "code_evidence": {
    "train_period": true,
    "validation_period": true,
    "uses_features_only": true,
    "validation_threshold": true,
    "row_based_topk": true,
    "final_fit_all_labeled": true,
    "external_import": true
  },
  "limits": [
    "교육용 가상 데이터로 학습했다. 실제 장비에 그대로 쓰지 않는다.",
    "확률은 '정비 뒤 30일' 기준이다. 정비 기록이 없는 장비는 판단하지 않는다.",
    "최종 판단은 정비 담당자가 한다. 모델은 점검 순서를 정하는 참고 자료다."
  ]
}
```

## 학습 코드 위치
- `train =`: `C:\workspaces\pdm_ai_lab\reports\train_drone.py`의 19행.
- `valid =`: `C:\workspaces\pdm_ai_lab\reports\train_drone.py`의 20행.
- `model.fit(`: `C:\workspaces\pdm_ai_lab\reports\train_drone.py`의 28행.
- `monthly_topk`: `C:\workspaces\pdm_ai_lab\reports\train_drone.py`의 41, 42행.
- `make_card`: `C:\workspaces\pdm_ai_lab\reports\train_drone.py`의 47행.
- `joblib.dump`: `C:\workspaces\pdm_ai_lab\reports\train_drone.py`의 66행.

## 모델 한계 — 내장 model_card.limits 원문
- 교육용 가상 데이터로 학습했다. 실제 장비에 그대로 쓰지 않는다.
- 확률은 '정비 뒤 30일' 기준이다. 정비 기록이 없는 장비는 판단하지 않는다.
- 최종 판단은 정비 담당자가 한다. 모델은 점검 순서를 정하는 참고 자료다.
