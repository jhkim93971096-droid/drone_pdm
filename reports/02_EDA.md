# 2단계 데이터 탐색(EDA)

## 범위와출처

모든 표의 수치는 부록 코드를 PowerShell에서 실행한 결과다. 별도 표기가 없으면 입력은 `data/data/drone_train.csv`다. 정비 기록 단위의 기술 통계이며 개별 장비 위험 확률·인과관계·모델 성능을 의미하지 않는다. 시험·이번 달 데이터는 구조 확인만 수행했다.

## 입력 파일 확인

출처: 각 CSV의 shape·nunique·날짜 범위·정답 열 존재 여부.

| 파일 | 행 수 | 열 수 | 장비 수 | 시작일 | 종료일 | 정답 |
| --- | --- | --- | --- | --- | --- | --- |
| drone_test.csv | 1241 | 17 | 150 | 2025-01-01 | 2025-12-31 | 없음 |
| drone_this_month.csv | 106 | 16 | 81 | 2026-01-01 | 2026-01-31 | 없음 |
| drone_train.csv | 2346 | 18 | 150 | 2023-01-01 | 2024-12-31 | 있음 |

## 컬럼별 자료형과 결측

출처: 학습 CSV의 dtypes·isna·nunique. 날짜는 읽은 뒤 변환.

| 컬럼 | 자료형 | 결측 수 | 결측률(%) | 고유값 수 |
| --- | --- | --- | --- | --- |
| equipment_id | str | 0 | 0 | 150 |
| equipment_type | str | 0 | 0 | 4 |
| unit_code | str | 0 | 0 | 12 |
| equipment_age_years | float64 | 0 | 0 | 74 |
| maintenance_date | datetime64[us] | 0 | 0 | 697 |
| maintenance_type | str | 0 | 0 | 3 |
| fault_code | str | 1707 | 72.762 | 40 |
| fault_category | str | 1707 | 72.762 | 5 |
| severity | int64 | 0 | 0 | 6 |
| downtime_hours | float64 | 0 | 0 | 312 |
| repair_duration_hours | float64 | 0 | 0 | 218 |
| parts_replaced_count | int64 | 0 | 0 | 11 |
| maintenance_cost | int64 | 0 | 0 | 308 |
| maintenance_success | int64 | 0 | 0 | 2 |
| cumulative_operating_hours | float64 | 0 | 0 | 2234 |
| days_since_last_maintenance | float64 | 150 | 6.394 | 94 |
| availability_rate | float64 | 0 | 0 | 334 |
| failure_within_30days | int64 | 0 | 0 | 2 |

## 수치형 원본 분포

출처: 학습 CSV의 describe. 이상치 후보 포함; count는 유효값 수, std는 표본 표준편차.

| index | count | mean | std | min | 25% | 50% | 75% | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| equipment_age_years | 2,346 | 4.354 | 1.626 | 0.6 | 3.1 | 4.4 | 5.6 | 7.9 |
| severity | 2,346 | 0.786 | 1.446 | 0 | 0 | 0 | 1 | 5 |
| downtime_hours | 2,346 | 8.097 | 41.794 | 0.5 | 2.025 | 3.5 | 5 | 999 |
| repair_duration_hours | 2,346 | 3.637 | 4.89 | 0.2 | 1.2 | 2 | 3.3 | 55.9 |
| parts_replaced_count | 2,346 | 0.864 | 1.431 | 0 | 0 | 0 | 1 | 10 |
| maintenance_cost | 2,346 | 93.198 | 791.122 | 8 | 16 | 23 | 49 | 19,000 |
| maintenance_success | 2,346 | 0.944 | 0.23 | 0 | 1 | 1 | 1 | 1 |
| cumulative_operating_hours | 2,346 | 1,400.032 | 616.249 | 140.3 | 932.475 | 1,363.4 | 1,810.975 | 3,542.6 |
| days_since_last_maintenance | 2,196 | 44.8 | 25.13 | 1 | 21 | 51 | 64 | 94 |
| availability_rate | 2,346 | 0.92 | 0.122 | 0.3 | 0.922 | 0.965 | 0.977 | 0.998 |
| failure_within_30days | 2,346 | 0.224 | 0.417 | 0 | 0 | 0 | 0 | 1 |

## equipment_type 분포

출처: 학습 CSV의 value_counts, 결측 포함.

| equipment_type | 기록 수 | 비중(%) |
| --- | --- | --- |
| 정찰드론 | 783 | 33.376 |
| 수송드론 | 601 | 25.618 |
| 감시드론 | 581 | 24.766 |
| 교육용드론 | 381 | 16.24 |

## maintenance_type 분포

출처: 학습 CSV의 value_counts, 결측 포함.

| maintenance_type | 기록 수 | 비중(%) |
| --- | --- | --- |
| 예방정비 | 1707 | 72.762 |
| 사후정비 | 468 | 19.949 |
| 긴급정비 | 171 | 7.289 |

## fault_category 분포

출처: 학습 CSV의 value_counts, 결측 포함.

| fault_category | 기록 수 | 비중(%) |
| --- | --- | --- |
| 결측(원본) | 1707 | 72.762 |
| 배터리 | 180 | 7.673 |
| 모터 | 147 | 6.266 |
| 통신 | 126 | 5.371 |
| 센서 | 107 | 4.561 |
| 기체 | 79 | 3.367 |

## 결측 의미와 이상치 후보

출처: 학습 CSV 조건별 마스크 합계·첫 기록 인덱스 비교.

| 점검 항목 | 기록 수 |
| --- | --- |
| 전체 행 중복 | 0 |
| 장비·정비일 중복 | 0 |
| downtime_hours = 999 | 4 |
| maintenance_cost > 10000 | 5 |
| 고장 코드·유형 결측 위치 불일치 | 0 |
| 고장 유형 결측 중 예방정비가 아닌 기록 | 0 |
| 예방정비 중 고장 유형이 있는 기록 | 0 |
| 장비별 첫 기록과 경과일 결측 위치 불일치 | 0 |
| 심각도 범위 이탈 | 0 |
| 정비 성공 허용값 이탈 | 0 |
| 가동률 범위 이탈 | 0 |

## 정비 구분과 고장 유형 결측의 관계

출처: 학습 CSV의 crosstab.

| maintenance_type | 유형 있음 | 유형 결측 |
| --- | --- | --- |
| 긴급정비 | 171 | 0 |
| 사후정비 | 468 | 0 |
| 예방정비 | 0 | 1707 |

## 처리 가정 전후 비교

출처: 메모리 복사본에 가동중단 999→결측, 비용 >10000→/100만 적용. 기존 실습 규칙의 적용 후보이며 원인은 데이터만으로 확정하지 않음.

| 컬럼 | 구분 | 결측 수 | 평균 | 중앙값 | 최댓값 |
| --- | --- | --- | --- | --- | --- |
| downtime_hours | 원본 | 0 | 8.097 | 3.5 | 999 |
| downtime_hours | 처리 가정 | 4 | 6.404 | 3.5 | 74 |
| maintenance_cost | 원본 | 0 | 93.198 | 23 | 19,000 |
| maintenance_cost | 처리 가정 | 0 | 57.202 | 23 | 478 |

### 3단계 처리 후보

- 가동중단 시간의 미입력 후보는 행 삭제 없이 결측으로 처리한다.
- 과도한 비용은 자릿수 오류 규칙 적용을 검토한다.
- 고장 유형·코드 결측은 예방정비와 일치하므로 최빈값 대신 `N/A`로 구분한다.
- 직전 정비 경과일 결측은 장비별 첫 관측 기록과 일치한다. 결측은 유지하고 첫 정비 표시를 만든다. 관측 시작 이전 이력이 없음을 입증한 것은 아니다.
- 나머지 큰 수치는 고장 특성을 반영할 수 있으므로 크기만으로 삭제하지 않는다.

## 정답 분포

출처: 학습 CSV의 정답 value_counts.

| 정답 | 기록 수 | 비중(%) |
| --- | --- | --- |
| 0 | 1821 | 77.621 |
| 1 | 525 | 22.379 |

## 드론 유형별

출처: 학습 CSV의 equipment_type별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.

| equipment_type | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- |
| 감시드론 | 581 | 118 | 20.31 |
| 교육용드론 | 381 | 52 | 13.648 |
| 수송드론 | 601 | 191 | 31.78 |
| 정찰드론 | 783 | 164 | 20.945 |

## 정비 구분별

출처: 학습 CSV의 maintenance_type별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.

| maintenance_type | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- |
| 긴급정비 | 171 | 110 | 64.327 |
| 사후정비 | 468 | 221 | 47.222 |
| 예방정비 | 1707 | 194 | 11.365 |

## 고장 유형별

출처: 학습 CSV의 fault_category별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.

| fault_category | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- |
| 결측(예방정비) | 1707 | 194 | 11.365 |
| 기체 | 79 | 42 | 53.165 |
| 모터 | 147 | 89 | 60.544 |
| 배터리 | 180 | 97 | 53.889 |
| 센서 | 107 | 45 | 42.056 |
| 통신 | 126 | 58 | 46.032 |

## 계절별

출처: 학습 CSV의 season별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.

| season | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- |
| 가을 | 596 | 141 | 23.658 |
| 겨울 | 593 | 153 | 25.801 |
| 봄 | 557 | 87 | 15.619 |
| 여름 | 600 | 144 | 24 |

## 월별

출처: 학습 CSV의 year_month별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.

| year_month | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- |
| 2023-01 | 51 | 7 | 13.725 |
| 2023-02 | 63 | 12 | 19.048 |
| 2023-03 | 109 | 15 | 13.761 |
| 2023-04 | 70 | 10 | 14.286 |
| 2023-05 | 93 | 9 | 9.677 |
| 2023-06 | 86 | 19 | 22.093 |
| 2023-07 | 111 | 30 | 27.027 |
| 2023-08 | 112 | 31 | 27.679 |
| 2023-09 | 100 | 18 | 18 |
| 2023-10 | 93 | 17 | 18.28 |
| 2023-11 | 87 | 20 | 22.989 |
| 2023-12 | 125 | 27 | 21.6 |
| 2024-01 | 115 | 42 | 36.522 |
| 2024-02 | 111 | 19 | 17.117 |
| 2024-03 | 91 | 12 | 13.187 |
| 2024-04 | 86 | 19 | 22.093 |
| 2024-05 | 108 | 22 | 20.37 |
| 2024-06 | 92 | 20 | 21.739 |
| 2024-07 | 96 | 25 | 26.042 |
| 2024-08 | 103 | 19 | 18.447 |
| 2024-09 | 98 | 30 | 30.612 |
| 2024-10 | 117 | 28 | 23.932 |
| 2024-11 | 101 | 28 | 27.723 |
| 2024-12 | 128 | 46 | 35.938 |

## 유형·계절별

출처: 학습 CSV의 equipment_type, season별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.

| equipment_type | season | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- | --- |
| 감시드론 | 가을 | 144 | 27 | 18.75 |
| 감시드론 | 겨울 | 134 | 23 | 17.164 |
| 감시드론 | 봄 | 149 | 32 | 21.477 |
| 감시드론 | 여름 | 154 | 36 | 23.377 |
| 교육용드론 | 가을 | 93 | 10 | 10.753 |
| 교육용드론 | 겨울 | 96 | 10 | 10.417 |
| 교육용드론 | 봄 | 92 | 13 | 14.13 |
| 교육용드론 | 여름 | 100 | 19 | 19 |
| 수송드론 | 가을 | 160 | 61 | 38.125 |
| 수송드론 | 겨울 | 155 | 62 | 40 |
| 수송드론 | 봄 | 136 | 20 | 14.706 |
| 수송드론 | 여름 | 150 | 48 | 32 |
| 정찰드론 | 가을 | 199 | 43 | 21.608 |
| 정찰드론 | 겨울 | 208 | 58 | 27.885 |
| 정찰드론 | 봄 | 180 | 22 | 12.222 |
| 정찰드론 | 여름 | 196 | 41 | 20.918 |

## 계절·고장 유형별

출처: 학습 CSV의 season, fault_category별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.

| season | fault_category | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- | --- |
| 가을 | 결측(예방정비) | 428 | 43 | 10.047 |
| 가을 | 기체 | 20 | 11 | 55 |
| 가을 | 모터 | 36 | 27 | 75 |
| 가을 | 배터리 | 48 | 29 | 60.417 |
| 가을 | 센서 | 30 | 12 | 40 |
| 가을 | 통신 | 34 | 19 | 55.882 |
| 겨울 | 결측(예방정비) | 406 | 55 | 13.547 |
| 겨울 | 기체 | 22 | 15 | 68.182 |
| 겨울 | 모터 | 38 | 24 | 63.158 |
| 겨울 | 배터리 | 76 | 38 | 50 |
| 겨울 | 센서 | 27 | 10 | 37.037 |
| 겨울 | 통신 | 24 | 11 | 45.833 |
| 봄 | 결측(예방정비) | 451 | 44 | 9.756 |
| 봄 | 기체 | 16 | 5 | 31.25 |
| 봄 | 모터 | 23 | 7 | 30.435 |
| 봄 | 배터리 | 20 | 11 | 55 |
| 봄 | 센서 | 21 | 8 | 38.095 |
| 봄 | 통신 | 26 | 12 | 46.154 |
| 여름 | 결측(예방정비) | 422 | 52 | 12.322 |
| 여름 | 기체 | 21 | 11 | 52.381 |
| 여름 | 모터 | 50 | 31 | 62 |
| 여름 | 배터리 | 36 | 19 | 52.778 |
| 여름 | 센서 | 29 | 15 | 51.724 |
| 여름 | 통신 | 42 | 16 | 38.095 |

## 패턴 해석

그룹별 재고장률 차이는 추가 검토할 관찰 패턴이다. 드론 유형·계절·고장 유형의 효과를 서로 분리하거나 심각도·정비 구분을 보정한 결과가 아니다. 특히 표본이 작은 조합과 동일 장비 반복 기록은 비율의 변동성을 높일 수 있다. 고장 유형이 비어 있는 예방정비에도 재고장 기록이 있어 해당 행을 일괄 삭제하면 관측 구성이 달라진다.

## 기간 분할 준비

출처: 학습 CSV 정비일 기준 분할 후 정답 집계. 시험 정답은 미제공.

| period | 기록 수 | 재고장 기록 수 | 재고장률(%) |
| --- | --- | --- | --- |
| 검증(2024-07~12) | 643 | 176 | 27.372 |
| 학습(~2024-06-30) | 1703 | 349 | 20.493 |

## 다음 단계 주의사항

- 예측 시점은 정비 직후다. 그 달 전체 `availability_rate`는 미래 정보를 포함하므로 모델 입력에서 제외한다.
- 식별자와 날짜 및 `fault_code`는 모델 입력에서 제외한다. 날짜·장비 번호는 이력 연결과 기간 분할에 사용한다.
- 시간 피처는 정비일까지의 기록만 사용하고 시험·이번 달 피처에는 앞 기간 이력을 연결한다.
- 위험 기준은 검증 기간에서 고르며 정답 없는 시험 자료로 시험 성능을 계산하지 않는다.
- 정답이 미래 관측 기간으로 정의되므로 기간 경계의 정답 확정 시점도 후속 검증에서 점검한다.
- 이 보고서는 EDA이며 정제 함수·학습 스킬·모델 재학습은 수행하지 않았다.

## 원본 보존 확인

출처: 원본 CSV의 실행 전후 SHA-256 비교. 모두 동일.

| 파일 | SHA-256 |
| --- | --- |
| drone_test.csv | 5fa789dd8111ce5c3303e9a5c9f0694aec409a1c3a504574cc2ab2386ece7a7e |
| drone_this_month.csv | 379631f03af5139d8a0c5c7278d812b7892da022a4d7650488eafe5ff564e346 |
| drone_train.csv | 26c4d3711fd5c91dc183815af83ba5af6107b6470ae2d3660da2a50586136121 |

## 재현용 실행 코드

아래 코드를 PowerShell에서 `@'`와 `'@ | python -` 사이에 붙여 실행한다. 한글 전달을 위해 먼저 `$OutputEncoding = [System.Text.UTF8Encoding]::new()`를 실행한다. 기존 보고서 보호를 위해 재실행 전 코드의 출력 파일명을 바꾼다. 코드 부록까지 동일하게 저장하려면 현재 명령처럼 `DRONE_EDA_SOURCE` 환경변수에 코드 문자열을 전달한다.

```python
import sys, os, json, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'C:\workspaces\drone_pdm_new')
out=root/'reports/02_EDA.md'
if out.exists(): raise FileExistsError(str(out))
paths=list((root/'data/data').glob('drone_*.csv'))
def hashes(): return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=hashes()
frames={p.name:pd.read_csv(p,encoding='utf-8-sig') for p in paths}
d=frames['drone_train.csv'].copy()
d['maintenance_date']=pd.to_datetime(d.maintenance_date,errors='raise')
y='failure_within_30days'
assert d[y].notna().all() and set(d[y].unique())=={0,1}
assert all(y not in f for n,f in frames.items() if n!='drone_train.csv')
def fmt(x):
 if pd.isna(x): return '결측'
 if isinstance(x,(float,np.floating)): return f'{x:,.3f}'.rstrip('0').rstrip('.')
 return str(x).replace('|','/').replace('\n',' ')
def table(f):
 return '\n'.join(['| '+' | '.join(map(str,f.columns))+' |','| '+' | '.join(['---']*len(f.columns))+' |']+['| '+' | '.join(fmt(x) for x in row)+' |' for row in f.itertuples(index=False,name=None)])
s=['# 2단계 데이터 탐색(EDA)','## 범위와出처'.replace('出','출'),'모든 표의 수치는 부록 코드를 PowerShell에서 실행한 결과다. 별도 표기가 없으면 입력은 `data/data/drone_train.csv`다. 정비 기록 단위의 기술 통계이며 개별 장비 위험 확률·인과관계·모델 성능을 의미하지 않는다. 시험·이번 달 데이터는 구조 확인만 수행했다.']
def section(title,source,f): s.extend(['## '+title,'출처: '+source,table(f)])
rows=[]
for name,f in frames.items():
 dates=pd.to_datetime(f.maintenance_date)
 rows.append([name,len(f),len(f.columns),f.equipment_id.nunique(),dates.min().date(),dates.max().date(),'있음' if y in f else '없음'])
section('입력 파일 확인','각 CSV의 shape·nunique·날짜 범위·정답 열 존재 여부.',pd.DataFrame(rows,columns=['파일','행 수','열 수','장비 수','시작일','종료일','정답']))
section('컬럼별 자료형과 결측','학습 CSV의 dtypes·isna·nunique. 날짜는 읽은 뒤 변환.',pd.DataFrame([[c,str(d[c].dtype),int(d[c].isna().sum()),d[c].isna().mean()*100,d[c].nunique()] for c in d],columns=['컬럼','자료형','결측 수','결측률(%)','고유값 수']))
num=d.select_dtypes(include='number').describe().T.reset_index()
section('수치형 원본 분포','학습 CSV의 describe. 이상치 후보 포함; count는 유효값 수, std는 표본 표준편차.',num)
for c in ['equipment_type','maintenance_type','fault_category']:
 f=d[c].fillna('결측(원본)').value_counts().rename_axis(c).reset_index(name='기록 수')
 f['비중(%)']=f['기록 수']/len(d)*100
 section(c+' 분포','학습 CSV의 value_counts, 결측 포함.',f)
first=d.sort_values('maintenance_date').groupby('equipment_id').head(1).index
missing=d.index[d.days_since_last_maintenance.isna()]
checks=[['전체 행 중복',d.duplicated().sum()],['장비·정비일 중복',d.duplicated(['equipment_id','maintenance_date']).sum()],['downtime_hours = 999',d.downtime_hours.eq(999).sum()],['maintenance_cost > 10000',d.maintenance_cost.gt(10000).sum()],['고장 코드·유형 결측 위치 불일치',(d.fault_code.isna()!=d.fault_category.isna()).sum()],['고장 유형 결측 중 예방정비가 아닌 기록',(d.fault_category.isna()&d.maintenance_type.ne('예방정비')).sum()],['예방정비 중 고장 유형이 있는 기록',(d.maintenance_type.eq('예방정비')&d.fault_category.notna()).sum()],['장비별 첫 기록과 경과일 결측 위치 불일치',len(set(first).symmetric_difference(set(missing)))],['심각도 범위 이탈',(~d.severity.between(0,5)).sum()],['정비 성공 허용값 이탈',(~d.maintenance_success.isin([0,1])).sum()],['가동률 범위 이탈',(~d.availability_rate.between(0,1)).sum()]]
section('결측 의미와 이상치 후보','학습 CSV 조건별 마스크 합계·첫 기록 인덱스 비교.',pd.DataFrame(checks,columns=['점검 항목','기록 수']))
cross=pd.crosstab(d.maintenance_type,d.fault_category.isna()).rename(columns={False:'유형 있음',True:'유형 결측'}).reset_index()
section('정비 구분과 고장 유형 결측의 관계','학습 CSV의 crosstab.',cross)
clean=d.copy()
clean['downtime_hours']=clean.downtime_hours.replace(999,np.nan)
clean['maintenance_cost']=clean.maintenance_cost.mask(clean.maintenance_cost.gt(10000),clean.maintenance_cost/100)
comparison=[[c,label,int(f[c].isna().sum()),f[c].mean(),f[c].median(),f[c].max()] for c in ['downtime_hours','maintenance_cost'] for label,f in [('원본',d),('처리 가정',clean)]]
section('처리 가정 전후 비교','메모리 복사본에 가동중단 999→결측, 비용 >10000→/100만 적용. 기존 실습 규칙의 적용 후보이며 원인은 데이터만으로 확정하지 않음.',pd.DataFrame(comparison,columns=['컬럼','구분','결측 수','평균','중앙값','최댓값']))
s+=['### 3단계 처리 후보','- 가동중단 시간의 미입력 후보는 행 삭제 없이 결측으로 처리한다.\n- 과도한 비용은 자릿수 오류 규칙 적용을 검토한다.\n- 고장 유형·코드 결측은 예방정비와 일치하므로 최빈값 대신 `N/A`로 구분한다.\n- 직전 정비 경과일 결측은 장비별 첫 관측 기록과 일치한다. 결측은 유지하고 첫 정비 표시를 만든다. 관측 시작 이전 이력이 없음을 입증한 것은 아니다.\n- 나머지 큰 수치는 고장 특성을 반영할 수 있으므로 크기만으로 삭제하지 않는다.']
def rates(f,cols):
 g=f.groupby(cols,dropna=False,observed=True)[y].agg(['size','sum','mean']).reset_index()
 g['mean']*=100
 return g.rename(columns={'size':'기록 수','sum':'재고장 기록 수','mean':'재고장률(%)'})
labels=d[y].value_counts().sort_index().rename_axis('정답').reset_index(name='기록 수')
labels['비중(%)']=labels['기록 수']/len(d)*100
section('정답 분포','학습 CSV의 정답 value_counts.',labels)
w=d.copy()
w['fault_category']=w.fault_category.fillna('결측(예방정비)')
w['season']=w.maintenance_date.dt.month.map({12:'겨울',1:'겨울',2:'겨울',3:'봄',4:'봄',5:'봄',6:'여름',7:'여름',8:'여름',9:'가을',10:'가을',11:'가을'})
w['year_month']=w.maintenance_date.dt.strftime('%Y-%m')
for title,cols in [('드론 유형별',['equipment_type']),('정비 구분별',['maintenance_type']),('고장 유형별',['fault_category']),('계절별',['season']),('월별',['year_month']),('유형·계절별',['equipment_type','season']),('계절·고장 유형별',['season','fault_category'])]:
 section(title,'학습 CSV의 '+', '.join(cols)+'별 정답 size·sum·mean. 계절은 정비 월 기준이며 겨울은 연도 구분 없이 집계.',rates(w,cols))
s+=['## 패턴 해석','그룹별 재고장률 차이는 추가 검토할 관찰 패턴이다. 드론 유형·계절·고장 유형의 효과를 서로 분리하거나 심각도·정비 구분을 보정한 결과가 아니다. 특히 표본이 작은 조합과 동일 장비 반복 기록은 비율의 변동성을 높일 수 있다. 고장 유형이 비어 있는 예방정비에도 재고장 기록이 있어 해당 행을 일괄 삭제하면 관측 구성이 달라진다.']
period=np.where(d.maintenance_date<='2024-06-30','학습(~2024-06-30)','검증(2024-07~12)')
section('기간 분할 준비','학습 CSV 정비일 기준 분할 후 정답 집계. 시험 정답은 미제공.',rates(d.assign(period=period),['period']))
s+=['## 다음 단계 주의사항','- 예측 시점은 정비 직후다. 그 달 전체 `availability_rate`는 미래 정보를 포함하므로 모델 입력에서 제외한다.\n- 식별자와 날짜 및 `fault_code`는 모델 입력에서 제외한다. 날짜·장비 번호는 이력 연결과 기간 분할에 사용한다.\n- 시간 피처는 정비일까지의 기록만 사용하고 시험·이번 달 피처에는 앞 기간 이력을 연결한다.\n- 위험 기준은 검증 기간에서 고르며 정답 없는 시험 자료로 시험 성능을 계산하지 않는다.\n- 정답이 미래 관측 기간으로 정의되므로 기간 경계의 정답 확정 시점도 후속 검증에서 점검한다.\n- 이 보고서는 EDA이며 정제 함수·학습 스킬·모델 재학습은 수행하지 않았다.']
assert before==hashes(),'원본 변경 감지'
section('원본 보존 확인','원본 CSV의 실행 전후 SHA-256 비교. 모두 동일.',pd.DataFrame(list(before.items()),columns=['파일','SHA-256']))
s+=['## 재현용 실행 코드','아래 코드를 PowerShell에서 `@\'`와 `\'@ | python -` 사이에 붙여 실행한다. 한글 전달을 위해 먼저 `$OutputEncoding = [System.Text.UTF8Encoding]::new()`를 실행한다. 기존 보고서 보호를 위해 재실행 전 코드의 출력 파일명을 바꾼다. 코드 부록까지 동일하게 저장하려면 현재 명령처럼 `DRONE_EDA_SOURCE` 환경변수에 코드 문자열을 전달한다.','```python\n'+os.environ['DRONE_EDA_SOURCE']+'\n```']
limits=json.loads(Path(r'C:\workspaces\pdm_ai_lab\artifacts\model_card.json').read_text(encoding='utf-8'))['limits']
s+=['## 한계와 최종 판단','아래는 기존 `C:/workspaces/pdm_ai_lab/artifacts/model_card.json`의 limits 원문이다. 이 프로젝트 모델의 검증 완료를 의미하지 않는다.','\n'.join('- '+x for x in limits)]
out.parent.mkdir(exist_ok=True)
out.write_text('\n\n'.join(s)+'\n',encoding='utf-8-sig')
assert '재현용 실행 코드' in out.read_text(encoding='utf-8-sig')
print('저장 및 재읽기 확인:',out)
print('원본 해시 일치:',before==hashes())
print(rates(w,['equipment_type']).to_string(index=False))
print(rates(w,['season']).to_string(index=False))
print('미입력 후보:',int(d.downtime_hours.eq(999).sum()),'비용 오류 후보:',int(d.maintenance_cost.gt(10000).sum()))
```

## 한계와 최종 판단

아래는 기존 `C:/workspaces/pdm_ai_lab/artifacts/model_card.json`의 limits 원문이다. 이 프로젝트 모델의 검증 완료를 의미하지 않는다.

- 교육용 가상 데이터로 학습했다. 실제 장비에 그대로 쓰지 않는다.
- 확률은 '정비 뒤 30일' 기준이다. 정비 기록이 없는 장비는 판단하지 않는다.
- 최종 판단은 정비 담당자가 한다. 모델은 점검 순서를 정하는 참고 자료다.
