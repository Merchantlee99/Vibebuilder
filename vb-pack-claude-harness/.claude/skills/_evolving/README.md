# `_evolving/` — Auto-generated Skills

이 디렉토리는 **Layer 4 self-evolving** 계층이 생성한 skill 초안이 들어오는
공간이다. `scripts/harness/skill_auto_gen.py` 가 events.jsonl 에서 동일
task 패턴을 ≥ 3회 관찰하면 여기에 draft 를 제안한다.

## 상태 단계

| 상태 | 위치 | 의미 |
|------|------|------|
| `draft-proposed` | `_evolving/<slug>/SKILL.md` | 자동 생성됨. 사용자 승인 대기 |
| `user-approved` | `_manual/<slug>/SKILL.md` 로 이동 | 정식 스킬로 승격 |
| `rejected` | `_evolving/<slug>/REJECTED.md` 표시 | 제안 폐기. 재발 시 무시 |

## 승인 flow

1. 자동 제안이 `_evolving/<slug>/SKILL.md` 에 작성됨
2. 사용자가 읽고 판단:
   - **수락** → `mv _evolving/<slug> _manual/<slug>` + frontmatter 의 `status` 를 `active` 로
   - **거절** → `touch _evolving/<slug>/REJECTED.md`
   - **보류** → 아무것도 안 함. 다음 rollup 때 다시 검토됨
3. 이동/거절 이벤트는 Gate ⑦ 가 감시. 이 디렉토리는 **AI 단독 수정 불가**.

## 자동 생성 기준

`skill_auto_gen.py` 가 제안을 만들기 전 다음을 확인:

- 동일 task 패턴 events 이 최소 3건 누적
- 기존 `_manual/` 스킬과 70% 이상 겹치지 않음 (TBD: similarity clustering)
- 최근 30일 이내 발생
- 사용자가 `runtime.json → self_evolving.skill_auto_gen_enabled == true` 로 허용

## 초안 품질

자동 생성 draft 는 **완전한 스킬이 아니다**. 다음을 채워야 active 가능:

- `## 언제 쓰는가` — 자동 생성은 "<pattern> 이 발생할 때" 수준. 구체화 필요.
- `## 단계` — 관찰된 trajectory 에서 추출. 검증 필요.
- `## 가드레일` — 기본 3개만 자동 (Layer 3 gates 준수, actor crossover, sealed prompt). 도메인별 제약 추가 필요.

## 실수 방지

- `_evolving/` 의 skill 을 **활성 스킬 카탈로그** (`/skills` 슬래시 명령 결과) 에 보이지 않도록 하는 것이 기본
- 사용자가 `_manual/` 로 이동시킨 후에만 카탈로그 노출
- `REJECTED.md` 가 있는 slug 는 향후 제안에서 제외

## 디렉토리 예시 (초기엔 비어있음)

```
_evolving/
├── README.md                    ← 이 파일
└── (empty until skill_auto_gen.py proposes something)
```

---

**이 README 는 사용자가 편집 가능** (Gate ⑦ 보호 대상 아님 — 문서일 뿐).
다만 `_evolving/<slug>/` 안의 실제 skill 파일은 Gate ⑦ 보호 목록에 들어간다
(현재 skeleton 단계에서는 아직 아니지만, v1 에서 추가 예정).
