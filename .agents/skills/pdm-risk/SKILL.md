---
name: pdm-risk
description: 드론 정비 모델로 재점검 우선순위·장비별 근거·재점검 계획을 산출하고 시험 예측과 분석 보고서를 만든다. 드론 위험 분석과 제출물 검수 요청에 사용한다.
---

# 드론 위험 분석과 제출물

프로젝트 루트에서 실행한다. 모델은 artifacts/training_run.joblib, 운영 기준은 reports/06_operations.md다. 원본과 모델은 변경하지 않는다.

- 목록: `python .agents/skills/pdm-risk/scripts/score.py`. `--top`은 조회 행 수만 바꾸며 정책의 선정 용량은 바꾸지 않는다.
- 장비 근거: 같은 명령에 `--explain`과 실제 출력의 드론 번호를 붙인다.
- 시험 예측: `--write-test`로 reports/test_predictions_2025.csv 하나를 만든다. 원본 모든 행과 순서를 보존하고 날짜는 YYYY-MM-DD, 확률은 0~1로 저장한다.
- 재점검 계획: `--write-plan`으로 reports/2026-01_재점검계획.md 하나를 만든다. 수치 근거·선정·초과 대기를 함께 기록한다.
- 분석 보고서: 시험 예측 생성 뒤 `--write-analysis`로 reports/08_analysis.md 하나를 만든다.
- 한 번에 결과 하나만 생성한다. 기존 파일이 있으면 중단하므로 임의 삭제·덮어쓰기 대신 보존·버전 방식을 정한다.
- 순위·확률·대수·기여 요인은 스크립트 출력만 인용한다. 앱과 같은 scripts/app_data.py·scripts/operations.py를 사용한다.
- 시험 성능을 만들지 않는다. 검증 마지막 달의 부분 평가와 독립 시험 미평가를 명시한다.
- 보고서 끝에 학습 번들 model_card.limits를 그대로 적고 최종 판단은 정비 담당자가 한다고 명시한다. 권고는 점검 항목이며 고장 원인·정비 효과를 단정하지 않는다.
- 생성 뒤 `python scripts/check.py`로 시험 전체 행·모델 재예측·계획 수치·설명·앱과의 일치를 검증하고 실제 결과를 보여 준다.
