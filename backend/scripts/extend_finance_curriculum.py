"""Add the draft six-stage finance curriculum to the existing V1 content pack.

Existing imported records are retained at their original content version. New
records are authored as drafts and cite the FINXL pages that support their topic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PACK = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "assessment-content"
    / "v1"
    / "finxl_assessment_content_v1.json"
)
PACK_VERSION = "1.1.0"
FMER = "Financial Modeling & Equity Reasearch (FM&ER).pdf"
FSR = "Financial Statements & Ratios.pdf"
SCALE = [
    {"score": score, "label": label}
    for score, label in enumerate(
        ("No assessable evidence", "Limited", "Developing", "Competent", "Strong")
    )
]

# Each row is a newly authored stem, expected concepts, follow-up, difficulty,
# category, source document, PDF pages, and the source topic being aligned.
STAGES: dict[str, dict[str, Any]] = {
    "soft_1": {
        "title": "Finance Foundations and Communication",
        "description": "Explain basic finance terms clearly using simple language and examples.",
        "competency": (
            "FIN_FOUNDATIONS_COMM",
            "Finance Foundations and Explanation",
            "Explain foundational financial concepts accurately in accessible language.",
        ),
        "pages": (FSR, [1, 2, 3, 5, 8]),
        "dimensions": [
            (
                "conceptual_accuracy",
                "0.40",
                "Defines the concept accurately",
                "Distinguishes related terms correctly",
            ),
            ("purpose_and_use", "0.25", "Explains why the concept matters to a business"),
            (
                "example_and_clarity",
                "0.35",
                "Uses a relevant simple example",
                "Explains without relying on unexplained jargon",
            ),
        ],
        "questions": [
            (
                "What is financial modeling, and how can a simple model help a business plan?",
                ["structured representation", "assumptions", "forecast or decision support"],
                "What is one input and one output a basic model might contain?",
                "basic",
                "conceptual",
                FSR,
                [1],
            ),
            (
                "What does a balance sheet tell you about a business at a particular point in time?",  # noqa: E501
                ["financial position", "assets", "liabilities and equity", "point in time"],
                "Can you give one example of an asset and one liability?",
                "basic",
                "conceptual",
                FSR,
                [3, 4, 5],
            ),
            (
                "What does an income statement show, and how does it help explain business performance?",  # noqa: E501
                ["performance over a period", "revenue", "expenses", "profit or loss"],
                "How would you explain the income statement to a new business owner?",
                "basic",
                "conceptual",
                FSR,
                [2],
            ),
            (
                "What does a cash flow statement explain? Name its main activity groups in simple terms.",  # noqa: E501
                ["cash movements over a period", "operating", "investing", "financing"],
                "Give a simple example of a cash inflow from one of those activities.",
                "basic",
                "conceptual",
                FSR,
                [5, 6, 7, 8],
            ),
            (
                "Explain assets, liabilities, and equity using a simple business example.",
                [
                    "resources controlled",
                    "obligations",
                    "residual ownership",
                    "assets equal liabilities plus equity",
                ],
                "If a business borrows cash, which of these categories change?",
                "basic",
                "communication",
                FSR,
                [4, 5],
            ),
            (
                "What is the difference between revenue and profit? Use a small example.",
                [
                    "revenue from sales",
                    "expenses deducted",
                    "profit is not revenue",
                    "simple numerical example",
                ],
                "If sales are 100 and expenses are 80, what is profit before any other items?",
                "basic",
                "communication",
                FSR,
                [1, 2],
            ),
            (
                "What is working capital, and why does a business monitor it?",
                [
                    "current assets less current liabilities",
                    "short-term operating needs",
                    "receivables inventory payables",
                ],
                "How could too much inventory affect working capital?",
                "basic",
                "conceptual",
                FSR,
                [8],
            ),
            (
                "Why is cash flow management important even when a business reports a profit?",
                [
                    "cash timing differs from accrual profit",
                    "pay obligations on time",
                    "working capital or investment needs",
                    "example",
                ],
                "Give an example of a profitable sale that has not yet brought in cash.",
                "basic",
                "communication",
                FSR,
                [5, 8, 14, 15],
            ),
        ],
    },
    "soft_2": {
        "title": "Conceptual Understanding and Financial Reasoning",
        "description": "Interpret basic ratios and connect profitability, liquidity, solvency, efficiency, and cash flow.",  # noqa: E501
        "competency": (
            "FIN_CONCEPTUAL_REASONING",
            "Financial Concepts and Reasoning",
            "Interpret financial concepts in context and explain relationships among measures.",
        ),
        "pages": (FSR, [9, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24]),
        "dimensions": [
            (
                "interpretation",
                "0.40",
                "Explains what a ratio or statement relationship indicates",
                "Avoids treating a ratio as a conclusion by itself",
            ),
            (
                "financial_reasoning",
                "0.35",
                "Connects cause and effect across measures",
                "Uses relevant evidence to explain the result",
            ),
            ("contextual_judgment", "0.25", "Recognizes industry, trend, or composition context"),
        ],
        "questions": [
            (
                "A current ratio rises while profit margins fall. What might this combination mean?",  # noqa: E501
                [
                    "liquidity measure",
                    "profitability measure",
                    "composition and trend matter",
                    "investigate current assets and margins",
                ],
                "What additional information would help distinguish a healthy change from a warning sign?",  # noqa: E501
                "intermediate",
                "scenario_based",
                FSR,
                [18, 25],
            ),
            (
                "How would you explain the difference between liquidity and solvency to a business owner?",  # noqa: E501
                [
                    "near-term obligations",
                    "long-term ability to meet obligations",
                    "cash versus capital structure",
                    "clear example",
                ],
                "Which kind of problem could a company have if one is strong but the other is weak?",  # noqa: E501
                "basic",
                "communication",
                FSR,
                [18, 19, 20],
            ),
            (
                "A company has a higher quick ratio than last year but lower profitability. How would you interpret that?",  # noqa: E501
                [
                    "inventory excluded from quick assets",
                    "liquidity and profit differ",
                    "investigate cash receivables margins",
                    "avoid one-ratio conclusion",
                ],
                "What could cause liquidity to improve while profitability weakens?",
                "intermediate",
                "scenario_based",
                FSR,
                [18, 22, 25],
            ),
            (
                "What can debt-to-equity and interest coverage tell you together about financial risk?",  # noqa: E501
                [
                    "leverage",
                    "interest-paying capacity",
                    "debt purpose and operating performance",
                    "interpret together",
                ],
                "What trend would make you more concerned about the debt position?",
                "intermediate",
                "analytical",
                FSR,
                [19, 23, 26],
            ),
            (
                "If receivables grow faster than sales, what might receivables turnover or collection days help you investigate?",  # noqa: E501
                [
                    "collection speed",
                    "credit terms and aging",
                    "cash conversion",
                    "customer concentration or provisions",
                ],
                "What evidence would you check before recommending a tighter credit policy?",
                "intermediate",
                "analytical",
                FSR,
                [19, 27],
            ),
            (
                "How can a company report positive profit but have negative operating cash flow?",
                [
                    "accrual accounting",
                    "receivables or inventory increase",
                    "payables decrease",
                    "noncash items and reconciliation",
                ],
                "Which working-capital movements would you check first?",
                "intermediate",
                "scenario_based",
                FSR,
                [9, 15],
            ),
            (
                "Why should a financial ratio be compared with prior periods or similar companies?",
                [
                    "trend",
                    "industry differences",
                    "accounting or business mix",
                    "ratio alone lacks context",
                ],
                "What could make a peer comparison misleading?",
                "basic",
                "analytical",
                FSR,
                [16, 17, 20],
            ),
            (
                "How do net income, retained earnings, and cash flow connect across the three statements?",  # noqa: E501
                [
                    "net income on income statement",
                    "retained earnings roll forward",
                    "cash flow reconciliation",
                    "ending cash links to balance sheet",
                ],
                "Why might the change in retained earnings differ from the change in cash?",
                "intermediate",
                "conceptual",
                FSR,
                [9, 13, 14],
            ),
        ],
    },
    "soft_3": {
        "title": "Practical Finance Scenarios and Problem-Solving",
        "description": "Diagnose practical business finance issues and explain justified recommendations to stakeholders.",  # noqa: E501
        "competency": (
            "FIN_SCENARIO_RECOMMENDATION",
            "Practical Finance Problem Solving",
            "Identify financial drivers, assess evidence, and communicate practical recommendations.",  # noqa: E501
        ),
        "pages": (FSR, [14, 15, 16, 25, 26, 27]),
        "dimensions": [
            (
                "problem_identification",
                "0.30",
                "Identifies the stated financial issue",
                "Separates symptoms from possible causes",
            ),
            (
                "analysis_and_evidence",
                "0.35",
                "Selects relevant financial evidence",
                "Explains plausible cause and effect",
            ),
            ("recommendation", "0.20", "Recommends an actionable response tied to evidence"),
            (
                "stakeholder_communication",
                "0.15",
                "Explains the recommendation clearly for its audience",
            ),
        ],
        "questions": [
            (
                "A company's revenue is growing but cash is falling. What would you investigate and recommend first?",  # noqa: E501
                [
                    "receivables and collection",
                    "inventory and working capital",
                    "capital expenditure or debt flows",
                    "recommend action and monitor cash",
                ],
                "How would you explain your first recommendation to a non-finance manager?",
                "intermediate",
                "scenario_based",
                FSR,
                [14],
            ),
            (
                "A company reports profit but has negative operating cash flow. How would you explain possible causes to its owner?",  # noqa: E501
                [
                    "accrual profit",
                    "receivables inventory payables",
                    "noncash adjustments",
                    "distinguish temporary from recurring",
                ],
                "What two figures or trends would you ask to see next?",
                "intermediate",
                "scenario_based",
                FSR,
                [15],
            ),
            (
                "Operating expenses are rising faster than revenue. How would you analyze the issue before proposing a cost action?",  # noqa: E501
                [
                    "expense categories",
                    "fixed versus variable or one-off",
                    "margin and volume trends",
                    "avoid unsupported across-the-board cuts",
                ],
                "How would you check whether a proposed cost reduction could harm revenue?",
                "intermediate",
                "scenario_based",
                FSR,
                [2, 17],
            ),
            (
                "Inventory has grown much faster than sales. What risks and checks would you present to management?",  # noqa: E501
                [
                    "inventory turnover or days",
                    "slow-moving stock and product mix",
                    "demand and seasonality",
                    "cash tied up",
                ],
                "Suggest one action and one measure to track its effect.",
                "intermediate",
                "scenario_based",
                FSR,
                [15, 19],
            ),
            (
                "A company is struggling to pay suppliers despite reporting healthy sales. How would you investigate its working capital?",  # noqa: E501
                ["receivables", "inventory", "payables and terms", "cash conversion cycle"],
                "Which action might improve cash timing without damaging supplier relationships?",
                "intermediate",
                "scenario_based",
                FSR,
                [8, 24],
            ),
            (
                "Debt has increased and interest costs are reducing profit. What would you analyze before recommending a response?",  # noqa: E501
                [
                    "purpose and maturity of debt",
                    "interest coverage and cash flow",
                    "rates and operating returns",
                    "trade-offs of repayment or refinancing",
                ],
                "How would your recommendation change if the borrowing funded productive expansion?",  # noqa: E501
                "intermediate",
                "scenario_based",
                FSR,
                [19, 23, 26],
            ),
            (
                "Profit margin is falling while sales are stable. How would you identify likely drivers and explain your findings?",  # noqa: E501
                [
                    "gross margin and cost of sales",
                    "operating expense trends",
                    "pricing volume and mix",
                    "evidence-led recommendation",
                ],
                "What would you tell a stakeholder if the data does not yet identify one clear cause?",  # noqa: E501
                "intermediate",
                "analytical",
                FSR,
                [2, 17, 25],
            ),
            (
                "A manager asks whether to expand while cash is tight. What financial information and trade-offs would you explain?",  # noqa: E501
                [
                    "forecast cash needs",
                    "working capital and capital spending",
                    "expected returns and downside",
                    "clear recommendation with uncertainty",
                ],
                "How would you summarize the decision in two sentences for a non-finance audience?",
                "intermediate",
                "communication",
                FMER,
                [9],
            ),
        ],
    },
    "technical_1": {
        "title": "Financial Modeling Fundamentals",
        "description": "Structure a basic model from historical information, assumptions, drivers, and forecast outputs.",  # noqa: E501
        "competency": (
            "FIN_MODEL_FUNDAMENTALS",
            "Financial Modeling Fundamentals",
            "Organize historical financial data and transparent assumptions into an auditable forecast.",  # noqa: E501
        ),
        "pages": (FMER, [6, 9]),
        "dimensions": [
            (
                "model_structure",
                "0.30",
                "Separates inputs, calculations, and outputs",
                "Maintains a clear period and statement layout",
            ),
            (
                "forecasting_fundamentals",
                "0.35",
                "Links revenue or cost forecasts to business drivers",
                "Uses historical information appropriately",
            ),
            (
                "assumptions_and_hygiene",
                "0.35",
                "Identifies and labels assumptions",
                "Explains checks and auditability",
            ),
        ],
        "questions": [
            (
                "Describe a clear layout for a basic financial model and explain how inputs differ from outputs.",  # noqa: E501
                [
                    "historical actuals",
                    "assumptions and calculations",
                    "forecast outputs",
                    "labels and checks",
                ],
                "How would you make a changed assumption easy for another analyst to find?",
                "basic",
                "practical",
                FMER,
                [6],
            ),
            (
                "What historical information would you gather before forecasting a company's revenue and expenses?",  # noqa: E501
                [
                    "income statement history",
                    "business drivers and periods",
                    "consistent definitions",
                    "validate missing or unusual data",
                ],
                "How would you handle a missing historical month?",
                "basic",
                "practical",
                FMER,
                [6],
            ),
            (
                "A business sells 1,000 units at 50 each. Explain a simple way to forecast next period revenue if volume is expected to grow 5% and price is unchanged.",  # noqa: E501
                [
                    "revenue equals units times price",
                    "volume driver",
                    "5% growth assumption",
                    "forecast 52,500",
                ],
                "Which assumption would you change to model a price increase separately?",
                "basic",
                "practical",
                FMER,
                [6],
            ),
            (
                "How could you forecast operating expenses using historical data and a business driver?",  # noqa: E501
                [
                    "historical baseline",
                    "percentage of revenue or cost driver",
                    "explicit assumption",
                    "check reasonableness",
                ],
                "When might a percentage-of-revenue assumption be unsuitable?",
                "basic",
                "practical",
                FMER,
                [6, 9],
            ),
            (
                "Explain how an assumption change should flow through a model to its outputs.",
                ["input cell", "linked calculations", "outputs update", "traceable formulas"],
                "What check could reveal a broken formula link?",
                "basic",
                "conceptual",
                FMER,
                [6],
            ),
            (
                "How would you organize historical actuals and forecast periods so a reviewer can distinguish them?",  # noqa: E501
                [
                    "consistent periods",
                    "actual versus forecast labels",
                    "source references",
                    "consistent formatting and units",
                ],
                "What would you document when a historical figure is restated?",
                "basic",
                "practical",
                FMER,
                [6],
            ),
            (
                "A revenue forecast uses customer growth and average spend. How do these drivers combine to produce a projection?",  # noqa: E501
                [
                    "customers multiplied by spend",
                    "driver assumptions",
                    "period alignment",
                    "sanity check against history",
                ],
                "How might you explain a forecast increase if customer count rises but spend falls?",  # noqa: E501
                "intermediate",
                "analytical",
                FMER,
                [6, 9],
            ),
            (
                "What basic checks would you add to make a spreadsheet forecast easier to audit?",
                [
                    "formula consistency",
                    "balance or reconciliation checks",
                    "assumption labels",
                    "source and units",
                ],
                "What would you do if a check fails rather than hiding it?",
                "basic",
                "practical",
                FMER,
                [6],
            ),
        ],
    },
    "technical_2": {
        "title": "Financial Statements and Ratio Analysis",
        "description": "Interpret statements and calculate or compare supported financial ratios in context.",  # noqa: E501
        "competency": (
            "FIN_STATEMENT_RATIO_ANALYSIS",
            "Financial Statement and Ratio Analysis",
            "Interpret statement items and use ratio, trend, and comparative evidence accurately.",
        ),
        "pages": (FSR, [1, 2, 5, 8, 9, 16, 17, 18, 19, 20, 22, 23, 24]),
        "dimensions": [
            (
                "calculation_accuracy",
                "0.30",
                "Uses the appropriate stated inputs and formula",
                "Calculates accurately with units or periods",
            ),
            (
                "financial_interpretation",
                "0.40",
                "Explains financial meaning",
                "Connects measures to business condition",
            ),
            (
                "comparative_context",
                "0.30",
                "Uses trends or relevant comparisons",
                "Recognizes limits and composition effects",
            ),
        ],
        "questions": [
            (
                "Current assets are 240 and current liabilities are 160. Calculate the current ratio and explain what it can and cannot tell you.",  # noqa: E501
                [
                    "240 divided by 160",
                    "1.5 times",
                    "short-term coverage indicator",
                    "composition and timing limits",
                ],
                "What additional detail would help assess the quality of current assets?",
                "basic",
                "practical",
                FSR,
                [18],
            ),
            (
                "Quick assets are 150 and current liabilities are 100. Calculate the quick ratio and compare its meaning with the current ratio.",  # noqa: E501
                [
                    "quick ratio equals 1.5",
                    "excludes inventory and often prepaids",
                    "liquidity without inventory",
                    "industry and timing context",
                ],
                "Why could two companies with the same current ratio have different quick ratios?",
                "basic",
                "practical",
                FSR,
                [18, 22],
            ),
            (
                "Revenue is 500 and EBIT is 50. Calculate operating margin and explain what a fall in this margin might signal.",  # noqa: E501
                [
                    "EBIT divided by revenue",
                    "10 percent",
                    "operating profitability",
                    "price cost or mix investigation",
                ],
                "Which statement lines would you compare to investigate the decline?",
                "basic",
                "practical",
                FSR,
                [2, 17],
            ),
            (
                "A company has debt of 300 and equity of 200. Calculate debt-to-equity and explain why the result needs context.",  # noqa: E501
                [
                    "300 divided by 200",
                    "1.5 times",
                    "leverage",
                    "industry debt purpose coverage and trend",
                ],
                "Which cash-flow measure could help assess debt service capacity?",
                "basic",
                "practical",
                FSR,
                [19, 23],
            ),
            (
                "How would you interpret a decline in inventory turnover over several periods?",
                [
                    "COGS over average inventory",
                    "slower movement or more inventory",
                    "product mix and demand",
                    "compare with seasonality and peers",
                ],
                "What operational detail could distinguish deliberate stocking from obsolete inventory?",  # noqa: E501
                "intermediate",
                "analytical",
                FSR,
                [19, 24],
            ),
            (
                "Compare gross margin and net margin. What different parts of company performance do they reveal?",  # noqa: E501
                [
                    "gross profit over revenue",
                    "net profit over revenue",
                    "production costs versus all expenses and financing/tax",
                    "trend context",
                ],
                "If gross margin is stable but net margin falls, where would you investigate?",
                "intermediate",
                "conceptual",
                FSR,
                [2, 17],
            ),
            (
                "How would you compare a company's liquidity and profitability trends with a competitor fairly?",  # noqa: E501
                [
                    "consistent definitions and periods",
                    "industry and business mix",
                    "ratio trends",
                    "accounting differences and one-off items",
                ],
                "What limitation would you include in your comparison?",
                "intermediate",
                "analytical",
                FSR,
                [16, 17, 20],
            ),
            (
                "Trace how net income and a change in receivables can affect the income statement, balance sheet, and operating cash flow.",  # noqa: E501
                [
                    "net income on income statement",
                    "retained earnings",
                    "receivables on balance sheet",
                    "receivable increase reduces indirect operating cash flow",
                ],
                "Why can cash collections lag reported revenue?",
                "intermediate",
                "analytical",
                FSR,
                [8, 9, 14, 15],
            ),
        ],
    },
    "technical_3": {
        "title": "Financial Modeling Applications",
        "description": "Apply linked forecasts, scenarios, variance analysis, and supported valuation concepts to decisions.",  # noqa: E501
        "competency": (
            "FIN_MODEL_APPLICATIONS",
            "Financial Modeling Applications and Judgment",
            "Interpret integrated financial forecasts, test assumptions, and justify decisions under uncertainty.",  # noqa: E501
        ),
        "pages": (FMER, [7, 9]),
        "dimensions": [
            (
                "model_integration",
                "0.30",
                "Links forecast drivers to financial statement outputs",
                "Explains relevant statement and cash effects",
            ),
            (
                "scenario_and_variance",
                "0.30",
                "Tests assumptions or explains variances",
                "Identifies key sensitivities and limitations",
            ),
            ("financial_judgment", "0.25", "Weighs risks and trade-offs", "Avoids false precision"),
            (
                "recommendation_justification",
                "0.15",
                "Connects recommendation to model evidence",
                "States conditions or monitoring needs",
            ),
        ],
        "questions": [
            (
                "How would you build a base case and downside case for a business whose sales depend on customer volume and average price?",  # noqa: E501
                [
                    "define drivers",
                    "vary volume and price assumptions",
                    "flow through revenue and costs",
                    "compare cash and profit outcomes",
                ],
                "Which assumption might matter most, and how would you test that?",
                "intermediate",
                "practical",
                FMER,
                [9],
            ),
            (
                "A forecast shows higher profit but lower cash. Explain how an integrated model could help identify why.",  # noqa: E501
                [
                    "income statement profit",
                    "working capital movements",
                    "capital expenditure and financing",
                    "cash flow reconciliation",
                ],
                "Which balance-sheet schedules would you inspect first?",
                "intermediate",
                "analytical",
                FSR,
                [8, 9, 14, 15],
            ),
            (
                "Actual operating costs are 12% above forecast. Describe a variance analysis that could support a decision.",  # noqa: E501
                [
                    "compare actual to forecast",
                    "volume price mix or rate drivers",
                    "one-off versus recurring",
                    "action and forecast update",
                ],
                "How would you avoid treating a volume-driven variance as a unit-cost problem?",
                "intermediate",
                "practical",
                FMER,
                [9],
            ),
            (
                "Which assumptions would you sensitize when evaluating a capital spending decision, and how would you communicate uncertainty?",  # noqa: E501
                [
                    "investment amount and timing",
                    "volume cost or utilization",
                    "cash flow and return outcomes",
                    "range not point certainty",
                ],
                "How could a decision maker use the downside case?",
                "intermediate",
                "analytical",
                FMER,
                [9],
            ),
            (
                "How can a model represent a change in customer demand through revenue, costs, working capital, and cash?",  # noqa: E501
                [
                    "revenue drivers",
                    "variable and fixed costs",
                    "receivables or inventory",
                    "cash flow implications",
                ],
                "Which relationship would you check to confirm the model remains internally consistent?",  # noqa: E501
                "intermediate",
                "practical",
                FMER,
                [6, 9],
            ),
            (
                "A management forecast depends on an optimistic growth assumption. How would you challenge and govern that assumption?",  # noqa: E501
                [
                    "source evidence",
                    "historical and external reasonableness",
                    "owner and approval",
                    "sensitivity and documented override",
                ],
                "What would you report if evidence supports a wide range rather than one value?",
                "intermediate",
                "analytical",
                FMER,
                [6, 9],
            ),
            (
                "FINXL covers discounted cash flow and comparable analysis. What assumptions would you explain before presenting a valuation conclusion?",  # noqa: E501
                [
                    "forecast cash flows",
                    "discount rate and terminal assumptions for DCF",
                    "peer selection and comparability for comps",
                    "valuation range and risks",
                ],
                "Why might two supported methods produce different values?",
                "intermediate",
                "conceptual",
                FMER,
                [7],
            ),
            (
                "A model's forecast differs materially from actual performance. How would you decide whether to revise assumptions or investigate model design?",  # noqa: E501
                [
                    "variance drivers",
                    "data and formula checks",
                    "structural versus assumption error",
                    "document changes and decision implications",
                ],
                "What evidence would justify changing a key assumption?",
                "intermediate",
                "analytical",
                FMER,
                [6, 9],
            ),
        ],
    },
}


def source_ref(document: str, pages: list[int], status: str) -> dict[str, Any]:
    return {
        "source_document": document,
        "pdf_pages": pages,
        "section_or_module": "Topic support; newly authored assessment stem",
        "original_question_number_or_heading": None,
        "source_status": status,
        "review_notes": (
            "The cited pages support the topic only; this question wording is newly authored "
            "from the requested curriculum and is not claimed as source wording. Verify during "
            "FINXL subject-matter review."
        ),
    }


def indicators(dimensions: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {"score": score, "label": label, "evidence_description": description}
        for score, label, description in [
            (0, "No evidence", "No relevant answer evidence."),
            (1, "Limited", "Materially inaccurate or fragmentary evidence."),
            (2, "Developing", "Partly correct evidence with important omissions."),
            (3, "Competent", "Correct, relevant evidence with minor omissions."),
            (4, "Strong", "Accurate, concise evidence with sound reasoning and context."),
        ]
    ]


def extend_pack(content: dict[str, Any]) -> dict[str, Any]:
    if content.get("pack_version") != "1.0.0":
        raise ValueError("Expected the unmodified V1 assessment content pack")
    content["base_pack_version"] = "1.0.0"
    content["pack_version"] = PACK_VERSION
    content["governance"]["production_approved"] = False
    content["governance"]["approval_status"] = "draft"
    existing_ids = {item["question_id"] for item in content["questions"]}
    if any(item.startswith("Q_CURR_FIN_11_") for item in existing_ids):
        return content

    for stage_id, stage_data in STAGES.items():
        stage = next(row for row in content["stages"] if row["stage_id"] == stage_id)
        competency_id, competency_title, definition = stage_data["competency"]
        rubric_id = f"R_{competency_id}_V1_1"
        stage["proposed_display_title"] = stage_data["title"]
        stage["learning_objectives"] = [definition]
        stage["difficulty_coverage"] = sorted({row[3] for row in stage_data["questions"]})
        stage["question_ids"] = [
            *stage["question_ids"],
            *(f"Q_CURR_FIN_11_{stage_id}_{index:02d}" for index in range(1, 9)),
        ]
        stage["mapping_rationale"] = (
            "Draft alignment to the six-stage finance curriculum. Newly authored questions "
            "are mapped to the cited source topics; stage mapping and rubric require FINXL review."
        )
        stage["source_status"] = "inferred_draft"
        stage["source_references"] = [
            source_ref(stage_data["pages"][0], stage_data["pages"][1], "inferred_draft")
        ]
        stage["competency_ids"] = [*stage["competency_ids"], competency_id]

        content["competencies"].append(
            {
                "competency_id": competency_id,
                "name": competency_title,
                "description": definition,
                "learning_objectives": [definition],
                "stage_ids": [stage_id],
                "curriculum_module_ids": [],
                "relevant_topics": [row[0] for row in stage_data["questions"]],
                "expected_knowledge_or_capability": [definition],
                "source_references": [
                    source_ref(stage_data["pages"][0], stage_data["pages"][1], "inferred_draft")
                ],
                "source_status": "inferred_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "review_notes": "New competency proposed for the user-provided stage curriculum; review definitions and coverage before approval.",  # noqa: E501
                "content_version": PACK_VERSION,
            }
        )
        rubric_dimensions = [
            {
                "key": dim[0],
                "weight": dim[1],
                "performance_indicators": list(dim[2:]),
            }
            for dim in stage_data["dimensions"]
        ]
        content["rubrics"].append(
            {
                "rubric_id": rubric_id,
                "rubric_version_id": rubric_id,
                "competency_id": competency_id,
                "applicable_question_ids": [
                    f"Q_CURR_FIN_11_{stage_id}_{i:02d}" for i in range(1, 9)
                ],
                "dimensions": rubric_dimensions,
                "performance_levels": indicators([]),
                "scoring_scale": SCALE,
                "evidence_requirements": [
                    "Assess relevant evidence and reasoning; answer length is not a scoring criterion."  # noqa: E501
                ],
                "insufficient_evidence_criteria": [
                    "The response contains no assessable evidence for the linked question."
                ],
                "source_status": "inferred_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "source_references": [
                    source_ref(stage_data["pages"][0], stage_data["pages"][1], "inferred_draft")
                ],
                "review_notes": "Proposed stage-specific observable criteria and weights; FINXL review required.",  # noqa: E501
                "content_version": PACK_VERSION,
            }
        )

        document, default_pages = stage_data["pages"]
        for index, row in enumerate(stage_data["questions"], start=1):
            stem, concepts, followup, difficulty, category, item_doc, pages = row
            question_id = f"Q_CURR_FIN_11_{stage_id}_{index:02d}"
            evidence_id = f"E_{question_id}"
            evidence = {
                "evidence_id": evidence_id,
                "question_id": question_id,
                "competency_id": competency_id,
                "essential_concepts": concepts,
                "supporting_explanation": "A concise explanation that connects the stated concepts to the business question.",  # noqa: E501
                "application_or_reasoning": "Use the scenario, formula, or example in the question to show observable reasoning.",  # noqa: E501
                "examples_or_calculations": [],
                "incomplete_or_missing_evidence": [
                    "A memorized label or formula without relevant interpretation or explanation."
                ],
                "source_status": "inferred_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "source_references": [
                    source_ref(item_doc, pages or default_pages, "inferred_draft")
                ],
            }
            question = {
                "question_id": question_id,
                "text": stem,
                "competency_id": competency_id,
                "stage_id": stage_id,
                "curriculum_module_ids": [],
                "source_topic_ids": [],
                "difficulty": difficulty,
                "question_category": category,
                "question_kind": "base",
                "expected_answer_evidence_id": evidence_id,
                "rubric_id": rubric_id,
                "key_concepts_expected": concepts,
                "common_incomplete_answer_indicators": [
                    "Repeats a definition without applying or interpreting it."
                ],
                "source_references": [
                    source_ref(item_doc, pages or default_pages, "inferred_draft")
                ],
                "source_status": "inferred_draft",
                "review_status": "pending_finxl_review",
                "approval_status": "draft",
                "review_notes": "Newly authored stem. Topic references support the subject only; they do not claim source wording.",  # noqa: E501
                "content_version": PACK_VERSION,
            }
            follow_up = {
                "follow_up_id": f"FU_{question_id}_01",
                "parent_question_id": question_id,
                "stage_id": stage_id,
                "competency_id": competency_id,
                "text": followup,
                "intended_evidence_gap": "Clarify or extend evidence relevant to the original question while remaining within its stage and competency.",  # noqa: E501
                "source_references": [
                    source_ref(item_doc, pages or default_pages, "inferred_draft")
                ],
                "source_status": "inferred_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "review_notes": "Newly authored follow-up tied to its parent question; verify relevance and expected evidence.",  # noqa: E501
                "content_version": PACK_VERSION,
            }
            content["expected_answer_evidence"].append(evidence)
            content["questions"].append(question)
            content["follow_up_candidates"].append(follow_up)
    content["curriculum_alignment_version"] = PACK_VERSION
    return content


def main() -> None:
    content = json.loads(PACK.read_text(encoding="utf-8"))
    updated = extend_pack(content)
    PACK.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Draft curriculum content updated in {PACK}")


if __name__ == "__main__":
    main()
