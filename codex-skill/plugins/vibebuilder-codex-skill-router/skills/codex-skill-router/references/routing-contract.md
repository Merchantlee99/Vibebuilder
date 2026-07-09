# GPT-5.6 Routing Contract

`classify_task.py`는 일반 작업을 범용 라우터로 감싸지 않는 `native-first` 계약을 반환한다.

| 필드 | 의미 |
| --- | --- |
| `routing_policy` | 항상 `native-first` |
| `route` | `quick`, `normal`, `deep`, `ultra`, `design`, `debug`, `review`, `release` 중 하나 |
| `reasoning_effort_hint` | `default`, `high`, `xhigh` 설정 힌트. 프롬프트 문구가 아님 |
| `confidence` | 0~1 휴리스틱 신뢰도 |
| `matched` | route 판단에 쓰인 키워드 |
| `constraints` | 턴 전체에서 보존할 권한·아티팩트·완료 경계 |
| `suggested_skills` | 실제 트리거가 맞는 최소 전문 스킬 조합 |
| `evidence_required` | 완료 전에 필요한 증거 |
| `forbidden_actions` | 명시적 권한 없이는 실행할 수 없는 동작 |

## 핵심 제약

- 구현 동사가 없는 답변·설명·분석·리뷰·진단·계획 요청은 기본적으로 `read_only=true`다.
- `current_docs_required=true`이면 공식 또는 최신 1차 출처를 사용한다.
- `remote_write_requested=true`는 사용자가 push, publish, GitHub 업로드 또는 머지를 명시했을 때만 설정된다.
- `artifact_class`와 `completion_mode`는 증거 강도를 결정한다.
- 작은 편집은 전문 스킬 없이 처리할 수 있어야 한다.
- `product_complete`와 `release_gate`는 `safe_but_wrong_artifact_class_check`와 `claim_to_evidence_matrix`를 요구한다.
- read-only 지원 산출물은 `artifact_scope_confirmation`으로 제품 완료 주장과 구분한다.

## 조합 원칙

- OpenAI 현재 정보 → `openai-docs`
- 스킬·라우팅 변경 → `harness-doctor`
- 원인 조사 → `debug-root-cause`
- 명시적 감사·출시 검수 → `review-swarm`
- 대규모 최신 조사 → `deep-research-swarm`
- 동작을 가진 백엔드/API 로직 → `tdd-implementation`
- 중요한 UI 방향 탐색 → `lazyweb-design`, 구현 후 → `visual-qa`
- 제품 완료·수정 검증·출시 → `evidence-loop`
- 명시적 원격 게시 → `git-checkpoint`

## 수용 기준

```bash
python3 scripts/route_eval.py --suite train
python3 scripts/route_eval.py --suite heldout
```

route 일치만 보지 않는다. read-only 기본값, artifact/completion mode, skill 수 상한, 공식 문서 선택, evidence와 forbidden action도 함께 회귀 검사한다. 세부 gate는 `ouroboros-lite-gates.md`를 따른다.
