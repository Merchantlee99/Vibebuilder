# Plugin Adoption

이 플러그인은 GPT-5.6에서 모든 복잡한 작업을 사전 분류하지 않는다. 일반 작업은 모델이 직접 수행하고, 스킬·라우팅 하네스를 다룰 때만 `$codex-skill-router`를 명시적으로 호출한다.

## 전역 설치

사용자가 전역 변경을 명시적으로 요청한 경우에만 실행한다.

```bash
python3 scripts/install_global.py --dry-run
python3 scripts/install_global.py
```

설치기는 다음을 수행한다.

1. 현재 `~/.codex/AGENTS.md`, `~/.codex/config.toml`, 기존 설치본을 timestamp backup으로 보존한다.
2. 스킬을 `~/.agents/skills/codex-skill-router`에 복사한다.
3. Lazyweb와 Codex Extreme Operator의 광범위한 전역 강제 블록을 제거하고 짧은 GPT-5.6 계약을 추가한다.
4. 기본 reasoning effort를 `high`로 설정한다.
5. `apex`, `codex-extreme-operator`, `design-impact-router`를 backup 아래로 옮겨 active discovery에서 제외하고, config에도 disabled 상태를 남긴다.
6. 현재 App CLI가 거부하는 `network_access`, `child_agents_md`, `plugin_hooks`를 제거하고 deprecated `codex_hooks`를 `hooks`로 옮긴다.

백업 경로:

```text
~/.codex/backups/vibebuilder-codex-5-6/<timestamp>/
```

## App 반영 확인

새 Codex App 작업에서 App 번들 CLI의 prompt-input을 확인한다.

```bash
/Applications/ChatGPT.app/Contents/Resources/codex debug prompt-input \
  'Use $codex-skill-router to inspect this skill setup'
```

검수 조건:

- 전역 지시에 `VIBEBUILDER:CODEX-5-6` 블록이 보인다.
- 기본 prompt에는 `codex-skill-router`가 보이지 않는다. `allow_implicit_invocation=false`의 의도된 결과다.
- `$codex-skill-router`를 명시 호출하면 설치 경로의 `SKILL.md`와 bundled classifier가 실행된다.
- 비활성화한 legacy skill은 활성 스킬 목록에 보이지 않는다.
- 새 작업의 기본 model reasoning effort가 `high`다.

Codex App는 이미 열린 작업의 시스템 컨텍스트를 소급 교체하지 않는다. 검수는 반드시 새 prompt-input 또는 새 작업 기준으로 수행한다.
