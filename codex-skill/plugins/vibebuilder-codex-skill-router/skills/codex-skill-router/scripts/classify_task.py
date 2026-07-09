#!/usr/bin/env python3
"""Suggest a GPT-5.6 native-first Codex skill route for a task."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


ROUTING_POLICY = "native-first"

ROUTE_KEYWORDS = {
    "release": [
        "release",
        "launch",
        "deploy",
        "deployment",
        "production",
        "readiness",
        "go/no-go",
        "rollback",
        "publish",
        "push",
        "pull request",
        "릴리즈",
        "출시",
        "배포",
        "프로덕션",
        "운영",
        "런칭",
        "런치",
        "롤백",
        "업로드",
        "푸시",
        "머지",
    ],
    "review": [
        "review",
        "audit",
        "red-team",
        "red team",
        "critique",
        "code review",
        "검수",
        "레드팀",
        "리뷰",
        "코드 리뷰",
        "코드리뷰",
        "검토",
        "감사",
    ],
    "debug": [
        "debug",
        "bug",
        "crash",
        "fail",
        "failure",
        "broken",
        "stuck",
        "flaky",
        "regression",
        "reproduce",
        "root cause",
        "디버그",
        "오류",
        "실패",
        "버그",
        "고장",
        "안됨",
        "안돼",
        "안 돼",
        "멈춤",
        "원인",
        "재현",
        "에러",
        "깨짐",
        "장애",
        "느림",
        "지연",
        "플래키",
    ],
    "design": [
        "ui",
        "ux",
        "screen",
        "swiftui",
        "figma",
        "design",
        "onboarding",
        "paywall",
        "dashboard",
        "checkout",
        "pricing page",
        "landing",
        "button",
        "화면",
        "디자인",
        "인터페이스",
        "온보딩",
        "페이월",
        "대시보드",
        "체크아웃",
        "결제 화면",
        "랜딩",
        "버튼",
    ],
    "ultra": [
        "ultra",
        "extreme",
        "exhaustive",
        "deep research",
        "market research",
        "competitive research",
        "논문 조사",
        "시장 조사",
        "울트라",
        "딥리서치",
        "전수 조사",
    ],
    "deep": [
        "backend",
        "database",
        "postgres",
        "auth",
        "safety",
        "privacy",
        "quota",
        "model gateway",
        "eval",
        "architecture",
        "architectural",
        "contract",
        "migration",
        "설계",
        "구조",
        "아키텍처",
        "백엔드",
        "데이터베이스",
        "인증",
        "개인정보",
        "보안",
        "안전",
        "하네스",
        "스킬",
        "라우팅",
        "평가",
    ],
    "normal": [
        "implement",
        "build",
        "fix",
        "modify",
        "add",
        "change",
        "update",
        "refactor",
        "create",
        "edit",
        "apply",
        "install",
        "configure",
        "구현",
        "수정",
        "추가",
        "고쳐",
        "만들어",
        "바꿔",
        "변경",
        "개선",
        "적용",
        "반영",
        "설치",
        "재설계",
        "작성",
    ],
}

ROUTE_PRIORITY = ["release", "review", "debug", "design", "ultra", "deep", "normal"]

EXPLICIT_READ_ONLY_PATTERNS = [
    "read-only",
    "read only",
    "do not edit",
    "don't edit",
    "without changing",
    "without modifying",
    "without editing",
    "no edits",
    "analysis only",
    "analyze only",
    "수정하지",
    "수정은 하지",
    "수정 변경 하지",
    "변경하지",
    "바꾸지",
    "건드리지",
    "읽기 전용",
    "분석만",
    "검토만",
    "제안만",
    "하지마",
    "하지 말고",
]

IMPLEMENTATION_PATTERNS = [
    r"\b(?:implement|build|fix|modify|add|change|update|refactor|create|edit|apply|install|configure)\b",
    r"^improve\b",
    r"\band (?:improve|implement|build|fix|modify|change|update|edit|apply)\b",
    r"(?:구현|수정|추가|고쳐|만들어|바꿔|바꾸|변경|적용|반영|설치|재설계|작성)(?:해|하|서|해서|하고|고|한 뒤|할 것|을 하고|를 하고|줘|주세요)",
    r"개선(?:해|하|해서|하고|한 뒤|할 것|을 하고|를 하고|줘|주세요)",
]

CURRENT_DOCS_PATTERNS = [
    "latest",
    "current docs",
    "current version",
    "current references",
    "today",
    "recent",
    "release notes",
    "pricing",
    "price",
    "official",
    "market",
    "law",
    "regulation",
    "최신",
    "오늘",
    "요즘",
    "최근",
    "릴리즈 노트",
    "가격",
    "요금",
    "공식",
    "시장",
    "법률",
    "법적",
    "규정",
    "현재 버전",
]

OPENAI_PATTERNS = ["openai", "gpt-", "gpt ", "codex", "chatgpt"]

SKILL_HARNESS_PATTERNS = [
    "codex-extreme-operator",
    "codex skill",
    "skill router",
    "harness",
    "self-harness",
    "skillopt",
    "route fixture",
    "routing",
    "하네스",
    "스킬",
    "라우팅",
    "픽스처",
]

SECURITY_PATTERNS = [
    "security",
    "auth",
    "privacy",
    "permission",
    "injection",
    "secrets",
    "보안",
    "인증",
    "권한",
    "개인정보",
    "시크릿",
]

REMOTE_WRITE_PATTERNS = [
    "push",
    "publish",
    "pull request",
    "푸시",
    "업로드",
    "머지",
]

RELEASE_NOTES_PATTERNS = ["release notes", "changelog", "릴리즈 노트", "변경 로그"]

PRODUCTION_RELEASE_PATTERNS = [
    "release",
    "launch",
    "deploy",
    "deployment",
    "production",
    "readiness",
    "go/no-go",
    "rollback",
    "릴리즈",
    "출시",
    "배포",
    "프로덕션",
    "운영",
    "런칭",
    "런치",
    "롤백",
]

VERIFY_PATTERNS = [
    "test",
    "verify",
    "validate",
    "check",
    "proof",
    "finish",
    "테스트",
    "검증",
    "확인",
    "증명",
    "끝까지",
    "마무리",
]

SIGNIFICANT_DESIGN_PATTERNS = [
    "ux",
    "onboarding",
    "paywall",
    "dashboard",
    "checkout",
    "landing",
    "research",
    "reference",
    "current references",
    "사용자 경험",
    "온보딩",
    "페이월",
    "대시보드",
    "체크아웃",
    "랜딩",
    "리서치",
    "레퍼런스",
    "결제 화면",
]

SCOPED_UI_PATTERNS = [
    "only",
    "just",
    "color only",
    "copy only",
    "spacing only",
    "색상만",
    "문구만",
    "간격만",
    "버튼만",
]

BEHAVIOR_CODE_PATTERNS = [
    "api",
    "backend",
    "database",
    "server",
    "runtime",
    "logic",
    "auth",
    "persistence",
    "quota",
    "model gateway",
    "백엔드",
    "데이터베이스",
    "서버",
    "로직",
    "인증",
    "런타임",
    "영속성",
]

ARTIFACT_CLASS_KEYWORDS = {
    "cli": ["cli", "command line", "terminal tool", "명령줄", "터미널 도구"],
    "web_service": ["api", "endpoint", "server", "backend service", "webhook", "서버", "엔드포인트", "웹훅"],
    "web_app": ["web app", "website", "site", "frontend", "react", "next.js", "웹앱", "웹사이트", "프론트엔드"],
    "data_pipeline": ["pipeline", "etl", "csv", "dataset", "fixture diff", "파이프라인", "데이터셋"],
    "ui_surface": ["ui", "ux", "screen", "dashboard", "checkout", "paywall", "landing", "화면", "대시보드", "버튼"],
    "document": ["readme", "docs", "document", "spec", "prd", "문서", "리드미", "기획서"],
    "research_report": ["research", "market", "paper", "report", "analysis", "조사", "시장", "논문", "보고서", "분석"],
    "game": ["game", "canvas", "three.js", "webgl", "게임"],
}

PRODUCT_COMPLETE_ARTIFACTS = {"cli", "web_app", "web_service", "data_pipeline", "ui_surface", "game"}

BASE_FORBIDDEN_ACTIONS = [
    "push_remote_without_explicit_request",
    "deploy_without_explicit_request",
    "delete_data_without_explicit_request",
    "reset_history_without_explicit_request",
    "modify_secrets_without_explicit_request",
]


def keyword_matches(text: str, keyword: str) -> bool:
    if any(ch.isascii() and ch.isalnum() for ch in keyword):
        return re.search(rf"(?<![A-Za-z0-9_-]){re.escape(keyword)}(?![A-Za-z0-9_-])", text) is not None
    return keyword in text


def match_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword_matches(text, keyword)]


def any_match(text: str, keywords: list[str]) -> bool:
    return bool(match_keywords(text, keywords))


def any_regex(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def infer_artifact_class(lowered: str, *, skill_harness: bool) -> str:
    if skill_harness:
        return "skill_harness"
    for artifact_class, keywords in ARTIFACT_CLASS_KEYWORDS.items():
        if any_match(lowered, keywords):
            return artifact_class
    return "unspecified"


def infer_completion_mode(
    *,
    route: str,
    artifact_class: str,
    read_only: bool,
    implementation_requested: bool,
    release_gate: bool,
) -> str:
    if read_only:
        return "supporting_or_read_only" if route in {"quick", "review", "release"} else "analysis_complete"
    if release_gate:
        return "release_gate"
    if implementation_requested and artifact_class in PRODUCT_COMPLETE_ARTIFACTS:
        return "product_complete"
    if implementation_requested:
        return "code_complete"
    return "analysis_complete"


def build_constraints(lowered: str, hits: dict[str, list[str]]) -> dict[str, Any]:
    explicit_read_only = any_match(lowered, EXPLICIT_READ_ONLY_PATTERNS)
    implementation_requested = any_regex(lowered, IMPLEMENTATION_PATTERNS) and not explicit_read_only
    read_only = explicit_read_only or not implementation_requested
    release_notes_query = any_match(lowered, RELEASE_NOTES_PATTERNS)
    remote_write_requested = any_match(lowered, REMOTE_WRITE_PATTERNS) and not read_only
    production_release = any_match(lowered, PRODUCTION_RELEASE_PATTERNS) and not release_notes_query
    release_gate = (production_release or remote_write_requested) and not release_notes_query
    review_requested = bool(hits.get("review"))
    product_ui = bool(hits.get("design"))
    security_sensitive = any_match(lowered, SECURITY_PATTERNS)
    openai_work = any_match(lowered, OPENAI_PATTERNS)
    versioned_openai_work = openai_work and bool(re.search(r"(?:gpt[- ]?\d|codex app|openai)", lowered))
    current_docs_required = any_match(lowered, CURRENT_DOCS_PATTERNS) or versioned_openai_work
    skill_harness = any_match(lowered, SKILL_HARNESS_PATTERNS)
    verify_requested = any_match(lowered, VERIFY_PATTERNS)
    significant_design = (
        product_ui
        and any_match(lowered, SIGNIFICANT_DESIGN_PATTERNS)
        and not any_match(lowered, SCOPED_UI_PATTERNS)
    )
    behavior_code = implementation_requested and any_match(lowered, BEHAVIOR_CODE_PATTERNS)
    artifact_class = infer_artifact_class(lowered, skill_harness=skill_harness)
    return {
        "read_only": read_only,
        "current_docs_required": current_docs_required,
        "product_ui": product_ui,
        "release_gate": release_gate,
        "production_release": production_release,
        "review_requested": review_requested,
        "debug_requested": bool(hits.get("debug")),
        "security_sensitive": security_sensitive,
        "skill_harness": skill_harness,
        "implementation_requested": implementation_requested,
        "remote_write_requested": remote_write_requested,
        "release_notes_query": release_notes_query,
        "openai_work": openai_work,
        "verify_requested": verify_requested,
        "significant_design": significant_design,
        "behavior_code": behavior_code,
        "artifact_class": artifact_class,
    }


def choose_route(hits: dict[str, list[str]], constraints: dict[str, Any]) -> str:
    adjusted_hits = dict(hits)
    if constraints["release_notes_query"]:
        adjusted_hits.pop("release", None)
    if constraints["release_gate"]:
        return "release"
    if constraints["skill_harness"] and not any(route in adjusted_hits for route in ("review", "debug", "ultra")):
        adjusted_hits.setdefault("deep", ["skill_harness"])
    for route in ROUTE_PRIORITY:
        if route in adjusted_hits:
            return route
    return "quick"


def reasoning_effort_hint(route: str) -> str:
    if route in {"ultra", "release"}:
        return "xhigh"
    if route in {"deep", "debug", "review"}:
        return "high"
    return "default"


def append_unique(skills: list[str], skill: str) -> None:
    if skill not in skills:
        skills.append(skill)


def suggested_skills(route: str, constraints: dict[str, Any]) -> list[str]:
    skills: list[str] = []

    if constraints["current_docs_required"] and constraints["openai_work"]:
        append_unique(skills, "openai-docs")
    if constraints["skill_harness"]:
        append_unique(skills, "harness-doctor")
    if constraints["debug_requested"]:
        append_unique(skills, "debug-root-cause")
    if route == "ultra" and not constraints["skill_harness"]:
        append_unique(skills, "deep-research-swarm")
    if constraints["product_ui"] and constraints["significant_design"]:
        append_unique(skills, "lazyweb-design")
    if constraints["behavior_code"] and route in {"normal", "deep"} and not constraints["debug_requested"]:
        append_unique(skills, "tdd-implementation")
    if constraints["review_requested"] or constraints["production_release"]:
        append_unique(skills, "review-swarm")
    if constraints["product_ui"] and (constraints["implementation_requested"] or constraints["verify_requested"]):
        append_unique(skills, "visual-qa")

    needs_evidence_loop = (
        constraints["release_gate"]
        or (constraints["debug_requested"] and constraints["implementation_requested"])
        or (constraints.get("completion_mode") == "product_complete" and not constraints["product_ui"])
        or (
            constraints["verify_requested"]
            and constraints["implementation_requested"]
            and not constraints["product_ui"]
        )
    )
    if needs_evidence_loop:
        append_unique(skills, "evidence-loop")
    if constraints["remote_write_requested"]:
        append_unique(skills, "git-checkpoint")
    return skills


def evidence_required(route: str, constraints: dict[str, Any]) -> list[str]:
    evidence_by_route = {
        "quick": ["direct_answer_or_command_output"],
        "normal": ["focused_diff_or_test_evidence"],
        "deep": ["contract_or_source_reasoning"],
        "ultra": ["current_source_citations"],
        "design": ["rendered_visual_proof"] if not constraints["read_only"] else ["source_backed_references"],
        "debug": ["root_cause_evidence", "regression_check"] if not constraints["read_only"] else ["root_cause_evidence"],
        "review": ["findings_with_file_or_source_references"],
        "release": ["gate_checklist", "risk_inventory", "rollback_notes"],
    }
    evidence = list(evidence_by_route[route])
    if constraints["current_docs_required"]:
        evidence.append("current_primary_sources")
    if constraints["skill_harness"]:
        evidence.append("train_and_heldout_route_validation")

    artifact_evidence = {
        "cli": "headless_cli_run_or_golden_output",
        "web_app": "rendered_visual_state_evidence",
        "web_service": "api_smoke_or_contract_check",
        "data_pipeline": "fixture_output_diff",
        "ui_surface": "rendered_visual_state_evidence",
        "document": "source_consistency_check",
        "research_report": "source_citations_and_fact_inference_split",
        "skill_harness": "fresh_prompt_discovery_check",
        "game": "runtime_or_visual_playability_probe",
    }.get(constraints["artifact_class"])
    if artifact_evidence and artifact_evidence not in evidence:
        evidence.append(artifact_evidence)
    return evidence


def forbidden_actions(constraints: dict[str, Any]) -> list[str]:
    actions = list(BASE_FORBIDDEN_ACTIONS)
    if constraints["remote_write_requested"]:
        actions.remove("push_remote_without_explicit_request")
    if constraints["read_only"]:
        actions.extend(["edit_files", "write_files", "stage_or_commit_changes"])
    return actions


def confidence_for(route: str, hits: dict[str, list[str]], constraints: dict[str, Any]) -> float:
    if route == "quick":
        base = 0.5 if constraints["current_docs_required"] else 0.4
    else:
        base = 0.58 + min(len(hits.get(route, [])), 3) * 0.08
    if constraints["skill_harness"]:
        base += 0.04
    if constraints["read_only"]:
        base += 0.03
    return round(min(0.95, base), 2)


def classify(text: str) -> dict[str, object]:
    lowered = text.lower()
    hits: dict[str, list[str]] = {}
    for route, keywords in ROUTE_KEYWORDS.items():
        matched = match_keywords(lowered, keywords)
        if matched:
            hits[route] = matched

    constraints = build_constraints(lowered, hits)
    route = choose_route(hits, constraints)
    constraints["completion_mode"] = infer_completion_mode(
        route=route,
        artifact_class=str(constraints["artifact_class"]),
        read_only=bool(constraints["read_only"]),
        implementation_requested=bool(constraints["implementation_requested"]),
        release_gate=bool(constraints["release_gate"]),
    )
    return {
        "routing_policy": ROUTING_POLICY,
        "route": route,
        "reasoning_effort_hint": reasoning_effort_hint(route),
        "confidence": confidence_for(route, hits, constraints),
        "matched": hits,
        "constraints": constraints,
        "suggested_skills": suggested_skills(route, constraints),
        "evidence_required": evidence_required(route, constraints),
        "forbidden_actions": forbidden_actions(constraints),
    }


def main() -> int:
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        text = sys.stdin.read().strip()
    print(json.dumps(classify(text), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
