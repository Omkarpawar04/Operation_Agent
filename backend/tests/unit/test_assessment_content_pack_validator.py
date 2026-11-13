from __future__ import annotations

import copy
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_assessment_content import validate_content  # noqa: E402

PACK_PATH = Path(__file__).resolve().parents[3] / "docs" / "assessment-content" / "v1"
JSON_PATH = PACK_PATH / "finxl_assessment_content_v1.json"
WORKBOOK_PATH = PACK_PATH / "FINXL_Assessment_Content_V1.xlsx"


@pytest.fixture
def pack() -> dict[str, object]:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


def test_generated_pack_passes_validation_and_remains_draft(pack: dict[str, object]) -> None:
    assert validate_content(pack) == []
    assert pack["governance"]["production_approved"] is False
    assert all(item["approval_status"] == "draft" for item in pack["questions"])


def test_validator_rejects_duplicate_question_ids(pack: dict[str, object]) -> None:
    invalid = copy.deepcopy(pack)
    invalid["questions"].append(copy.deepcopy(invalid["questions"][0]))
    assert any("duplicate question_id" in issue for issue in validate_content(invalid))


def test_validator_rejects_invalid_stage_and_competency_mapping(pack: dict[str, object]) -> None:
    invalid = copy.deepcopy(pack)
    invalid["questions"][0]["stage_id"] = "technical_9"
    issues = validate_content(invalid)
    assert any("invalid stage" in issue for issue in issues)
    assert any("stage is not mapped to competency" in issue for issue in issues)


def test_validator_rejects_invalid_rubric_weights(pack: dict[str, object]) -> None:
    invalid = copy.deepcopy(pack)
    invalid["rubrics"][0]["dimensions"][0]["weight"] = "0.95"
    issues = validate_content(invalid)
    assert any("weights total" in issue for issue in issues)


def test_validator_rejects_cross_competency_followup(pack: dict[str, object]) -> None:
    invalid = copy.deepcopy(pack)
    invalid["follow_up_candidates"][0]["competency_id"] = "C_VALUATION"
    assert any("crosses parent competency or stage" in issue for issue in validate_content(invalid))


def test_validator_rejects_missing_source_traceability(pack: dict[str, object]) -> None:
    invalid = copy.deepcopy(pack)
    invalid["questions"][0]["source_references"] = []
    assert any("missing source traceability" in issue for issue in validate_content(invalid))


def test_validator_rejects_approved_generated_content(pack: dict[str, object]) -> None:
    invalid = copy.deepcopy(pack)
    invalid["questions"][0]["approval_status"] = "approved"
    assert any("must not be approved" in issue for issue in validate_content(invalid))


def _cell_text(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "s":
        return shared_strings[int(cell.findtext("{*}v", "0"))]
    inline = cell.find("{*}is/{*}t")
    return inline.text if inline is not None and inline.text else cell.findtext("{*}v", "")


def test_workbook_has_all_expected_sheets_and_required_headers() -> None:
    assert WORKBOOK_PATH.is_file()
    expected = {
        "Source Documents": {"Source ID", "File Name", "PDF Pages", "Source Status"},
        "Curriculum Modules": {"Module ID", "Module Title", "Curriculum Topics"},
        "Curriculum Topics": {
            "Topic ID",
            "Topic Source Type",
            "Module / Source Group",
            "Topic (source wording)",
        },
        "Stage Mapping": {
            "Stage ID",
            "Proposed Display Title",
            "Competency IDs",
            "Curriculum Module IDs",
        },
        "Competencies": {"Competency ID", "Name", "Stage IDs", "Source References"},
        "Question Bank": {
            "Question ID",
            "Exact Question Wording",
            "Competency ID",
            "Stage ID",
            "Difficulty",
            "Question Category",
        },
        "Expected Answer Evidence": {
            "Evidence ID",
            "Question ID",
            "Essential Concepts",
            "Application / Reasoning",
        },
        "Evaluation Rubrics": {
            "Rubric ID",
            "Competency ID",
            "Dimensions / Weights / Indicators",
            "Performance Levels (0-4)",
        },
        "Follow-up Candidates": {
            "Follow-up ID",
            "Parent Question ID",
            "Competency ID",
            "Exact Candidate Wording",
        },
        "Coverage and Gaps": {"Record Type", "Area / Stage", "Coverage Finding / Detail"},
        "Review and Approval Register": {
            "Review Item ID",
            "Item Type",
            "Item ID",
            "Review Status",
            "Decision",
        },
    }
    namespace = {
        "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "p": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(WORKBOOK_PATH) as archive:
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            item.attrib["Id"]: (
                item.attrib["Target"].lstrip("/")
                if item.attrib["Target"].lstrip("/").startswith("xl/")
                else "xl/" + item.attrib["Target"].lstrip("/")
            )
            for item in relationships
        }
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = ["".join(node.itertext()) for node in root.findall("m:si", namespace)]
        sheets = {
            sheet.attrib["name"]: targets[sheet.attrib[f"{{{namespace['r']}}}id"]]
            for sheet in workbook.findall("m:sheets/m:sheet", namespace)
        }
        assert set(sheets) == set(expected)
        pack = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        expected_data_rows = {
            "Source Documents": len(pack["source_documents"]),
            "Curriculum Modules": len(pack["curriculum_modules"]),
            "Curriculum Topics": len(pack["curriculum_topics"])
            + len(pack["supplemental_source_topics"]),
            "Stage Mapping": len(pack["stages"]),
            "Competencies": len(pack["competencies"]),
            "Question Bank": len(pack["questions"]),
            "Expected Answer Evidence": len(pack["expected_answer_evidence"]),
            "Evaluation Rubrics": len(pack["rubrics"]),
            "Follow-up Candidates": len(pack["follow_up_candidates"]),
            "Review and Approval Register": len(pack["review_approval_register"]),
        }
        for name, required_headers in expected.items():
            sheet_xml = ElementTree.fromstring(archive.read(sheets[name]))
            header_row = sheet_xml.find("m:sheetData/m:row[@r='1']", namespace)
            assert header_row is not None, name
            values = {
                _cell_text(cell, shared_strings) for cell in header_row.findall("m:c", namespace)
            }
            assert required_headers <= values, name
            if name in expected_data_rows:
                rows = sheet_xml.findall("m:sheetData/m:row", namespace)
                assert len(rows) == expected_data_rows[name] + 1, name
