#!/usr/bin/env python3
"""Suggest a Codex Extreme Operator route for a task."""

from __future__ import annotations

import json
import re
import sys


ROUTE_KEYWORDS = {
    "release": [
        "release",
        "launch",
        "app store",
        "deploy",
        "deployment",
        "production",
        "readiness",
        "packaging",
        "ship",
        "go/no-go",
        "rollback",
        "릴리즈",
        "출시",
        "배포",
        "프로덕션",
        "운영",
        "런칭",
        "런치",
        "패키징",
        "롤백",
        "심사",
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
        "lazyweb",
        "화면",
        "디자인",
        "인터페이스",
        "플로우",
        "온보딩",
        "페이월",
        "대시보드",
        "체크아웃",
        "결제",
        "랜딩",
    ],
    "ultra": [
        "ultra",
        "extreme",
        "exhaustive",
        "market",
        "research",
        "deep research",
        "논문",
        "시장",
        "극한",
        "울트라",
        "딥리서치",
        "전부",
        "모두",
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
        "improve",
        "apply",
        "change",
        "구현",
        "수정",
        "추가",
        "고쳐",
        "고쳐줘",
        "만들어",
        "바꿔",
        "개선",
        "적용",
        "반영",
    ],
}

ROUTE_PRIORITY = ["release", "review", "debug", "design", "ultra", "deep", "normal"]

READ_ONLY_PATTERNS = [
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
    "없이",
]

CURRENT_DOCS_PATTERNS = [
    "latest",
    "current docs",
    "current version",
    "today",
    "recent",
    "release notes",
    "pricing",
    "price",
    "api",
    "docs",
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
]

SKILL_HARNESS_PATTERNS = [
    "codex-extreme-operator",
    "harness",
    "self-harness",
    "skillopt",
    "route fixture",
    "routing",
    "skill",
    "하네스",
    "스킬",
    "라우팅",
    "픽스처",
    "평가",
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

ARTIFACT_CLASS_KEYWORDS = {
    "cli": [
        "cli",
        "command line",
        "terminal tool",
        "command-line",
        "명령줄",
        "터미널 도구",
        "커맨드",
    ],
    "web_app": [
        "web app",
        "website",
        "site",
        "frontend",
        "react",
        "next.js",
        "웹앱",
        "웹 앱",
        "웹사이트",
        "사이트",
        "프론트엔드",
    ],
    "web_service": [
        "api",
        "endpoint",
        "server",
        "backend service",
        "webhook",
        "api 서버",
        "엔드포인트",
        "웹훅",
        "서버",
    ],
    "data_pipeline": [
        "pipeline",
        "etl",
        "csv",
        "jsonl",
        "dataset",
        "fixture diff",
        "파이프라인",
        "데이터셋",
        "데이터 처리",
    ],
    "ui_surface": [
        "ui",
        "ux",
        "screen",
        "dashboard",
        "checkout",
        "paywall",
        "onboarding",
        "landing",
        "화면",
        "대시보드",
        "체크아웃",
        "페이월",
        "온보딩",
        "랜딩",
    ],
    "document": [
        "readme",
        "docs",
        "document",
        "spec",
        "prd",
        "문서",
        "리드미",
        "스펙",
        "기획서",
    ],
    "research_report": [
        "research",
        "market",
        "paper",
        "report",
        "analysis",
        "조사",
        "시장",
        "논문",
        "리포트",
        "보고서",
        "분석",
    ],
    "skill_harness": [
        "skill",
        "harness",
        "route fixture",
        "skillopt",
        "self-harness",
        "스킬",
        "하네스",
        "라우팅",
        "픽스처",
    ],
    "game": [
        "game",
        "canvas",
        "three.js",
        "webgl",
        "게임",
    ],
}

PRODUCT_COMPLETE_ARTIFACTS = {
    "cli",
    "web_app",
    "web_service",
    "data_pipeline",
    "ui_surface",
    "game",
}

DESTRUCTIVE_PATTERNS = [
    "push",
    "deploy",
    "delete",
    "reset",
    "drop",
    "destroy",
    "rm -rf",
    "푸시",
    "배포",
    "삭제",
    "리셋",
    "초기화",
]

RELEASE_NOTES_PATTERNS = [
    "release notes",
    "changelog",
    "릴리즈 노트",
    "변경 로그",
]

BASE_FORBIDDEN_ACTIONS = [
    "push_remote_without_explicit_request",
    "deploy_without_explicit_request",
    "delete_data_without_explicit_request",
    "reset_history_without_explicit_request",
    "modify_secrets_without_explicit_request",
]

BASE_EVIDENCE = {
    "quick": ["direct_answer_or_command_output"],
    "normal": ["focused_tests_or_diff_evidence"],
    "deep": ["tests_or_contract_reasoning"],
    "ultra": ["source_citations_or_eval_artifacts"],
    "design": ["source_backed_references", "rendered_visual_proof"],
    "debug": ["reproduction_or_nonrepro_reason", "root_cause_evidence", "regression_check"],
    "review": ["findings_with_file_or_source_references"],
    "release": ["gate_checklist", "risk_inventory", "rollback_notes"],
}


def keyword_matches(text: str, keyword: str) -> bool:
    if any(ch.isascii() and ch.isalnum() for ch in keyword):
        return re.search(rf"(?<![A-Za-z0-9_-]){re.escape(keyword)}(?![A-Za-z0-9_-])", text) is not None
    return keyword in text


def match_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword_matches(text, keyword)]


def any_match(text: str, keywords: list[str]) -> bool:
    return bool(match_keywords(text, keywords))


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
    if release_gate:
        return "release_gate"
    if read_only:
        return "supporting_or_read_only"
    if implementation_requested and artifact_class in PRODUCT_COMPLETE_ARTIFACTS:
        return "product_complete"
    if implementation_requested:
        return "code_complete"
    if route in {"review", "quick"}:
        return "supporting_or_read_only"
    return "analysis_complete"


def build_constraints(lowered: str, hits: dict[str, list[str]]) -> dict[str, object]:
    release_notes_query = any_match(lowered, RELEASE_NOTES_PATTERNS)
    release_gate = bool(hits.get("release")) and not release_notes_query
    review_requested = bool(hits.get("review"))
    security_sensitive = any_match(lowered, SECURITY_PATTERNS)
    read_only = any_match(lowered, READ_ONLY_PATTERNS)
    current_docs_required = any_match(lowered, CURRENT_DOCS_PATTERNS)
    skill_harness = any_match(lowered, SKILL_HARNESS_PATTERNS)
    design_hits = hits.get("design", [])
    skill_flow_only = skill_harness and bool(design_hits) and set(design_hits) <= {"플로우", "design"}
    product_ui = bool(design_hits) and not skill_flow_only
    destructive_action_requested = any_match(lowered, DESTRUCTIVE_PATTERNS)
    normal_hits = hits.get("normal", [])
    current_applied_only = bool(normal_hits) and set(normal_hits) <= {"적용"} and "적용된" in lowered
    implementation_requested = bool(normal_hits) and not current_applied_only and not read_only
    artifact_class = infer_artifact_class(lowered, skill_harness=skill_harness)
    route_hint = "release" if release_gate else ""
    completion_mode = infer_completion_mode(
        route=route_hint,
        artifact_class=artifact_class,
        read_only=read_only,
        implementation_requested=implementation_requested,
        release_gate=release_gate,
    )
    return {
        "read_only": read_only,
        "current_docs_required": current_docs_required,
        "product_ui": product_ui,
        "release_gate": release_gate,
        "review_requested": review_requested,
        "security_sensitive": security_sensitive,
        "skill_harness": skill_harness,
        "destructive_action_requested": destructive_action_requested,
        "implementation_requested": implementation_requested,
        "release_notes_query": release_notes_query,
        "artifact_class": artifact_class,
        "completion_mode": completion_mode,
    }


def choose_route(hits: dict[str, list[str]], constraints: dict[str, bool]) -> str:
    adjusted_hits = dict(hits)
    if constraints["read_only"]:
        adjusted_hits.pop("normal", None)
    if constraints["release_notes_query"] and not constraints["release_gate"]:
        adjusted_hits.pop("release", None)

    if constraints["skill_harness"] and "ultra" not in adjusted_hits:
        adjusted_hits.setdefault("deep", ["skill_harness"])

    if constraints["release_gate"]:
        return "release"

    for route in ROUTE_PRIORITY:
        if route in adjusted_hits:
            return route
    return "quick"


def suggested_skills(route: str, constraints: dict[str, bool]) -> list[str]:
    if route == "release":
        skills = ["evidence-loop", "review-swarm", "git-checkpoint"]
    elif route == "review":
        skills = ["review-swarm"]
    elif route == "debug":
        skills = ["debug-root-cause", "evidence-loop"]
    elif route == "design":
        skills = ["design-impact-router", "visual-qa"]
    elif route == "ultra":
        skills = ["deep-research-swarm", "evidence-loop", "review-swarm"]
    elif route == "deep":
        skills = ["tdd-implementation", "evidence-loop"]
    elif route == "normal":
        skills = ["tdd-implementation", "evidence-loop"]
    else:
        skills = []

    if constraints["skill_harness"] and "harness-doctor" not in skills:
        skills.insert(0, "harness-doctor")
    if constraints["read_only"]:
        skills = [skill for skill in skills if skill not in {"tdd-implementation", "git-checkpoint"}]
    return skills


def evidence_required(route: str, constraints: dict[str, object]) -> list[str]:
    evidence = list(BASE_EVIDENCE[route])
    if constraints["current_docs_required"] and "current_primary_sources" not in evidence:
        evidence.append("current_primary_sources")
    if constraints["read_only"] and "explicit_no_edit_confirmation" not in evidence:
        evidence.append("explicit_no_edit_confirmation")
    if constraints["skill_harness"] and "route_fixture_or_heldout_validation" not in evidence:
        evidence.append("route_fixture_or_heldout_validation")
    artifact_class = constraints.get("artifact_class")
    artifact_evidence = {
        "cli": "headless_cli_run_or_golden_output",
        "web_app": "rendered_visual_state_evidence",
        "web_service": "api_smoke_or_contract_check",
        "data_pipeline": "fixture_output_diff",
        "ui_surface": "rendered_visual_state_evidence",
        "document": "source_consistency_check",
        "research_report": "source_citations_and_fact_inference_split",
        "skill_harness": "train_and_heldout_route_validation",
        "game": "runtime_or_visual_playability_probe",
    }.get(artifact_class)
    if artifact_evidence and artifact_evidence not in evidence:
        evidence.append(artifact_evidence)
    completion_mode = constraints.get("completion_mode")
    if completion_mode in {"product_complete", "release_gate"}:
        for item in ("safe_but_wrong_artifact_class_check", "claim_to_evidence_matrix"):
            if item not in evidence:
                evidence.append(item)
    elif completion_mode == "supporting_or_read_only":
        if "artifact_scope_confirmation" not in evidence:
            evidence.append("artifact_scope_confirmation")
    return evidence


def forbidden_actions(constraints: dict[str, bool]) -> list[str]:
    actions = list(BASE_FORBIDDEN_ACTIONS)
    if constraints["read_only"]:
        actions.extend(["edit_files", "write_files", "stage_or_commit_changes"])
    return actions


def confidence_for(route: str, hits: dict[str, list[str]], constraints: dict[str, bool]) -> float:
    if route == "quick":
        base = 0.45 if constraints["current_docs_required"] else 0.35
    else:
        base = 0.55 + len(hits.get(route, [])) * 0.08
    if constraints["read_only"]:
        base += 0.05
    if constraints["skill_harness"]:
        base += 0.05
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
        artifact_class=str(constraints.get("artifact_class", "unspecified")),
        read_only=bool(constraints["read_only"]),
        implementation_requested=bool(constraints["implementation_requested"]),
        release_gate=bool(constraints["release_gate"]),
    )
    return {
        "route": route,
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
