from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = {
    "id",
    "language",
    "category",
    "topic",
    "no_analysis",
    "required_artifacts",
    "required_sections",
    "minimum_citations",
}
ALLOWED_LANGUAGES = {"en", "zh"}
ALLOWED_ARTIFACTS = {
    "question",
    "research_plan",
    "findings",
    "analysis",
    "draft",
    "report",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise TypeError(f"{path}:{line_number}: each line must be an object")
        cases.append(value)
    return cases


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_case(case: dict[str, Any], location: str) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_FIELDS - case.keys()
    extra = case.keys() - REQUIRED_FIELDS
    if missing:
        errors.append(f"{location}: missing fields: {sorted(missing)}")
    if extra:
        errors.append(f"{location}: unexpected fields: {sorted(extra)}")

    case_id = case.get("id")
    if not isinstance(case_id, str) or not case_id.strip():
        errors.append(f"{location}: id must be a non-empty string")
    if case.get("language") not in ALLOWED_LANGUAGES:
        errors.append(f"{location}: language must be one of {sorted(ALLOWED_LANGUAGES)}")
    for field in ("category", "topic"):
        if not isinstance(case.get(field), str) or not case[field].strip():
            errors.append(f"{location}: {field} must be a non-empty string")
    if not isinstance(case.get("no_analysis"), bool):
        errors.append(f"{location}: no_analysis must be boolean")

    artifacts = case.get("required_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"{location}: required_artifacts must be a non-empty list")
    else:
        invalid = set(artifacts) - ALLOWED_ARTIFACTS
        if invalid:
            errors.append(f"{location}: unsupported artifacts: {sorted(invalid)}")
        if "report" not in artifacts:
            errors.append(f"{location}: report must be required")
        if case.get("no_analysis") and "analysis" in artifacts:
            errors.append(f"{location}: no_analysis case cannot require analysis")
        if not case.get("no_analysis") and "analysis" not in artifacts:
            errors.append(f"{location}: analysis-enabled case must require analysis")

    sections = case.get("required_sections")
    if (
        not isinstance(sections, list)
        or not sections
        or not all(isinstance(item, str) and item.strip() for item in sections)
    ):
        errors.append(f"{location}: required_sections must contain non-empty strings")
    citations = case.get("minimum_citations")
    if not isinstance(citations, int) or isinstance(citations, bool) or citations < 1:
        errors.append(f"{location}: minimum_citations must be a positive integer")
    return errors


def validate_dataset(path: Path, expected_size: int | None = None) -> dict[str, Any]:
    cases = load_jsonl(path)
    errors: list[str] = []
    if expected_size is not None and len(cases) != expected_size:
        errors.append(f"{path}: expected {expected_size} cases, found {len(cases)}")

    ids: list[str] = []
    topics: list[str] = []
    for index, case in enumerate(cases, start=1):
        errors.extend(validate_case(case, f"{path}:{index}"))
        if isinstance(case.get("id"), str):
            ids.append(case["id"])
        if isinstance(case.get("topic"), str):
            topics.append(case["topic"].strip().casefold())

    duplicate_ids = sorted(key for key, value in Counter(ids).items() if value > 1)
    duplicate_topics = sorted(
        key for key, value in Counter(topics).items() if value > 1
    )
    if duplicate_ids:
        errors.append(f"{path}: duplicate ids: {duplicate_ids}")
    if duplicate_topics:
        errors.append(f"{path}: duplicate topics: {duplicate_topics}")

    return {
        "path": str(path),
        "case_count": len(cases),
        "sha256": sha256_file(path),
        "languages": dict(sorted(Counter(c.get("language") for c in cases).items())),
        "categories": dict(sorted(Counter(c.get("category") for c in cases).items())),
        "errors": errors,
    }


def validate_suite(dataset_dir: Path) -> dict[str, Any]:
    expected = {
        "research_smoke_v1.jsonl": 6,
        "research_main_v1.jsonl": 30,
    }
    datasets = [
        validate_dataset(dataset_dir / filename, size)
        for filename, size in expected.items()
    ]
    errors = [error for dataset in datasets for error in dataset["errors"]]

    smoke = load_jsonl(dataset_dir / "research_smoke_v1.jsonl")
    main = load_jsonl(dataset_dir / "research_main_v1.jsonl")
    smoke_topics = {case["topic"].strip().casefold() for case in smoke}
    main_topics = {case["topic"].strip().casefold() for case in main}
    overlap = sorted(smoke_topics & main_topics)
    if overlap:
        errors.append(f"smoke/main topics overlap: {overlap}")

    return {"valid": not errors, "datasets": datasets, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Deep Research eval datasets")
    parser.add_argument(
        "--dataset-dir", type=Path, default=Path("evals/datasets")
    )
    args = parser.parse_args()
    result = validate_suite(args.dataset_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
