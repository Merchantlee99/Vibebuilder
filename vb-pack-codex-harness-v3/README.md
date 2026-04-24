# Codex Harness v3

Codex Harness v3는 v2의 daily-driver 하네스를 기반으로 만든 `strict / high-trust` 템플릿입니다. 평소 개인 바이브코딩은 v2를 쓰고, 보안/금융/장기 운영/2인 협업처럼 더 강한 감사와 완료 차단이 필요한 프로젝트에는 v3를 사용합니다.

이 템플릿은 Codex 단독 사용을 전제로 합니다. 사용자는 자연어로 지시하고, Codex는 하네스 규칙에 따라 plan, subagent, worktree, terminal validation, browser QA, automation, independent review, strict gate를 선택합니다.

## v2와의 차이

| 구분 | v2 | v3 |
| --- | --- | --- |
| 기본 목적 | 평소 개발용 A+ 하네스 | 고신뢰 strict 템플릿 |
| Hooks | optional/off 기본 | config상 on, enforced mode에서 block |
| Review | independent review + optional HMAC | high-risk HMAC policy 내장 |
| Telemetry | hash chain + segment rotation | strict gate에서 검증 대상 |
| Model policy | planned model telemetry | strict 운영 문서와 감사 기준 포함 |
| Adoption | `--write`, optional enforce | `--profile solo/strict/team/production` |
| 운영 마찰 | 낮음 | 높음, 대신 감사성 강화 |

## 권장 사용

- 평소 개인 개발: v2
- 개인이지만 돈/보안/데이터가 걸린 프로젝트: v3 `solo` 또는 `strict`
- 최대 2인 협업: v3 `team`
- production 금융/보안/민감정보: v3 `production` + 외부 백업 + branch protection

## 핵심 구조

```text
.
├── AGENTS.md
├── README.md
├── ETHOS.md
├── .codex/
│   ├── config.toml
│   ├── agents/
│   └── hooks/
├── .agents/skills/
├── harness/
│   ├── runtime.json
│   ├── strict_policy.json
│   ├── context/
│   ├── reviews/
│   ├── telemetry/
│   ├── proposed-skills/
│   └── audits/
├── docs/ai/
├── templates/
├── scripts/harness/
└── tests/
```

## Strict Profiles

`harness/strict_policy.json`이 v3 운영 프로필을 정의합니다.

- `solo`: 개인용. hooks on, high-risk HMAC 권장, enforcement는 advisory 가능.
- `strict`: v3 기본 채택 프로필. hooks on, enforced session close, high-risk HMAC.
- `team`: 2인 협업. strict + 독립 리뷰 + protected main 권장.
- `production`: strict + branch protection + off-site telemetry backup 필수.

템플릿 상태에서는 `deployment_profile=template`, `enforcement_mode=advisory`로 둡니다. 실제 프로젝트에 복사한 뒤에만 strict profile을 활성화합니다.

## 검증

```bash
python3 scripts/harness/bootstrap.py
python3 scripts/harness/self_test.py
python3 -m unittest discover -s tests -q
python3 scripts/harness/score.py --min-score 95
python3 scripts/harness/strict_gate.py --template
```

## 프로젝트 채택

일반 strict 프로젝트:

```bash
python3 scripts/harness/adopt_project.py --check
python3 scripts/harness/adopt_project.py --write --profile strict
python3 scripts/harness/strict_gate.py --profile strict
```

개인용으로 약간 가볍게:

```bash
python3 scripts/harness/adopt_project.py --write --profile solo
python3 scripts/harness/strict_gate.py --profile solo
```

2인 협업 또는 production:

```bash
python3 scripts/harness/adopt_project.py --write --profile team
python3 scripts/harness/adopt_project.py --write --profile production
```

`strict`, `team`, `production`은 git repository 안에서 실행해야 합니다. enforced mode와 branch/CI 정책을 전제로 하기 때문입니다.

## High-Trust Review

고위험 작업은 prepared review event, nonce, artifact fingerprint, optional HMAC approval을 사용합니다.

```bash
python3 scripts/harness/review_gate.py prepare \
  --tier high-risk \
  --producer main-codex \
  --reviewer reviewer

python3 scripts/harness/review_gate.py finalize \
  --review-file harness/reviews/review-YYYYMMDDTHHMMSSZ.md \
  --require-prepared-event \
  --require-hmac \
  --hmac-secret-env HARNESS_REVIEW_SECRET \
  --approval-token <hmac-sha256(review_file:nonce)>
```

HMAC secret이 Codex 세션 밖에 있을 때만 human approval 증거가 됩니다. Codex가 secret을 볼 수 있다면 HMAC은 감사 신호일 뿐 신원 증명이 아닙니다.

## Telemetry

`event_log.py`는 NFC-normalized SHA256 hash chain, `events.manifest.json`, rotated segment를 검증합니다.

```bash
python3 scripts/harness/event_log.py verify
python3 scripts/harness/event_log.py rotate --max-bytes 1048576
python3 scripts/harness/session_index.py rebuild
python3 scripts/harness/ops_metrics.py
```

로컬 hash chain은 line tamper와 active truncate를 감지하지만, 전체 telemetry 폴더 삭제는 막지 못합니다. `production` profile에서는 GitHub Actions artifact, 별도 private repo, 외부 백업 중 하나를 운영 정책으로 연결해야 합니다.

## Completion Contract

`normal+` 작업 완료 전 요구사항:

- plan, validation, rollback artifact
- explicit ownership claim for write-scoped subagents
- independent review
- high-risk HMAC approval when strict/enforced
- event log verification
- quality gate
- session close
- residual risk and follow-up automation decision

## 공식 Codex 표면과의 관계

v3는 Codex-native 구조를 유지합니다: `AGENTS.md`, `.agents/skills`, `.codex/agents`, hooks, terminal, worktree/cloud mode, Git tools, browser, automations를 사용합니다. 다만 HMAC, hash-chain manifest, strict gate는 Codex 공식 primitive가 아니라 repo-local deterministic guardrail입니다. 공식 기능을 대체하지 않고 운영 감사와 완료 차단을 보강합니다.
