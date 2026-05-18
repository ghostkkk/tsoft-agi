---
name: agi-review
description: |
  현재 프로젝트의 candidate commits 를 가져와 사용자에게 표로 보여주고, 일괄 또는 개별 merge를 처리한다.
  사용자가 "commit 검토", "candidate 확인", "merge 처리", "AGI 정리", "쌓인 거 정리", "review 해줘", "묶어서 merge"를 요청하거나 AGI 페이지에 가지 않고 채팅 안에서 운영하고 싶을 때 호출한다.
  단독 검토 필요한 commit_type (direction_update / deprecated_direction / decision_changed) 은 일괄 merge에서 제외하고 별도로 안내.
argument-hint: "[project-id] [--auto-merge]"
---

# AGI Review — candidate commits 검토 + merge

목표: 사용자가 AGI 페이지를 안 보고도 채팅 안에서 candidates를 검토/병합.

## 0. 인자 정리
- `project-id`: 없으면 현재 cwd → project_map 추론. 그래도 없으면 사용자에게 묻기.
- `--auto-merge`: 일괄 가능 항목을 사용자 확인 없이 즉시 merge. 단독 검토 필요한 건 여전히 묻는다.

## 1. candidates 가져오기
```
curl -sL "https://erp.t-soft.co.kr/api/commits?project_id=<id>&status=candidate"
```

## 2. 표로 보여주기
다음 형식:
```
🔖 RecoveryT — candidate commits (N개)

#   type                  source   title (운전자 요청 ↘ AI 응답)
1   deprecated_direction  codex    "직접 설치하자" ↘ winget으로 WDK 10.0.26100…  ⚠ 단독
2   mixed                 codex    "동작 테스트 환경 다 구축" ↘ WDK/VS/MSBuild…
3   task_added            codex    "다음 단계는?" ↘ read-only minifilter PoC…
...

일괄 merge 가능 (단독 제외): N개
단독 검토 필요: M개  (direction_update / deprecated_direction / decision_changed)
```

- title의 `RAW:` prefix 제거.
- "사용자 요청: X 응답: Y" 패턴 매치 시 `X ↘ Y` 형식으로 압축 (양쪽 한 줄 잘림).

## 3. 사용자 응답 받기
다음 중 하나를 묻기:
- `all` — 일괄 가능 전체 merge
- `1,3,5` — 번호 선택 merge
- `skip 2,4` — 그 외 전체 merge
- `q` — 그만

## 4. merge 실행
### 일괄 (단독 아닌 것):
```
curl -sL -X POST "https://erp.t-soft.co.kr/api/commits/batch-merge" \
  -H "Content-Type: application/json" \
  -d '{"commit_ids":["<id1>","<id2>","..."],"merged_by":"<user-name>"}'
```

### 개별 (단독 검토 필요한 것):
- 사용자에게 한 개씩 보여주고 commit 상세 (decisions/tasks/risks 다 표시) → y/n 확인
- y면:
  ```
  curl -sL -X POST "https://erp.t-soft.co.kr/api/commits/<id>/merge" \
    -H "Content-Type: application/json" \
    -d '{"merged_by":"<user-name>"}'
  ```
- n면 reject:
  ```
  curl -sL -X POST "https://erp.t-soft.co.kr/api/commits/<id>/reject" \
    -H "Content-Type: application/json" \
    -d '{"merged_by":"<user-name>","reason":"<짧은 사유>"}'
  ```

## 5. 결과 보고
```
✓ merged 12개
✗ rejected 1개  (사유: <...>)
⚠ skipped 0개

Memory 업데이트:
 + confirmed_decisions 6개 신규
 + active_tasks 4개 신규
 + risks 2개 신규
 + deprecated 1개 신규
```

## 6. 응답 마지막 한 줄
```
ERP: skipped review-meta-action  (review 자체는 운영 메타. 결과는 이미 server에 반영됨)
```

## 주의
- 사용자 동의 없는 자동 merge 금지 (단 `--auto-merge` 인자 명시 시 일괄만).
- 단독 검토 필요 항목은 절대 사용자 동의 없이 merge X.
