"""Offline contract and decision fixtures for outreach.alumni_resource_lists."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "workflow_packages/outreach.alumni_resource_lists"
PROMPT = (PACKAGE / "PROMPT.md").read_text(encoding="utf-8")
SKILL = (PACKAGE / "skills/alumni-resource-lists/SKILL.md").read_text(encoding="utf-8")


# Representative public evidence for a founder whose product helps junior designers
# collect and present user research. This is a procedure input fixture, not web data.
USEFUL_INPUT = {
    "focus": "Northbridge University human-computer interaction program",
    "candidates": [
        {
            "id": "hci-kit",
            "title": "HCI resources I wish I had as a first-year researcher",
            "audience_evidence": "The page says it is for incoming HCI students.",
            "author_standing": "Author's public bio says Northbridge HCI alum, 2024 cohort.",
            "published": "2026-03-12",
            "public_evidence": "Original public page opens without login; indexed canonical URL.",
            "product_use_fit": "Includes a field-research toolkit for student interview projects.",
            "reach_evidence": "Public page shows 34 substantive comments.",
        },
        {
            "id": "design-hub",
            "title": "Northbridge Design Society: starter resources",
            "audience_evidence": "Maintained page labels the section 'new designers'.",
            "author_standing": "Current society mentor is named on the public university staff page.",
            "published": "2025-11-01",
            "public_evidence": "Original university page opens publicly and is indexed.",
            "product_use_fit": "Includes a general research planning spreadsheet.",
            "reach_evidence": "Listed on the actively maintained society resource hub.",
        },
        {
            "id": "grad-guide",
            "title": "Tools for new UX graduates",
            "audience_evidence": "Public page says it is for new UX graduates.",
            "author_standing": "Author's public profile says Northbridge alum and UX mentor.",
            "published": "2026-01-20",
            "public_evidence": "Original article opens publicly and is indexed.",
            "product_use_fit": "Lists a related portfolio review service, not research tools.",
            "reach_evidence": "No interaction count is shown.",
        },
    ],
}

EXPECTED_RANKED_OUTPUT = [
    {"id": "hci-kit", "scores": {"audience": 3, "product_use": 3, "currentness": 2, "reach": 2, "standing": 2}, "total": 12},
    {"id": "design-hub", "scores": {"audience": 3, "product_use": 2, "currentness": 2, "reach": 2, "standing": 2}, "total": 11},
    {"id": "grad-guide", "scores": {"audience": 2, "product_use": 1, "currentness": 2, "reach": 1, "standing": 2}, "total": 8},
]

ALL_REJECTED_INPUT = {
    "focus": "Northbridge University",
    "candidates": [
        {"id": "private-crop", "publication_date": "2026-06-01", "public_evidence": "Screenshot of a closed alumni Slack post; original cannot be opened."},
        {"id": "old-doc", "publication_date": "2022-01-10", "public_evidence": "Public original, but no current-year maintenance note; last substantive update is over 30 months old."},
    ],
}

PLAUSIBLE_BUT_UNUSABLE_RESULT = {
    "status": "ranked",
    "candidates": [
        {
            "id": "private-crop",
            "rank": 1,
            "score": 14,
            "reach_evidence": "Author has 80,000 followers.",
            "note": "Hi, I saw this and thought you might add our product.",
        },
        {
            "id": "old-doc",
            "rank": 2,
            "score": 11,
            "reach_evidence": "Likely popular with students.",
            "note": "Thanks for helping students. Please include our product.",
        },
    ],
}


def test_manifest_matches_package_contract_and_bounds_every_string():
    manifest = json.loads((PACKAGE / "workflow.json").read_text(encoding="utf-8"))
    definition = manifest["definition"]
    schema = definition["input_schema"]
    assert definition["key"] == PACKAGE.name
    assert definition["executor"] == "codex.procedure"
    assert definition["schedule_modes"] == ["on_demand"]
    assert schema["required"] == ["project_id"]
    assert schema["properties"]["focus"]["maxLength"] == 2000
    assert all(prop.get("maxLength") for prop in schema["properties"].values() if prop["type"] == "string")
    assert definition["procedure"]["entry_skill"] == "alumni-resource-lists"
    assert definition["procedure"]["skill_files"] == ["skills/alumni-resource-lists/SKILL.md"]
    assert definition["procedure"]["sandbox"] == {
        "profile": "isolated",
        "egress": "fenced",
        "timeout_seconds": 900,
    }


def test_prompt_keeps_the_exact_research_only_boundary():
    boundary = (
        "Never contact, comment on, or edit anyone's post or document. Never touch anything behind a private group, DM, paywall, or login. "
        "Only consider content that is publicly posted and indexable by a normal search. If a candidate list turns out to be private or ambiguous, skip it rather than guess."
    )
    assert boundary in PROMPT
    assert "founder sends any note themselves" in PROMPT


def test_useful_input_has_the_expected_relevance_then_reach_order():
    ids = {candidate["id"] for candidate in USEFUL_INPUT["candidates"]}
    assert [row["id"] for row in EXPECTED_RANKED_OUTPUT] == ["hci-kit", "design-hub", "grad-guide"]
    assert {row["id"] for row in EXPECTED_RANKED_OUTPUT} == ids
    for row in EXPECTED_RANKED_OUTPUT:
        assert row["total"] == sum(row["scores"].values())
    assert "Rank by total score, then audience and product-use fit combined, then observable reach" in SKILL


def test_private_or_stale_only_input_returns_no_ranked_candidates():
    reasons = {
        candidate["id"]: (
            "private_or_ambiguous" if "Screenshot" in candidate["public_evidence"] else "stale"
        )
        for candidate in ALL_REJECTED_INPUT["candidates"]
    }
    assert reasons == {"private-crop": "private_or_ambiguous", "old-doc": "stale"}
    assert "no verified public lists" in SKILL
    assert "older than 30 months" in SKILL


def test_plausible_but_unusable_procedure_result_is_rejected_by_the_method():
    result = PLAUSIBLE_BUT_UNUSABLE_RESULT
    assert result["status"] == "ranked"  # It looks complete at a glance.
    assert any(
        "Screenshot" in candidate["public_evidence"]
        for candidate in ALL_REJECTED_INPUT["candidates"]
        if candidate["id"] == result["candidates"][0]["id"]
    )
    assert "Likely popular" in result["candidates"][1]["reach_evidence"]
    assert "do not award points for unsupported claims" in SKILL
    # Both entries fail a hard gate, so a ranked output containing either is unusable.
    assert {candidate["id"] for candidate in result["candidates"]} & {
        candidate["id"] for candidate in ALL_REJECTED_INPUT["candidates"]
    }
