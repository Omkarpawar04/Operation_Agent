"""Build the review-only FINXL V1 content pack from the supplied PDFs.

This script extracts question stems and answer text from the source PDF and
combines them with explicitly labeled draft taxonomy, mappings, rubrics, and
follow-ups. It never writes to application tables or approves content.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "docs" / "source-material"
OUTPUT_DIR = ROOT / "docs" / "assessment-content" / "v1"
FMER_NAME = "Financial Modeling & Equity Reasearch (FM&ER).pdf"
FSR_NAME = "Financial Statements & Ratios.pdf"
STATUSES = ("source_derived", "source_based_draft", "inferred_draft", "needs_finxl_review")


def ref(document: str, pages: list[int], section: str, note: str = "") -> dict[str, Any]:
    return {
        "source_document": document,
        "pdf_pages": pages,
        "section_or_module": section,
        "original_question_number_or_heading": None,
        "source_status": "source_derived",
        "review_notes": note
        or "Confirm the cited page and interpretation during FINXL content review.",
    }


def refs_for_pages(pages: list[int], section: str, note: str = "") -> list[dict[str, Any]]:
    """Keep page citations attached to the PDF whose physical page range contains them."""
    references = []
    brochure_pages = sorted({page for page in pages if 1 <= page <= 12})
    qa_pages = sorted({page for page in pages if 13 <= page <= 27})
    if brochure_pages:
        references.append(ref(FMER_NAME, brochure_pages, section, note))
    if qa_pages:
        references.append(ref(FSR_NAME, qa_pages, section, note))
    return references


MODULES = [
    (
        "M1",
        "MS Excel Expert",
        6,
        [
            "Excel Essentials & key board shortcuts",
            "Basic & advance excel functions",
            "Conditional Formatting",
            "Paste Special",
            "VLOOKUP",
            "HLOOKUP",
            "Match Index",
            "SUMIF",
            "COUNTIF",
            "AND",
            "AVERAGEIF",
            "DATEDIF",
            "YEAR",
            "YEARFRACE",
            "MONTH",
            "Index",
            "Search",
            "Choose",
            "offset",
            "Sensitivity analysis with Data tables",
            "Pivot table",
            "Charting commonly used",
            "Dashboards",
            "templates",
            "Macros",
        ],
    ),
    (
        "M2",
        "Data Collection and Modeling",
        6,
        [
            "Authentic sources of financial data for companies based in the United States, India, China, Germany, and many more",
            "Tricks to collect data in shortest time",
            "Data collection & Data structuring for model",
            "Understanding of Financial Reports & its types",
            "10-K",
            "10-Q",
            "8-K",
            "20-F",
            "Create Model template for 5 years historical data",
            "Revenue Drivers",
            "Cost Drivers",
            "Income statement",
            "Balance sheet",
            "Cash flow statement",
            "Dividend schedule",
            "Asset Schedule",
            "Debt Schedule",
            "Equity Schedule",
        ],
    ),
    (
        "M3",
        "Finance Fundamentals",
        6,
        [
            "What Equity Research Analyst does?",
            "Skill set requires for Equity Research Analyst?",
            "Job roles of BUY SIDE and SELL SIDE Analysts",
            "Reading and Analyzing Income statement",
            "Balance sheet",
            "Cash flow statement",
            "Note to accounts",
            "GAAP & Non-GAAP",
            "Reported & Adjusted numbers",
            "Reported/Adjusted/GAAP/Non-GAAP EPS",
            "Restructuring & Adjusted numbers",
            "Pro-forma Income statement",
            "Restating financials for valuation and analysis",
            "Minority/Non-controlling",
            "Associates",
            "Subsidiary",
            "Convertible debt/securities",
            "Corporate actions and their treatments",
            "Rights issue",
            "Bonus issue",
            "Takeover",
            "Merger",
            "Acquisitions",
            "Interim/Annual dividend",
            "Stock splits",
            "Spin-offs",
            "Reverse split",
            "10 case studies on live companies",
            "Make business plan of startups",
            "Company's Business model understanding",
            "Economies/Sectors/Industries understanding",
            "Operational drivers & cost drivers & Projection",
        ],
    ),
    (
        "M4",
        "Sector/Industry Research",
        6,
        [
            "Analyzing Sectors/Industries/Companies",
            "Company's Business model understanding",
            "Economies/Sectors/Industries understanding",
            "Operational drivers & cost drivers & Projection",
            "Factors that impact the company's projections & valuations",
            "Case studies on 'Top Down' and 'Bottom Up' approaches",
            "Forecasting of IS, BS, CFS, and Schedules",
        ],
    ),
    (
        "M5",
        "Financial Modeling & Valuations",
        6,
        [
            "Interlinking of financial statements (IS, BS, CFS)",
            "Tallying the balance sheet in 30 minutes",
            "Best practices in Financial Model Building",
            "Forecasting basis for each line of IS, BS & CFS",
            "Debt Repayment Schedule (DRS)",
            "Fixed Assets Module (FAM)",
            "Dividend & Equity Schedule (ES)",
            "Liquidity ratios",
            "Leverage ratios",
            "Efficiency ratios",
            "Profitability ratios",
            "Market value ratios",
            "Calculation and analysis of ratios",
            "Compare company's ratios with competitors",
            "DuPont analysis",
            "Discounted Cash Flow (DCF)",
            "Business/economic life cycle concepts",
            "Time value of money concepts",
            "FCFF & FCFE",
            "Cost of capital (WACC)",
            "CAPM",
            "Cost of Debt",
            "Cost of preference shares",
            "Market Premium (Rm)",
            "Risk-Free rate of return (Rf)",
            "Levered beta & Un-levered beta",
            "Calculate beta using the last 5 years price",
            "Sensitivity analysis",
            "Net present value/company value",
            "Relative Valuation (Trading Comps/Exit Multiple)",
            "Criteria to choose competitors",
            "Criteria to choose Ratios for comparison",
            "P/E",
            "P/S",
            "EV/EBITDA",
            "P/B",
            "Price band and valuation conclusion",
            "Sum of the Parts Analysis (SOTP)",
            "DDM (Dividend Discount Model)/Gordon Growth Model",
        ],
    ),
    (
        "M6",
        "Equity Research Report",
        7,
        [
            "Introduction of various reports",
            "Initiating Coverage",
            "Company Update",
            "Scenario Road map",
            "Sector/Industry Reports",
            "Detailed equity research reports",
            "Short reports",
            "Economy, Industry, and sector research and analysis",
            "Analyst call BUY, SELL, NEUTRAL",
        ],
    ),
    (
        "M7",
        "Real Case Studies, Mock Interviews, Soft Skills Training",
        8,
        [
            "10+ real-time case studies",
            "100+ frequently asked Equity Research Interview questions with answers",
            "Positive attitude and emotional intelligence training",
            "Communication and interpersonal skills training",
            "Regular mock interviews",
            "Individual strengths and weaknesses",
            "Prepare an interview script",
            "Profile building and marketing",
            "Interview scheduling and placements",
        ],
    ),
]

COMPETENCIES: list[dict[str, Any]] = [
    (
        "C_SOFT_COMM",
        "Structured Interview Communication",
        "Explain a response clearly, organize supporting points, and communicate findings for an interview or presentation.",
        ["Present a structured explanation", "Support conclusions with relevant points"],
        ["soft_1"],
        ["M7", "M6"],
        [
            "Communication and interpersonal skills training",
            "Prepare an interview script",
            "Reports and presentations",
        ],
        "inferred_draft",
        [6, 7, 8],
    ),
    (
        "C_SOFT_REASON",
        "Structured Financial Problem-Solving",
        "Investigate a financial or business scenario using relevant statements, drivers, and evidence before reaching a conclusion.",
        ["Identify plausible drivers", "Select relevant evidence", "Explain a reasoned conclusion"],
        ["soft_2"],
        ["M3", "M4", "M5", "M7"],
        ["Case studies", "Operational drivers", "Scenario analysis"],
        "inferred_draft",
        [6, 7, 9],
    ),
    (
        "C_SOFT_RECOMMEND",
        "Research Presentation and Recommendation",
        "Synthesize company, industry, and valuation analysis into a clearly communicated research conclusion.",
        ["Explain a research view", "Connect analysis to a conclusion"],
        ["soft_3"],
        ["M4", "M6", "M7"],
        [
            "Initiating Coverage",
            "Company Update",
            "BUY, SELL, NEUTRAL",
            "Communication and interpersonal skills training",
        ],
        "inferred_draft",
        [7, 8],
    ),
    (
        "C_EXCEL",
        "Excel Modeling Tools",
        "Use the named Excel functions and features in the curriculum to organize, analyze, and present model data.",
        ["Select a relevant function or tool", "Explain a practical modeling use"],
        ["technical_3"],
        ["M1"],
        ["VLOOKUP", "INDEX", "MATCH", "Data tables", "Pivot table", "Macros"],
        "inferred_draft",
        [6],
    ),
    (
        "C_DATA",
        "Financial Data Collection and Structuring",
        "Identify source materials and organize historical financial information for model use.",
        ["Identify filings and financial reports", "Organize historical data and schedules"],
        ["technical_3"],
        ["M2"],
        ["10-K", "10-Q", "8-K", "20-F", "5 years historical data"],
        "inferred_draft",
        [6],
    ),
    (
        "C_FINANCE",
        "Finance Fundamentals and Reporting",
        "Explain the equity research role, financial reporting terminology, earnings measures, corporate actions, and business context listed in the curriculum.",
        ["Explain a named finance concept", "Distinguish the stated reporting concepts"],
        ["technical_1", "technical_2"],
        ["M3"],
        ["Buy-side and sell-side", "GAAP and Non-GAAP", "EPS", "Corporate actions"],
        "inferred_draft",
        [6],
    ),
    (
        "C_STATEMENTS",
        "Financial Statements and Accounting Relationships",
        "Interpret the income statement, balance sheet, and cash flow statement and explain relationships among their items.",
        ["Explain statement purpose and structure", "Trace a stated item across statements"],
        ["technical_1"],
        ["M2", "M3", "M5"],
        ["Income statement", "Balance sheet", "Cash flow statement", "Interlinking"],
        "source_based_draft",
        [6, 9],
    ),
    (
        "C_WORKING_CAPITAL",
        "Working Capital and Cash Flow Analysis",
        "Use working capital movements and cash flow evidence to explain differences between reported performance and cash movement.",
        ["Relate operating balances to cash", "Investigate cash conversion evidence"],
        ["technical_1", "soft_2"],
        ["M2", "M3", "M4", "M5"],
        ["Receivables", "Inventory", "Payables", "Cash flow"],
        "source_based_draft",
        [6, 14, 15, 16],
    ),
    (
        "C_RATIOS",
        "Financial Ratio Analysis",
        "Calculate or interpret liquidity, profitability, efficiency, leverage, solvency, and market value ratios and explain limitations or context.",
        ["Explain ratio meaning and formula", "Interpret ratio changes in context"],
        ["technical_2", "soft_2"],
        ["M5"],
        ["Liquidity", "Leverage", "Efficiency", "Profitability", "Market value", "DuPont"],
        "source_based_draft",
        [7, 16, 20, 27],
    ),
    (
        "C_VALUATION",
        "Valuation Methods and Cost of Capital",
        "Explain or apply the valuation methods and cost-of-capital topics explicitly listed by FINXL.",
        ["Describe a named valuation approach", "Relate assumptions to a valuation conclusion"],
        ["technical_2", "technical_3"],
        ["M5"],
        ["DCF", "FCFF", "FCFE", "WACC", "Trading comps", "SOTP", "DDM"],
        "source_based_draft",
        [7],
    ),
    (
        "C_FORECAST",
        "Financial Forecasting and Business Drivers",
        "Connect business, industry, operational, and cost drivers to financial projections and schedules.",
        ["Identify relevant drivers", "Explain forecast links to statements and schedules"],
        ["technical_3", "soft_3"],
        ["M2", "M3", "M4", "M5"],
        ["Revenue drivers", "Cost drivers", "Forecasting IS, BS, CFS and schedules"],
        "source_based_draft",
        [6],
    ),
    (
        "C_MODEL",
        "Integrated Financial Modeling",
        "Organize historical data, assumptions, statements, and supporting schedules into an integrated financial model.",
        ["Explain model structure", "Describe statement and schedule links"],
        ["technical_3"],
        ["M1", "M2", "M5"],
        [
            "5 years historical data",
            "Interlinking statements",
            "Debt schedule",
            "Fixed assets module",
        ],
        "source_based_draft",
        [6],
    ),
    (
        "C_RESEARCH",
        "Equity, Sector, and Industry Research",
        "Analyze companies, sectors, industries, economic context, and business models using the research approaches named in the curriculum.",
        [
            "Describe a top-down or bottom-up approach",
            "Connect industry context to company drivers",
        ],
        ["soft_3", "technical_2"],
        ["M3", "M4", "M6"],
        ["Company analysis", "Sector/industry reports", "Top Down", "Bottom Up"],
        "inferred_draft",
        [6, 7],
    ),
    (
        "C_REPORT",
        "Equity Research Reporting",
        "Structure a research report, company update, or scenario roadmap and communicate an analyst call with supporting analysis.",
        ["Present a research report structure", "Support a stated analyst call"],
        ["soft_3"],
        ["M6"],
        ["Initiating Coverage", "Company Update", "BUY, SELL, NEUTRAL"],
        "inferred_draft",
        [7],
    ),
    (
        "C_CORPACTIONS",
        "Corporate Actions and Consolidation Topics",
        "Explain the named corporate actions and ownership concepts listed in the finance fundamentals curriculum.",
        [
            "Identify the named action or ownership concept",
            "Describe its stated treatment or analysis context",
        ],
        ["technical_1", "technical_3"],
        ["M3"],
        [
            "Rights issue",
            "Merger",
            "Acquisitions",
            "Minority/Non-controlling",
            "Associates",
            "Subsidiary",
        ],
        "inferred_draft",
        [6],
    ),
    (
        "C_TRANSACTION",
        "Transaction and Business Case Analysis",
        "Analyze transaction, expansion, divestment, or strategic scenarios within the explicit scope of the supplied materials.",
        ["Identify relevant scenario variables", "Compare alternatives and their modeled impact"],
        ["soft_2", "technical_3"],
        ["M3", "M5"],
        ["Acquisitions", "Mergers", "Precedent Transactions", "Carve-out", "Synergy"],
        "inferred_draft",
        [6, 7, 9],
    ),
]

EXTRA_QUESTIONS = [
    (
        "Q_DRAFT_SOFT1_01",
        "Describe how you would organize an explanation of a financial analysis so a listener can follow your reasoning and conclusion.",
        "C_SOFT_COMM",
        "soft_1",
        "basic",
        "communication",
        [
            "Organizes the explanation into clear points",
            "Connects supporting information to a conclusion",
        ],
        ["Communication and interpersonal skills training", "Interview script"],
        [8],
        "M7",
        "Adds an assessable communication prompt; the brochure names training but supplies no original soft-skill questions.",
    ),
    (
        "Q_DRAFT_SOFT1_02",
        "When presenting a company analysis, how would you explain the evidence behind your conclusion and respond to a request for clarification?",
        "C_SOFT_COMM",
        "soft_1",
        "intermediate",
        "communication",
        [
            "States a conclusion and the evidence supporting it",
            "Clarifies the explanation when asked",
        ],
        ["Company analysis", "Communication and interpersonal skills training"],
        [6, 8],
        "M3/M7",
        "Draft prompt grounded in company analysis and communication training; no source question is claimed.",
    ),
    (
        "Q_DRAFT_SOFT2_01",
        "Revenue has increased while cash has declined. Which financial statement items and business drivers would you examine first, and why?",
        "C_SOFT_REASON",
        "soft_2",
        "intermediate",
        "scenario_based",
        [
            "Selects relevant working capital, investment, financing, and operating evidence",
            "Explains how the evidence would distinguish possible causes",
        ],
        ["Cash flow", "Operational drivers", "Scenario analysis"],
        [6, 9],
        "M3/M4/M7",
        "Source-based scenario prompt that extends the source Q&A scenario to probe prioritization; newly drafted.",
    ),
    (
        "Q_DRAFT_SOFT3_01",
        "How would you connect company, sector, and industry analysis to a research conclusion such as BUY, SELL, or NEUTRAL?",
        "C_SOFT_RECOMMEND",
        "soft_3",
        "advanced",
        "communication",
        [
            "Connects company, sector, and industry analysis",
            "Explains how analysis supports the stated call",
        ],
        ["Sector/Industry Reports", "BUY, SELL, NEUTRAL"],
        [7],
        "M4/M6",
        "Adds an integrative presentation prompt; no original question is claimed.",
    ),
    (
        "Q_DRAFT_WC_01",
        "How would you use receivables, inventory, and payables information to explain a change in operating working capital or cash flow?",
        "C_WORKING_CAPITAL",
        "soft_2",
        "intermediate",
        "scenario_based",
        [
            "Identifies receivables, inventory, and payables as operating items",
            "Explains how their movement can affect working capital or cash flow",
        ],
        ["Operating working capital", "Receivables", "Inventory", "Payables"],
        [6, 8],
        "M2/M3",
        "Adds a focused working-capital prompt because source topics and Q&A evidence are present but not isolated in an original question.",
    ),
    (
        "Q_DRAFT_EXCEL_01",
        "For a five-year historical financial model template, how might you use lookup, conditional, and summary functions named in the curriculum to organize or analyze data?",
        "C_EXCEL",
        "technical_3",
        "intermediate",
        "practical",
        [
            "Selects functions from the curriculum appropriate to the described task",
            "Explains how the output supports model organization or analysis",
        ],
        ["VLOOKUP/HLOOKUP", "SUMIF/COUNTIF", "Historical model template"],
        [6],
        "M1/M2",
        "Adds a practical prompt because the brochure lists Excel tools but contains no extracted Excel interview question.",
    ),
    (
        "Q_DRAFT_DATA_01",
        "You are preparing five years of historical company data for a model. Which source filings and financial schedules listed in the curriculum would you collect and structure?",
        "C_DATA",
        "technical_3",
        "intermediate",
        "practical",
        [
            "Names relevant filing types from the curriculum",
            "Organizes historical statement and schedule data for model use",
        ],
        ["10-K", "10-Q", "8-K", "20-F", "Revenue/Cost drivers", "Statements and schedules"],
        [6],
        "M2",
        "Adds coverage for data collection and structuring, which the companion Q&A does not test directly.",
    ),
    (
        "Q_DRAFT_FINANCE_01",
        "How does the course distinguish reported and adjusted numbers or GAAP and non-GAAP EPS, and what would you check when analyzing the difference?",
        "C_FINANCE",
        "technical_1",
        "intermediate",
        "analytical",
        [
            "Distinguishes the named reporting measures",
            "Identifies adjustments or source notes to examine without assuming a specific adjustment",
        ],
        ["GAAP and Non-GAAP", "Reported and Adjusted numbers", "EPS"],
        [6],
        "M3",
        "Draft based on named topics; no source answer defines a complete checklist.",
    ),
    (
        "Q_DRAFT_ACTION_01",
        "Choose one corporate action listed in the course and explain what information you would review to understand its treatment in company financial analysis.",
        "C_CORPACTIONS",
        "technical_1",
        "intermediate",
        "conceptual",
        [
            "Selects a corporate action from the listed curriculum",
            "Explains a relevant treatment or analysis consideration, with uncertainties identified",
        ],
        ["Rights issue", "Merger", "Acquisition", "Dividend", "Stock split"],
        [6],
        "M3",
        "Broad question because the brochure lists actions but does not provide their treatments.",
    ),
    (
        "Q_DRAFT_RESEARCH_01",
        "Compare the top-down and bottom-up approaches named in the course. How could either approach help connect industry conditions to a company's projections?",
        "C_RESEARCH",
        "technical_2",
        "intermediate",
        "analytical",
        [
            "Distinguishes the two named approaches",
            "Relates industry or company analysis to projections",
        ],
        ["Top Down", "Bottom Up", "Company projections"],
        [6],
        "M4",
        "Course lists both approaches and projection analysis but does not define a formal comparison answer.",
    ),
    (
        "Q_DRAFT_FORECAST_01",
        "How would you identify business, operational, or cost drivers to support forecasts for the income statement, balance sheet, cash flow statement, and schedules?",
        "C_FORECAST",
        "technical_3",
        "advanced",
        "analytical",
        [
            "Identifies drivers from the described company or industry context",
            "Connects forecast assumptions to statements and schedules",
        ],
        ["Business model", "Operational and cost drivers", "Forecasting IS, BS, CFS and schedules"],
        [6],
        "M3/M4/M5",
        "Adds integrated coverage for driver-based forecasting named across modules.",
    ),
    (
        "Q_DRAFT_MODEL_01",
        "Describe how you would check that an integrated financial model links the three statements and balances, using the schedules named in the course.",
        "C_MODEL",
        "technical_3",
        "advanced",
        "practical",
        [
            "Explains links among income statement, balance sheet, and cash flow statement",
            "References supporting debt, fixed asset, dividend, or equity schedules",
        ],
        ["Interlinking statements", "Balance sheet reconciliation", "DRS", "FAM", "ES"],
        [6],
        "M5",
        "Adds model integration coverage; brochure states these learning areas but does not provide an assessment question.",
    ),
    (
        "Q_DRAFT_VALUATION_01",
        "At a high level, how would you organize a DCF analysis using the course's stated cash flow, discount-rate, and sensitivity topics?",
        "C_VALUATION",
        "technical_2",
        "advanced",
        "analytical",
        [
            "References FCFF or FCFE, cost of capital, and net present value/company value",
            "Explains that assumptions can be tested through sensitivity analysis",
        ],
        ["DCF", "FCFF and FCFE", "WACC", "Sensitivity analysis"],
        [7],
        "M5",
        "Draft question from explicitly listed DCF topics; no formula or unsupported valuation convention is imposed.",
    ),
    (
        "Q_DRAFT_VALUATION_02",
        "How would you select competitors and comparison ratios for a trading-comps analysis, then communicate the resulting valuation conclusion?",
        "C_VALUATION",
        "technical_2",
        "advanced",
        "analytical",
        [
            "Explains competitor and ratio selection",
            "Connects stated multiples to a price band or valuation conclusion",
        ],
        ["Trading comps", "Competitor criteria", "P/E", "P/S", "EV/EBITDA", "P/B"],
        [7],
        "M5",
        "Adds practical coverage for explicitly listed relative valuation topics.",
    ),
    (
        "Q_DRAFT_REPORT_01",
        "What sections or analyses would you bring together for an initiating coverage report, and how would you support its BUY, SELL, or NEUTRAL conclusion?",
        "C_REPORT",
        "soft_3",
        "advanced",
        "communication",
        [
            "References report or coverage components listed in the curriculum",
            "Connects valuation and sector/industry analysis to an analyst call",
        ],
        [
            "Initiating Coverage",
            "Company Update",
            "Sector/Industry Reports",
            "Valuation conclusion",
        ],
        [7],
        "M5/M6",
        "Integrative report prompt based on listed report types and conclusions; not a source question.",
    ),
    (
        "Q_DRAFT_TRANSACTION_01",
        "A business is considering an acquisition, divestment, or carve-out. What scenario and model impacts would you organize before comparing alternatives?",
        "C_TRANSACTION",
        "technical_3",
        "advanced",
        "scenario_based",
        [
            "Identifies alternatives and relevant scenario variables",
            "Explains how a model can compare impacts",
        ],
        ["Acquisitions/disposals", "Carve-out planning", "Scenario analysis", "Synergy planning"],
        [9],
        "M3/M5",
        "Uses transaction topics explicitly named in the brochure; does not assert LBO coverage.",
    ),
    (
        "Q_DRAFT_EXCEL_02",
        "How could a data table, pivot table, or chart help you review model sensitivities or summarize financial data?",
        "C_EXCEL",
        "technical_3",
        "basic",
        "practical",
        ["Chooses a listed Excel feature", "Explains a relevant analysis or presentation use"],
        ["Data tables", "Pivot table", "Charting"],
        [6],
        "M1",
        "Adds application coverage for named Excel features; not an original FINXL interview question.",
    ),
]

FOLLOW_UP_TEXTS = {
    "Q_SRC_FSR_001": "Which statement would you consult first to answer a stakeholder's question, and why?",
    "Q_SRC_FSR_002": "Which model assumption would you vary first to understand funding needs or valuation impact?",
    "Q_SRC_FSR_003": "Which subtotal would best isolate operating performance, and which items below it can change net profit?",
    "Q_SRC_FSR_004": "Pick one current and one non-current item; what would each tell you about position at the reporting date?",
    "Q_SRC_FSR_005": "How would you tell whether cash was generated from operations, investing activity, or financing?",
    "Q_SRC_FSR_006": "Which operating current asset or liability movement would you check first to explain a cash change?",
    "Q_SRC_FSR_007": "How does a two-account transaction keep the Balance Sheet equation in balance?",
    "Q_SRC_FSR_008": "If Accounts Receivable rises while revenue is recognized, trace its effect through cash flow and ending cash.",
    "Q_SRC_FSR_009": "How would straight-line and declining-balance methods differ in their expense pattern over time?",
    "Q_SRC_FSR_010": "Trace a cash-funded machinery purchase from investing cash flow to PPE and subsequent depreciation.",
    "Q_SRC_FSR_011": "Which expense bridges the EBITDA and EBIT amounts in the source example?",
    "Q_SRC_FSR_012": "How can potential shares from a convertible instrument affect diluted EPS, and what anti-dilutive caveat applies?",
    "Q_SRC_FSR_013": "Choose one listed Balance Sheet item and explain its associated movement in cash, equity, or liabilities.",
    "Q_SRC_FSR_014": "Which change in receivables versus CapEx or debt repayment would you inspect to explain the cash decline?",
    "Q_SRC_FSR_015": "How would you reconcile net income to operating cash flow using receivables, inventory, and payables?",
    "Q_SRC_FSR_016": "Which turnover or inventory-age evidence would help distinguish future demand preparation from slow-moving stock?",
    "Q_SRC_FSR_017": "Which comparison period, competitor, or industry benchmark would make a ratio more interpretable?",
    "Q_SRC_FSR_018": "Which risk might you investigate if a ratio trend moved opposite to the operating result?",
    "Q_SRC_FSR_019": "Which margin or return ratio best answers the question, and what does its denominator tell you?",
    "Q_SRC_FSR_020": "How would a rise in inventory affect the current ratio and quick ratio differently?",
    "Q_SRC_FSR_021": "Which average balance and activity measure are used in one efficiency ratio, and what movement does it reflect?",
    "Q_SRC_FSR_022": "Which debt-servicing measure would you pair with leverage, and why?",
    "Q_SRC_FSR_023": "Which market-value metric matches the investor question, and which denominator is used?",
    "Q_SRC_FSR_024": "How do debt, cash, preferred stock, and minority interest affect the enterprise-value bridge?",
    "Q_SRC_FSR_025": "How could debt financing make ROE differ from ROA even when net income is unchanged?",
    "Q_SRC_FSR_026": "Which definition will you use for invested capital or capital employed, and why does the source note matter?",
    "Q_SRC_FSR_027": "Which assets are excluded from quick assets under the source's description?",
    "Q_SRC_FSR_028": "Which maturity, interest-rate, and cash-flow details would alter a conclusion about leverage risk?",
    "Q_SRC_FSR_029": "What obligation does DSCR include that interest coverage does not?",
    "Q_SRC_FSR_030": "What distinct operating signals could receivables turnover and inventory turnover provide?",
    "Q_SRC_FSR_031": "Which of DIO, DSO, or DPO contributes most to a longer cash conversion cycle?",
    "Q_SRC_FSR_032": "Which current asset drove the ratio rise, and how would margins and turnover help assess its quality?",
    "Q_SRC_FSR_033": "How would you test whether new debt funded expansion or a cash shortfall, and whether returns justify it?",
    "Q_SRC_FSR_034": "How would you use DuPont analysis to separate margin, asset-turnover, and equity-multiplier effects on ROE?",
    "Q_SRC_FSR_035": "Which ageing and DSO measures could test whether credit terms or collections changed?",
    "Q_DRAFT_SOFT1_01": "Which supporting point would you lead with, and how does it help the listener follow your conclusion?",
    "Q_DRAFT_SOFT1_02": "What evidence would you clarify first if a listener questioned the conclusion?",
    "Q_DRAFT_SOFT2_01": "Which statement movement would you compare first to distinguish delayed collections from investment spending?",
    "Q_DRAFT_SOFT3_01": "Which analysis would most change the BUY, SELL, or NEUTRAL conclusion, and why?",
    "Q_DRAFT_WC_01": "Which of receivables, inventory, or payables changed, and how could that movement affect operating cash?",
    "Q_DRAFT_EXCEL_01": "Which named function would you choose for one specific task in that template, and what output would you check?",
    "Q_DRAFT_DATA_01": "How would you reconcile a historical figure across the filing and the model template before forecasting?",
    "Q_DRAFT_FINANCE_01": "Which source note would help you understand an adjustment without assuming it is recurring?",
    "Q_DRAFT_ACTION_01": "Which company statement or note would you review first to understand the selected action's treatment?",
    "Q_DRAFT_RESEARCH_01": "What company-level evidence would you use to test an industry conclusion reached top-down or bottom-up?",
    "Q_DRAFT_FORECAST_01": "Which driver assumption would you sensitize first, and which statement lines would reflect the change?",
    "Q_DRAFT_MODEL_01": "Which balance-sheet reconciliation or schedule link would you check first if the model did not balance?",
    "Q_DRAFT_VALUATION_01": "Which stated cash-flow or discount-rate assumption would have the greatest effect on the sensitivity?",
    "Q_DRAFT_VALUATION_02": "How would you explain the effect of a different peer set or comparison ratio on the price band?",
    "Q_DRAFT_REPORT_01": "Which evidence would you present first to connect sector analysis and valuation to the analyst call?",
    "Q_DRAFT_TRANSACTION_01": "Which scenario variable would you change first to compare the modeled alternatives?",
    "Q_DRAFT_EXCEL_02": "What feature output would you inspect to confirm that the summary or sensitivity is useful?",
}

SUPPLEMENTAL_TOPICS = [
    (
        "Statements and Modeling",
        1,
        "Financial statements: purpose, financial performance, financial position, cash generation/use, and stakeholder decisions",
    ),
    (
        "Statements and Modeling",
        1,
        "Financial modeling purpose: structured Excel model, performance representation, and future forecast",
    ),
    (
        "Statements and Modeling",
        1,
        "Modeling uses: forecasts, assumptions, valuation, investment/business decisions, scenarios, funding needs",
    ),
    ("Income Statement", 2, "Income Statement purpose and period presentation"),
    ("Income Statement", 2, "Revenue, COGS, gross profit, and operating expense structure"),
    (
        "Income Statement",
        2,
        "Selling, general, administrative, depreciation and amortization, and R&D expenses",
    ),
    (
        "Income Statement",
        2,
        "Operating profit, interest/dividend income, EBIT, interest paid, gains/losses, PBT, tax, PAT",
    ),
    (
        "Income Statement",
        2,
        "Preference dividends, non-controlling interest, and net profit attributable to equity shareholders",
    ),
    ("EPS", 3, "Basic EPS formula and weighted-average basic shares"),
    (
        "EPS",
        3,
        "Diluted EPS and potential shares from convertible securities and other dilutive instruments",
    ),
    ("Balance Sheet", 3, "Balance Sheet purpose and point-in-time presentation"),
    (
        "Balance Sheet",
        3,
        "Current assets: cash, receivables, inventories, finance receivables, securities, deferred tax assets, and other current assets",
    ),
    (
        "Balance Sheet",
        4,
        "Non-current assets: investments, fixed-maturity/equity securities, PP&E, goodwill, regulatory assets, intangibles, and other assets",
    ),
    (
        "Balance Sheet",
        4,
        "Current liabilities: payables, accrued expenses, deferred revenue, commercial paper, current debt, tax payable, leases",
    ),
    (
        "Balance Sheet",
        4,
        "Non-current liabilities: deferred revenue, long-term debt, leases, other liabilities, commitments, contingencies",
    ),
    (
        "Balance Sheet",
        5,
        "Shareholders' equity: common stock, capital in excess of par, retained earnings, AOCI, treasury stock, NCI",
    ),
    ("Balance Sheet", 5, "Accounting equation: assets equal liabilities plus shareholders' equity"),
    ("Cash Flow Statement", 5, "Cash Flow Statement purpose and cash movement during a period"),
    (
        "Cash Flow Statement",
        5,
        "Operating cash flow: net income, non-cash and other adjustments, restructuring/acquisition items, and working capital movements",
    ),
    (
        "Cash Flow Statement",
        6,
        "Operating cash flow changes in receivables, inventory, prepaid expenses, payables, tax payable, and other balances",
    ),
    (
        "Cash Flow Statement",
        6,
        "Investing cash flow: capital spending, PP&E sales, acquisitions, divestitures, investments, and other assets",
    ),
    (
        "Cash Flow Statement",
        7,
        "Financing cash flow: debt issuance/repayment, borrowing, dividends, share repurchases, options, and other financing",
    ),
    (
        "Cash Flow Statement",
        7,
        "Exchange-rate effects, net cash change, and beginning/ending cash reconciliation",
    ),
    ("Working Capital", 8, "Working capital formula: current assets less current liabilities"),
    (
        "Working Capital",
        8,
        "Operating working capital focus on receivables, inventory, and payables; cash and debt generally excluded",
    ),
    (
        "Accounting Equation",
        8,
        "Balance Sheet equation and example; each accounting transaction affects at least two accounts",
    ),
    (
        "Statement Links",
        9,
        "Net income flows to retained earnings and is the indirect-method operating cash flow starting point",
    ),
    ("Statement Links", 9, "Cash Flow Statement ending cash links to Balance Sheet cash"),
    (
        "Statement Links",
        9,
        "Changes in receivables, inventory, payables, debt, and fixed assets affect cash flow",
    ),
    (
        "Depreciation and CapEx",
        10,
        "Depreciation as systematic allocation of tangible fixed asset cost over useful life; non-cash expense",
    ),
    (
        "Depreciation and CapEx",
        10,
        "Straight-line depreciation formula and example using cost, salvage value, and useful life",
    ),
    (
        "Depreciation and CapEx",
        10,
        "Written Down Value / Declining Balance depreciation on carrying value",
    ),
    ("Depreciation and CapEx", 10, "CapEx, OpEx, and COGS definitions and examples"),
    (
        "Depreciation and CapEx",
        11,
        "CapEx capitalized as an asset; OpEx expensed in period; COGS direct production/purchase costs",
    ),
    (
        "Depreciation and CapEx",
        12,
        "Machinery purchase effects on PPE, cash, investing cash flow, and later depreciation",
    ),
    ("Earnings Measures", 12, "EBIT and EBITDA definitions and their stated relationship"),
    (
        "EPS",
        12,
        "EPS meaning and basic EPS formula net income less preference dividends divided by weighted-average shares",
    ),
    (
        "EPS",
        13,
        "Diluted EPS: options, convertible bonds, convertible preference shares, adjusted earnings/shares, anti-dilutive exclusion",
    ),
    (
        "Balance Sheet Items",
        13,
        "Treasury stock as repurchased own shares and deduction from equity",
    ),
    (
        "Balance Sheet Items",
        13,
        "Retained earnings roll-forward: opening retained earnings plus net income less dividends",
    ),
    (
        "Balance Sheet Items",
        14,
        "Deferred revenue/contract liability when cash is received before goods/services are delivered",
    ),
    ("Balance Sheet Items", 14, "Non-controlling interest ownership in a subsidiary"),
    (
        "Scenario Analysis",
        14,
        "Revenue growth with falling cash: receivables, inventory, CapEx, financing outflows, expenses, interest, taxes",
    ),
    (
        "Scenario Analysis",
        15,
        "Net profit with negative operating cash flow: accrual accounting and working capital reconciliation",
    ),
    (
        "Scenario Analysis",
        15,
        "Inventory growth versus sales: inventory turnover/days, product mix, slow-moving stock, production, demand, price, seasonality",
    ),
    (
        "Ratio Analysis",
        16,
        "Ratio analysis purpose, related financial figures, and uses in evaluating performance, position, and efficiency",
    ),
    (
        "Ratio Analysis",
        17,
        "Ratio analysis purposes: profitability, liquidity, efficiency, solvency, comparisons, decision support, and risk identification",
    ),
    ("Profitability Ratios", 17, "Gross profit margin: gross profit divided by revenue"),
    ("Profitability Ratios", 17, "Operating profit margin: EBIT divided by revenue"),
    ("Profitability Ratios", 17, "Net profit margin: net profit divided by revenue"),
    ("Profitability Ratios", 18, "ROA, ROE, and ROIC definitions/formulas as presented"),
    ("Liquidity Ratios", 18, "Current ratio: current assets divided by current liabilities"),
    (
        "Liquidity Ratios",
        18,
        "Quick ratio: quick assets divided by current liabilities; inventory excluded",
    ),
    (
        "Liquidity Ratios",
        18,
        "Cash ratio: cash and cash equivalents divided by current liabilities",
    ),
    ("Efficiency Ratios", 19, "Inventory turnover: COGS divided by average inventory"),
    (
        "Efficiency Ratios",
        19,
        "Receivables turnover: credit sales divided by average accounts receivable",
    ),
    ("Efficiency Ratios", 19, "Total asset turnover: revenue divided by average total assets"),
    (
        "Efficiency Ratios",
        19,
        "Working capital turnover: revenue divided by average working capital",
    ),
    ("Solvency Ratios", 19, "Debt-to-equity, debt ratio, interest coverage, and DSCR"),
    ("Solvency Ratios", 20, "Solvency ratio interpretation depends on ratio and industry"),
    (
        "Market Value Ratios",
        20,
        "P/E, P/B, EPS, dividend yield, and EV/EBITDA definitions/formulas",
    ),
    (
        "Enterprise Value",
        20,
        "Enterprise value formula including market capitalization, debt, preferred stock, minority interest, and cash",
    ),
    (
        "Returns and Capital",
        21,
        "ROA versus ROE and the effect of debt/liabilities on the equity denominator",
    ),
    (
        "Returns and Capital",
        21,
        "ROIC versus ROCE definitions, formulas, and variability in definitions",
    ),
    (
        "Liquidity Ratios",
        22,
        "Current ratio versus quick ratio, including inventory and prepaid-expense exclusion discussion",
    ),
    (
        "Solvency Ratios",
        23,
        "High debt-to-equity: leverage, interest obligations, risk, rate/performance sensitivity, and possible returns",
    ),
    (
        "Solvency Ratios",
        23,
        "Interest coverage versus DSCR; interest-only versus interest-plus-principal coverage",
    ),
    ("Efficiency Ratios", 24, "Receivables turnover versus inventory turnover and interpretation"),
    ("Efficiency Ratios", 24, "Cash Conversion Cycle components: DIO, DSO, DPO, and CCC formula"),
    (
        "Scenario Analysis",
        25,
        "Increasing current ratio with declining profitability: composition, working capital quality, margins, turnover, cash flow",
    ),
    (
        "Scenario Analysis",
        26,
        "Rising debt-to-equity: debt purpose, interest, coverage, maturities, rate type, operating returns",
    ),
    (
        "Scenario Analysis",
        26,
        "Strong profit margin with declining ROE; equity growth, asset turnover, leverage, and DuPont analysis",
    ),
    (
        "Scenario Analysis",
        27,
        "Declining receivables turnover with fast sales growth: DSO, credit policy, ageing, provisions, concentration, cash flow",
    ),
]


def read_questions(path: Path) -> list[dict[str, Any]]:
    reader = PdfReader(path)
    full_text = "\n".join(
        f"\n=== PDF PAGE {page_no} ===\n" + (page.extract_text() or "")
        for page_no, page in enumerate(reader.pages, start=1)
    )
    matches = list(re.finditer(r"(?m)^\s*Q\.\s*", full_text))
    result: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(full_text)
        segment = full_text[match.end() : end]
        answer_marker = re.search(r"\bAnswer:\s*", segment, flags=re.I)
        if answer_marker is not None:
            stem_text = segment[: answer_marker.start()]
        else:
            stem_match = re.search(r"(.*?\?)", segment, flags=re.S)
            if stem_match is None:
                continue
            stem_text = stem_match.group(1)
        stem = " ".join(stem_text.split())
        page_prefix = full_text[: match.start()]
        page_no = max(
            (int(value) for value in re.findall(r"=== PDF PAGE (\d+) ===", page_prefix)),
            default=1,
        )
        answer = (
            segment[answer_marker.end() :]
            if answer_marker is not None
            else segment[len(stem_text) :]
        )
        answer_pages = [int(value) for value in re.findall(r"=== PDF PAGE (\d+) ===", answer)]
        trailing_page = re.search(r"(?:\n\s*)=== PDF PAGE (\d+) ===\s*$", answer)
        if trailing_page is not None:
            answer_pages = [page for page in answer_pages if page != int(trailing_page.group(1))]
        answer_pages = sorted(set([page_no, *answer_pages]))
        answer = re.sub(r"\n\s*=== PDF PAGE \d+ ===\s*", " ", answer)
        answer = "\n".join(line.rstrip() for line in answer.strip().splitlines())
        result.append(
            {"text": stem, "page": page_no, "answer_pages": answer_pages, "answer": answer}
        )
    return result


def competency_for(text: str) -> str:
    value = text.casefold()
    if any(term in value for term in ("financial modelling", "financial modeling")):
        return "C_MODEL"
    if any(
        re.search(rf"\b{re.escape(term)}\b", value)
        for term in ("ratio", "enterprise value", "roa", "roe", "roic", "roce", "turnover", "dscr")
    ) or any(
        term in value
        for term in (
            "debt-to-equity",
            "cash conversion cycle",
            "current ratio",
            "quick ratio",
            "interest coverage",
        )
    ):
        return "C_RATIOS"
    if any(
        term in value
        for term in (
            "revenue increased",
            "cash balance",
            "negative cash",
            "inventory has increased",
            "increases from",
            "increased significantly",
            "declining roe",
            "turnover has declined",
        )
    ):
        return "C_SOFT_REASON"
    if (
        "financial statements" in value
        or "income statement" in value
        or "balance sheet" in value
        or "cash flow statement" in value
        or "working capital" in value
        or "depreciation" in value
        or "capex" in value
        or "ebit" in value
        or "eps" in value
    ):
        return "C_STATEMENTS"
    return "C_FINANCE"


def stage_for(question: dict[str, Any], competency: str, page: int) -> str:
    if question["text"].casefold().startswith(("a company's", "a company ")):
        return "soft_2"
    if competency == "C_SOFT_REASON":
        return "soft_2"
    if competency == "C_RATIOS":
        return "technical_2"
    if competency == "C_MODEL":
        return "technical_3"
    if competency == "C_STATEMENTS":
        return "technical_1"
    return "technical_1" if page < 16 else "technical_2"


def clean_answer(text: str) -> str:
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"\n\s*BASIC LEVEL\s*", "\n", text)
    text = re.sub(r"\n\s*ADVANCED LEVEL\s*", "\n", text)
    text = re.sub(r"\n\s*SCENARIO-BASED QUESTIONS\s*", "\n", text)
    return text.strip()


def source_examples(answer: str) -> list[str]:
    lines = [" ".join(line.split()) for line in answer.splitlines() if line.strip()]
    selected = []
    for line in lines:
        lowered = line.casefold()
        if (
            lowered.startswith(("example:", "for example:", "formula:", "step "))
            or " = " in line
            or "₹" in line
            and any(char.isdigit() for char in line)
        ):
            selected.append(line)
    return list(dict.fromkeys(selected))


def write_reports(content: dict[str, Any]) -> None:
    questions = content["questions"]
    source_count = sum(q["source_status"] == "source_derived" for q in questions)
    draft_count = sum(q["source_status"] == "source_based_draft" for q in questions)
    stages = content["stages"]
    stage_lines = []
    for stage in stages:
        by_difficulty = Counter(
            q["difficulty"] for q in questions if q["stage_id"] == stage["stage_id"]
        )
        stage_lines.append(
            f"| `{stage['stage_id']}` | {stage['proposed_display_title']} | "
            f"{len(stage['competency_ids'])} | {len(stage['question_ids'])} | "
            f"{by_difficulty.get('basic', 0)} / {by_difficulty.get('intermediate', 0)} / {by_difficulty.get('advanced', 0)} |"
        )
    module_lines = [
        f"| {module['module_id']} | {module['title']} | {len(module['topics'])} | "
        f"{module['source_references'][0]['pdf_pages'][0]} |"
        for module in content["curriculum_modules"]
    ]
    gap_lines = [
        f"| {gap['area']} | {gap['finding']} | {gap['recommended_action']} |"
        for gap in content["coverage_and_gaps"]["gaps"]
    ]
    coverage = f"""# FINXL Content Coverage Report — V1

## Source documents processed

| Source file | Pages | Processing | Limitations |
|---|---:|---|---|
| `{FMER_NAME}` | 12 | pypdf extraction; pages 6–9 visually rendered and checked | Custom font text extraction is corrupted. Curriculum on pages 6–9 was checked against rendered pages. |
| `{FSR_NAME}` | 27 | pypdf extraction, page-tagged question and answer capture | Text is readable. Extracted boundaries and technical accuracy still need reviewer confirmation. |

The FM&ER filename supplied in the repository is misspelled “Reasearch”; it is preserved exactly in references. Page numbering in this pack is 1-based PDF page numbering.

## Curriculum modules and topics

The brochure contains seven numbered modules. Modules 1–5 appear together on PDF page 6; ratio and valuation topics continue on page 7; module 6 is on page 7; module 7 is on page 8. PDF page 9 gives business-professional contexts such as shaping, running, expanding, or divesting a business. That page is cross-referenced in relevant scenario content but is not assigned an eighth formal module.

| Module | Title | Topic entries | Source page |
|---|---|---:|---:|
{chr(10).join(module_lines)}

Brochure taxonomy entries: **{len(content["curriculum_topics"])}** across seven numbered modules. Supplemental Q&A taxonomy entries: **{len(content["supplemental_source_topics"])}**. Combined topic records: **{len(content["curriculum_topics"]) + len(content["supplemental_source_topics"])}**. Overlap is retained where the brochure repeats a topic in more than one module context. Supplemental Q&A topics are explicitly not treated as an eighth course module.

## Proposed application-stage mapping

| Stage ID | Proposed title | Competencies | Questions | Basic / Intermediate / Advanced |
|---|---|---:|---:|
{chr(10).join(stage_lines)}

Stage IDs and titles follow the existing application sequence and supplied M8.2 definitions. The curriculum modules are not treated as equivalent to stages. Soft-stage competencies and all course-to-stage mappings are proposals inferred from course descriptions; they require FINXL approval.

## Pack counts

- Competencies: **{len(content["competencies"])}**; each is a proposed catalogue entry.
- Supplemental Q&A topic records: **{len(content["supplemental_source_topics"])}**, grouped by source sections/pages and kept separate from the seven numbered brochure modules.
- Questions: **{len(questions)}** total: **{source_count} source-derived** question stems extracted from the Q&A PDF and **{draft_count} newly written source-based drafts** grounded in brochure topics.
- Expected-answer evidence records: **{len(content["expected_answer_evidence"])}**; source answers are preserved as excerpts/answer text for source-derived questions, while draft criteria are labeled as inferred.
- Rubrics: **{len(content["rubrics"])}** draft rubric records across **{len(set(r["competency_id"] for r in content["rubrics"]))}** competencies. Each uses 0–4 levels and weights totaling 1.00; weights and levels are inferred and unapproved.
- Follow-up candidates: **{len(content["follow_up_candidates"])}** source-based draft candidates linked to parent questions and their competency/stage. None is approved.
- Approval: **0** approved records. All records are draft or pending review and remain outside production.

## Source-derived versus drafted material

Source-derived items are the question stems and answer content present in the supplied Financial Statements & Ratios PDF, and the faithfully transcribed curriculum topics/modules from the FM&ER brochure. Source-based draft questions extend documented topics where direct interview questions were absent. Competency definitions/mappings, question-specific evidence framing, rubrics, scoring weights, performance-level indicators, and follow-up wording are proposals, not FINXL-approved assessment standards.

## Coverage gaps and review requirements

| Area | Finding | Recommended action |
|---|---|---|
{chr(10).join(gap_lines)}

### LBO coverage

**No explicit LBO curriculum support was found in either supplied document.** The application’s technical_3 title mentions LBO, but that title is not source evidence. The pack maps documented financial modeling, schedules, forecasting, valuation, and named M&A/transaction topics to the stage only as a proposal. FINXL must provide LBO material or approve a revised technical_3 scope before production content can be authored for LBO.

### Extraction and assessment limitations

- Brochure pages 6–9 were visually checked because custom font mapping corrupts text extraction. The pack avoids using the corrupted extracted text as evidence where visual reading was available.
- The Q&A PDF yielded {source_count} question stems. Questions have no printed question numbers; section headings and 1-based PDF page references are used instead.
- The Q&A PDF includes detailed answers for its questions. The pack preserves answer text on the source-derived question records; reviewers should verify extracted segmentation and source statements. Source explanations that appear questionable must be flagged rather than silently corrected.
- Course-brochure topic listings do not establish exact assessment scope, required difficulty, or approved question wording.
- The source material does not specify official competency definitions, stage mappings, rubric dimensions, weights, performance levels, follow-up wording, or pass thresholds.

## Recommended next steps

1. FINXL content owner reviews and accepts/rejects each competency and six-stage mapping.
2. Subject-matter reviewers verify each source question, answer boundary, technical statement, and page reference.
3. FINXL approves or revises draft questions, expected evidence, follow-ups, and each 0–4 rubric, including its inferred weights.
4. Obtain explicit decision on technical_3/LBO scope and any required LBO source material.
5. Only after approval, prepare a separate controlled import into the existing assessment-content tables; this pack has not been imported.
"""
    (OUTPUT_DIR / "FINXL_Content_Coverage_Report.md").write_text(coverage, encoding="utf-8")

    trace_lines = [
        "# FINXL Source Traceability — V1",
        "",
        "All page numbers below are 1-based PDF pages. The exact source filenames are preserved, including the repository filename typo `Reasearch`. No item is approved.",
        "",
        "## Source documents",
        "",
        f"- `{FMER_NAME}`: PDF pages 6–9 visually checked for curriculum modules, topics, and business-professional examples. Extracted text is corrupted by custom font encoding.",
        f"- `{FSR_NAME}`: all 27 pages text-extracted; extracted question stems are indexed by page and section heading.",
        "",
        "## Competencies",
        "",
        "| Competency ID | Name | Source locations | Source status |",
        "|---|---|---|---|",
    ]
    for comp in content["competencies"]:
        locations = "; ".join(
            f"{src['source_document']} p. {','.join(map(str, src['pdf_pages']))} ({src['section_or_module']})"
            for src in comp["source_references"]
        )
        trace_lines.append(
            f"| `{comp['competency_id']}` | {comp['name']} | {locations} | `{comp['source_status']}` |"
        )
    trace_lines.extend(
        [
            "",
            "## Supplemental Q&A topic taxonomy",
            "",
            "The 27-page Q&A source contributes its own topic groups rather than an invented eighth course module. Each `ST_FSR_*` record links to its PDF page and section group in the JSON and workbook.",
            "",
            "| Source Topic ID | Topic Group | Topic | Source Page |",
            "|---|---|---|---|",
        ]
    )
    for topic in content["supplemental_source_topics"]:
        trace_lines.append(
            f"| `{topic['source_topic_id']}` | {topic['topic_group']} | {topic['topic']} | {topic['source_references'][0]['pdf_pages'][0]} |"
        )
    trace_lines.extend(
        [
            "",
            "## Questions and expected evidence",
            "",
            "| Question ID | Source wording / draft label | Source location | Status | Evidence record |",
            "|---|---|---|---|---|",
        ]
    )
    for question in questions:
        source = question["source_references"][0]
        loc = f"{source['source_document']} p. {','.join(map(str, source['pdf_pages']))}; {source.get('original_question_number_or_heading') or source['section_or_module']}"
        label = (
            "Extracted source question"
            if question["source_status"] == "source_derived"
            else "New source-based draft; not an original FINXL question"
        )
        trace_lines.append(
            f"| `{question['question_id']}` | {label}: {question['text']} | {loc} | `{question['source_status']}` | `{question['expected_answer_evidence_id']}` |"
        )
    trace_lines.extend(
        [
            "",
            "## Rubrics",
            "",
            "| Rubric ID | Competency | Applicable questions | Source basis | Status |",
            "|---|---|---|---|---|",
        ]
    )
    for rubric in content["rubrics"]:
        comp = next(
            c for c in content["competencies"] if c["competency_id"] == rubric["competency_id"]
        )
        qids = ", ".join(f"`{qid}`" for qid in rubric["applicable_question_ids"])
        locations = "; ".join(
            f"{src['source_document']} p. {','.join(map(str, src['pdf_pages']))}"
            for src in rubric["source_references"]
        )
        trace_lines.append(
            f"| `{rubric['rubric_id']}` | `{comp['competency_id']}` | {qids} | Proposed indicators inferred from source topics/evidence; weights and level descriptors not in source ({locations}) | `inferred_draft` |"
        )
    trace_lines.extend(
        [
            "",
            "## Follow-up candidates",
            "",
            "Each follow-up is newly worded and is linked in JSON to its parent question, competency, stage, and evidence concepts. Its traceability inherits the parent question's source reference. No follow-up wording appears in the supplied source PDFs; every candidate is `source_based_draft` and pending review.",
            "",
            "## Inferred mappings",
            "",
            "The six application-stage mappings and competency associations are proposals. Course materials do not map their modules to `soft_1`, `soft_2`, `soft_3`, `technical_1`, `technical_2`, or `technical_3`. The stage mapping source status is `inferred_draft`.",
            "",
        ]
    )
    (OUTPUT_DIR / "FINXL_Source_Traceability.md").write_text(
        "\n".join(trace_lines), encoding="utf-8"
    )


def source_question_entry(item: dict[str, Any], index: int) -> dict[str, Any]:
    competency = competency_for(item["text"])
    stage = stage_for(item, competency, item["page"])
    module = {
        "C_STATEMENTS": ["M3", "M5"],
        "C_RATIOS": ["M5"],
        "C_MODEL": ["M1", "M2", "M5"],
        "C_SOFT_REASON": ["M3", "M4", "M5", "M7"],
        "C_FINANCE": ["M3"],
    }[competency]
    answer = clean_answer(item["answer"])
    first = [
        " ".join(part.split()) for part in re.split(r"(?<=[.!?])\s+|\n", answer) if part.strip()
    ]
    evidence = first[:3] or [
        "Source question is present; source answer extraction requires reviewer confirmation."
    ]
    scenario = (
        stage == "soft_2"
        or item["text"].casefold().startswith(("a company's", "a company "))
        or any(word in item["text"].casefold() for word in ("how would you", "investigate"))
    )
    difficulty = "basic" if item["page"] <= 8 or item["page"] in range(16, 21) else "advanced"
    if scenario:
        difficulty = "intermediate" if item["page"] < 25 else "advanced"
    category = (
        "scenario_based"
        if stage == "soft_2"
        else ("analytical" if difficulty == "advanced" else "conceptual")
    )
    identifier = f"Q_SRC_FSR_{index:03d}"
    if item["text"].casefold().startswith(("a company's", "a company ")):
        source_heading = "Scenario-Based Questions"
    elif item["page"] <= 8:
        source_heading = "Basic Level"
    elif item["page"] <= 13:
        source_heading = "Advanced Level"
    elif item["page"] == 16:
        source_heading = "Ratio Analysis – Mock Interview Answers (Basic Level)"
    else:
        source_heading = "Ratio Analysis – Mock Interview Answers (Advanced Level)"
    source_ref = ref(
        FSR_NAME,
        item["answer_pages"],
        "Financial Statements & Financial Modelling – Interview Questions and Answers",
        "Question stem and its source answer are extracted from the cited page(s); answer text is retained below for reviewer traceability.",
    )
    source_ref["original_question_number_or_heading"] = source_heading
    return {
        "question_id": identifier,
        "text": item["text"],
        "competency_id": competency,
        "stage_id": stage,
        "curriculum_module_ids": module,
        "source_topic_ids": [],
        "difficulty": difficulty,
        "question_category": category,
        "question_kind": "base",
        "expected_answer_evidence_id": f"E_{identifier}",
        "rubric_id": f"R_{competency}_V1",
        "key_concepts_expected": evidence[:5],
        "common_incomplete_answer_indicators": [],
        "source_answer_text": answer,
        "source_references": [source_ref],
        "source_status": "source_derived",
        "review_status": "pending_finxl_review",
        "approval_status": "draft",
        "review_notes": "Question wording and answer meaning are source-derived. Confirm extraction, technical accuracy, and suitability as an assessment item; brochure or Q&A presence is not approval.",
    }


def source_topic_ids_for_question(
    text: str, pages: list[int], topic_records: list[dict[str, Any]]
) -> list[str]:
    value = text.casefold()
    groups: set[str] = set()
    if "financial model" in value or "financial statements" in value:
        groups.update(("Statements and Modeling",))
    if "income statement" in value:
        groups.update(("Income Statement",))
    if "balance sheet" in value:
        groups.update(("Balance Sheet", "Balance Sheet Items"))
    if "equation" in value and "balance sheet" in value:
        groups.add("Accounting Equation")
    if "cash flow" in value or "cash balance" in value:
        groups.update(("Cash Flow Statement", "Scenario Analysis"))
    if "working capital" in value:
        groups.add("Working Capital")
    if "interconnect" in value:
        groups.add("Statement Links")
    if "depreciation" in value or "capex" in value or "opex" in value or "cogs" in value:
        groups.add("Depreciation and CapEx")
    if "ebit" in value or "ebitda" in value:
        groups.add("Earnings Measures")
    if "eps" in value:
        groups.add("EPS")
    if (
        "treasury stock" in value
        or "retained earnings" in value
        or "deferred revenue" in value
        or "non-controlling interest" in value
    ):
        groups.add("Balance Sheet Items")
    if "ratio analysis" in value:
        groups.add("Ratio Analysis")
    if "profitability" in value or "profit margin" in value:
        groups.add("Profitability Ratios")
    if "liquidity" in value or "current ratio" in value or "quick ratio" in value:
        groups.add("Liquidity Ratios")
    if "efficiency" in value or "turnover" in value or "cash conversion cycle" in value:
        groups.add("Efficiency Ratios")
    if "solvency" in value or "debt" in value or "dscr" in value or "interest coverage" in value:
        groups.add("Solvency Ratios")
    if "market value" in value:
        groups.add("Market Value Ratios")
    if "enterprise value" in value:
        groups.add("Enterprise Value")
    if "roa" in value or "roe" in value or "roic" in value or "roce" in value:
        groups.add("Returns and Capital")
    if value.startswith(("a company's", "a company ")):
        groups.add("Scenario Analysis")
    return [
        topic["source_topic_id"]
        for topic in topic_records
        if topic["topic_group"] in groups and topic["source_references"][0]["pdf_pages"][0] in pages
    ]


def matches_topic(searchable: str, topic_text: str) -> bool:
    stop_words = {
        "what",
        "does",
        "with",
        "from",
        "using",
        "used",
        "and",
        "the",
        "for",
        "its",
        "how",
        "any",
        "your",
        "each",
        "types",
        "course",
        "named",
        "listed",
        "analysis",
        "understanding",
        "concepts",
    }
    terms = [
        term
        for term in re.findall(r"[a-z0-9]+", topic_text.casefold())
        if len(term) > 3 and term not in stop_words
    ]
    if not terms:
        return False
    matched = [bool(re.search(rf"\b{re.escape(term)}\b", searchable.casefold())) for term in terms]
    acronyms = {term.casefold() for term in re.findall(r"\b[A-Z]{2,5}\b", topic_text)}
    acronym_found = any(
        re.search(rf"\b{re.escape(term)}\b", searchable, flags=re.I) for term in acronyms
    )
    return all(matched) or acronym_found


def curriculum_topic_ids_for_question(
    question: dict[str, Any], topic_records: list[dict[str, Any]]
) -> list[str]:
    searchable = (question["text"] + " " + " ".join(question["key_concepts_expected"])).casefold()
    modules = set(question["curriculum_module_ids"])
    result = []
    for topic in topic_records:
        if topic["module_id"] not in modules:
            continue
        if matches_topic(searchable, topic["topic"]):
            result.append(topic["topic_id"])
    return result


def main() -> None:
    if not (SOURCE_DIR / FMER_NAME).is_file() or not (SOURCE_DIR / FSR_NAME).is_file():
        raise FileNotFoundError("Both source PDFs are required in docs/source-material.")

    module_records = []
    for module_id, title, page, topics in MODULES:
        module_records.append(
            {
                "module_id": module_id,
                "title": title,
                "topics": topics,
                "source_references": [ref(FMER_NAME, [page], f"Module {module_id}: {title}")],
                "source_status": "source_derived",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
            }
        )

    curriculum_topic_records = [
        {
            "topic_id": f"T_{mid}_{index:02d}",
            "module_id": mid,
            "topic": topic,
            "source_status": "source_derived",
            "approval_status": "draft",
            "review_status": "pending_finxl_review",
            "source_references": [ref(FMER_NAME, [page], f"Module {mid}: {title}")],
        }
        for mid, title, page, topics in MODULES
        for index, topic in enumerate(topics, 1)
    ]
    supplemental_topic_records = [
        {
            "source_topic_id": f"ST_FSR_{index:03d}",
            "source_id": "SRC_FSR",
            "topic_group": group,
            "topic": topic,
            "source_status": "source_derived",
            "approval_status": "draft",
            "review_status": "pending_finxl_review",
            "source_references": [
                ref(
                    FSR_NAME,
                    [page],
                    group,
                    "Topic faithfully restructured from the supplied Q&A document; not a separate numbered brochure module.",
                )
            ],
        }
        for index, (group, page, topic) in enumerate(SUPPLEMENTAL_TOPICS, 1)
    ]

    competencies = []
    for row in COMPETENCIES:
        cid, name, description, objectives, stages, modules, topics, status, pages = row
        competencies.append(
            {
                "competency_id": cid,
                "name": name,
                "description": description,
                "learning_objectives": objectives,
                "stage_ids": stages,
                "curriculum_module_ids": modules,
                "relevant_topics": topics,
                "expected_knowledge_or_capability": objectives,
                "source_references": refs_for_pages(pages, "; ".join(modules)),
                "source_status": status,
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "review_notes": "Proposed competency catalogue entry; FINXL content owner must confirm scope, definition, and stage mapping.",
            }
        )

    extracted = read_questions(SOURCE_DIR / FSR_NAME)
    questions = [source_question_entry(item, index) for index, item in enumerate(extracted, 1)]
    for question in questions:
        question["source_topic_ids"] = source_topic_ids_for_question(
            question["text"],
            question["source_references"][0]["pdf_pages"],
            supplemental_topic_records,
        )
    for row in EXTRA_QUESTIONS:
        (
            qid,
            text,
            cid,
            stage,
            difficulty,
            category,
            concepts,
            modules_topics,
            pages,
            module_label,
            reason,
        ) = row
        module_ids = [part for part in module_label.split("/") if part.startswith("M")]
        questions.append(
            {
                "question_id": qid,
                "text": text,
                "competency_id": cid,
                "stage_id": stage,
                "curriculum_module_ids": module_ids,
                "curriculum_topic_ids": [],
                "source_topic_ids": [],
                "difficulty": difficulty,
                "question_category": category,
                "question_kind": "base",
                "expected_answer_evidence_id": f"E_{qid}",
                "rubric_id": f"R_{cid}_V1",
                "key_concepts_expected": concepts,
                "common_incomplete_answer_indicators": [],
                "source_references": refs_for_pages(pages, module_label, reason),
                "source_status": "source_based_draft",
                "review_status": "pending_finxl_review",
                "approval_status": "draft",
                "review_notes": reason
                + " Not an original FINXL interview question; no source answer is claimed.",
            }
        )

    for question in questions:
        question["curriculum_topic_ids"] = curriculum_topic_ids_for_question(
            question, curriculum_topic_records
        )
    for competency in competencies:
        competency["curriculum_topic_ids"] = [
            topic["topic_id"]
            for topic in curriculum_topic_records
            if topic["module_id"] in competency["curriculum_module_ids"]
            and any(
                matches_topic(relevant, topic["topic"])
                for relevant in competency["relevant_topics"]
            )
        ]
        competency["source_topic_ids"] = list(
            dict.fromkeys(
                topic_id
                for question in questions
                if question["competency_id"] == competency["competency_id"]
                for topic_id in question["source_topic_ids"]
            )
        )

    evidence_records = []
    for question in questions:
        source_based = question["source_status"] == "source_derived"
        source_answer = question.get("source_answer_text", "")
        evidence_records.append(
            {
                "evidence_id": question["expected_answer_evidence_id"],
                "question_id": question["question_id"],
                "competency_id": question["competency_id"],
                "essential_concepts": question["key_concepts_expected"][:3],
                "supporting_explanation": "Demonstrate a coherent explanation linking the stated concepts to the question."
                if not source_based
                else "See the preserved source answer text on the question record; evidence points above are faithfully restructured from its opening statements.",
                "application_or_reasoning": "Apply the listed course topic to the question context and explain the reasoning."
                if not source_based
                else "Use the application, formula, or reasoning included in the source answer where the question requires it.",
                "examples_or_calculations": source_examples(source_answer) if source_based else [],
                "incomplete_or_missing_evidence": [],
                "source_answer_excerpt": source_answer[:3000] if source_based else None,
                "source_status": "source_derived" if source_based else "inferred_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "source_references": question["source_references"],
                "review_notes": "Evidence is an unvalidated draft; do not treat as a memorized answer key. Add question-specific omissions only when supported and reviewed.",
            }
        )

    question_groups: dict[str, list[dict[str, Any]]] = {}
    for q in questions:
        question_groups.setdefault(q["competency_id"], []).append(q)
    rubrics = []
    for comp in competencies:
        cid = comp["competency_id"]
        if cid not in question_groups:
            continue
        dimensions = [
            {
                "key": "conceptual_accuracy",
                "weight": "0.40",
                "performance_indicators": [
                    "Explains the relevant concepts accurately",
                    "Uses terminology supported by the question source",
                ],
            },
            {
                "key": "evidence_and_application",
                "weight": "0.35",
                "performance_indicators": [
                    "Uses relevant evidence or calculations",
                    "Applies the concepts to the stated question",
                ],
            },
            {
                "key": "reasoning_and_clarity",
                "weight": "0.25",
                "performance_indicators": [
                    "Explains a coherent line of reasoning",
                    "States limitations or uncertainty when relevant",
                ],
            },
        ]
        rubrics.append(
            {
                "rubric_id": f"R_{cid}_V1",
                "rubric_version_id": f"R_{cid}_V1",
                "competency_id": cid,
                "applicable_question_ids": [q["question_id"] for q in question_groups[cid]],
                "dimensions": dimensions,
                "performance_levels": [
                    {
                        "score": 0,
                        "label": "No assessable evidence",
                        "evidence_description": "No relevant evidence is demonstrated.",
                    },
                    {
                        "score": 1,
                        "label": "Limited",
                        "evidence_description": "Evidence is fragmentary or substantially incomplete.",
                    },
                    {
                        "score": 2,
                        "label": "Developing",
                        "evidence_description": "Some relevant concepts are present, but explanation or application is incomplete.",
                    },
                    {
                        "score": 3,
                        "label": "Competent",
                        "evidence_description": "Relevant concepts and supporting reasoning are explained with minor omissions.",
                    },
                    {
                        "score": 4,
                        "label": "Strong",
                        "evidence_description": "Relevant concepts, evidence, application, and reasoning are integrated; limitations are handled where relevant.",
                    },
                ],
                "scoring_scale": [
                    {"score": score, "label": label}
                    for score, label in enumerate(
                        ["No assessable evidence", "Limited", "Developing", "Competent", "Strong"]
                    )
                ],
                "evidence_requirements": [
                    "At least one relevant evidence point from the linked question's expected-answer evidence."
                ],
                "insufficient_evidence_criteria": [
                    "Response contains no assessable evidence for the rubric dimensions."
                ],
                "source_status": "inferred_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "source_references": comp["source_references"],
                "review_notes": "Weights and performance-level language are proposed for review because source documents do not define scoring weights or performance levels. Existing backend scale is 0-4 and weights must sum to 1.0. Server pass threshold remains unchanged and is not included here.",
            }
        )

    followups = []
    for q in questions:
        concepts = q["key_concepts_expected"]
        focus = concepts[0] if concepts else "the evidence you used"
        follow_up_text = FOLLOW_UP_TEXTS.get(q["question_id"])
        if follow_up_text is None:
            raise ValueError(f"No reviewed-draft follow-up wording for {q['question_id']}")
        followups.append(
            {
                "follow_up_id": f"FU_{q['question_id']}_01",
                "parent_question_id": q["question_id"],
                "competency_id": q["competency_id"],
                "stage_id": q["stage_id"],
                "text": follow_up_text,
                "intended_evidence_gap": f"Clarify evidence and reasoning for the original question's expected concept: {focus}.",
                "source_status": "source_based_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "source_references": q["source_references"],
                "review_notes": "New candidate wording grounded in the parent question and its expected-answer concepts. Not approved for production; reviewer should check naturalness, specificity, and non-repetition.",
            }
        )

    stage_titles = {
        "soft_1": "Communication & Behavioral Foundations",
        "soft_2": "Problem Framing & Structured Thinking",
        "soft_3": "Executive Presence & Stakeholder Influence",
        "technical_1": "Accounting Fundamentals & 3-Statement Mechanics",
        "technical_2": "Valuation Methodologies (DCF & Comps)",
        "technical_3": "LBO Modeling & M&A Mechanics",
    }
    stages = []
    for stage_id, title in stage_titles.items():
        stage_comps = [c for c in competencies if stage_id in c["stage_ids"]]
        module_ids = sorted({m for c in stage_comps for m in c["curriculum_module_ids"]})
        qids = [q["question_id"] for q in questions if q["stage_id"] == stage_id]
        stages.append(
            {
                "stage_id": stage_id,
                "proposed_display_title": title,
                "competency_ids": [c["competency_id"] for c in stage_comps],
                "curriculum_module_ids": module_ids,
                "learning_objectives": list(
                    dict.fromkeys(obj for c in stage_comps for obj in c["learning_objectives"])
                ),
                "difficulty_coverage": sorted(
                    {q["difficulty"] for q in questions if q["stage_id"] == stage_id}
                ),
                "question_ids": qids,
                "mapping_rationale": "Many-to-many proposed mapping based on overlapping learning topics; application stage identifiers are preserved. Soft-skill mappings are inferred from course preparation and are not source-defined assessment constructs."
                if stage_id.startswith("soft")
                else "Proposed curriculum alignment; module and application-stage boundaries are not stated as equivalent in the source.",
                "source_status": "inferred_draft",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
                "source_references": refs_for_pages(
                    sorted(
                        {
                            p
                            for c in stage_comps
                            for s in c["source_references"]
                            for p in s["pdf_pages"]
                        }
                    ),
                    "; ".join(module_ids),
                )
                if stage_comps
                else [],
            }
        )

    question_counts = Counter(q["stage_id"] for q in questions)
    difficulty_counts = Counter((q["stage_id"], q["difficulty"]) for q in questions)
    coverage_gaps = [
        {
            "gap_id": "GAP_LBO",
            "area": "LBO",
            "finding": "The supplied FM&ER brochure and Financial Statements & Ratios Q&A do not identify LBO modeling or LBO mechanics as course content. The technical_3 application title mentions LBO, but that is not evidence of curriculum coverage.",
            "source_status": "needs_finxl_review",
            "review_status": "pending_finxl_review",
            "recommended_action": "FINXL content owner to provide explicit LBO curriculum or confirm that technical_3 should assess only documented financial modeling and transaction topics.",
        },
        {
            "gap_id": "GAP_SOFT",
            "area": "Soft-skill definitions",
            "finding": "The brochure names communication/interpersonal skills, mock interviews, interview scripting, positive attitude, and emotional intelligence; it does not define the six-stage soft competencies or formal rubrics.",
            "source_status": "inferred_draft",
            "review_status": "pending_finxl_review",
            "recommended_action": "Approve or revise each soft-stage competency and its boundaries.",
        },
        {
            "gap_id": "GAP_RUBRIC",
            "area": "Scoring",
            "finding": "Neither source defines rubric dimensions, weights, or performance levels. The rubric pack proposes these solely for review.",
            "source_status": "inferred_draft",
            "review_status": "pending_finxl_review",
            "recommended_action": "Validate criteria and weights with assessment/content owners before import or use.",
        },
        {
            "gap_id": "GAP_EXCEL",
            "area": "Excel questions",
            "finding": "The brochure provides a detailed Excel topic list but no formal Excel interview questions or answers.",
            "source_status": "source_based_draft",
            "review_status": "pending_finxl_review",
            "recommended_action": "Review the source-based draft prompts and add approved practical tasks if required.",
        },
        {
            "gap_id": "GAP_CORP_ACTIONS",
            "area": "Corporate action treatments",
            "finding": "The brochure lists actions and related ownership concepts but does not describe their accounting or valuation treatments.",
            "source_status": "needs_finxl_review",
            "review_status": "pending_finxl_review",
            "recommended_action": "Obtain FINXL lesson material or content-owner-approved treatment notes before assessing detailed treatment.",
        },
        {
            "gap_id": "GAP_FMER_OCR",
            "area": "FM&ER text extraction",
            "finding": "The brochure's embedded/custom font produces corrupted text extraction. Curriculum pages 6-9 were visually rendered and checked; several pages are promotional or irrelevant to assessment content.",
            "source_status": "needs_finxl_review",
            "review_status": "pending_finxl_review",
            "recommended_action": "Use the rendered brochure pages as source verification; provide a text-accessible original for future automated extraction if exact transcription is needed.",
        },
        {
            "gap_id": "GAP_SOURCE_TERMS",
            "area": "Source wording requiring SME check",
            "finding": "The brochure prints 'YEARFRACE' (PDF p. 6), and the Q&A answer includes 'Gain Associated with the Juice Transaction' (PDF p. 5). Both strings are retained as supplied; their intended meaning has not been inferred or corrected.",
            "source_status": "needs_finxl_review",
            "review_status": "pending_finxl_review",
            "recommended_action": "Ask the FINXL content owner/SME to confirm whether these are source typos, specialized terms, or intended wording before retaining them in approved content.",
        },
    ]

    content = {
        "schema_version": "finxl_assessment_content.v1",
        "pack_version": "1.0.0",
        "generated_at": "2026-11-12",
        "governance": {
            "approval_status": "draft",
            "review_status": "pending_finxl_review",
            "production_approved": False,
            "approval_note": "All content is draft or pending FINXL review. Nothing in this pack is production-approved or imported into the application database.",
            "application_stage_ids": list(stage_titles),
            "difficulty_values": ["basic", "intermediate", "advanced"],
            "question_category_values": [
                "conceptual",
                "practical",
                "scenario_based",
                "analytical",
                "communication",
            ],
            "source_status_values": list(STATUSES),
            "approval_status_values": ["draft", "review", "approved", "retired"],
            "review_status_values": ["pending_finxl_review", "accepted", "rejected"],
            "backend_alignment": "Question and rubric IDs are pack identifiers. Existing backend assessment tables are not modified. Future import must map draft/review metadata to the existing content-governance lifecycle and must not import non-approved content into production selection.",
        },
        "source_documents": [
            {
                "source_id": "SRC_FMER",
                "file_name": FMER_NAME,
                "relative_path": "docs/source-material/" + FMER_NAME,
                "page_count": 12,
                "role": "FM&ER course brochure",
                "extraction_method": "pypdf text extraction plus visual render review of pages 6-9",
                "extraction_quality": "Custom font corrupts substantial extracted text. Pages 6-9 were visually inspected and curriculum taxonomy transcribed; pages 10 contains encoded glyph noise. See extraction limitations.",
                "source_status": "source_derived",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
            },
            {
                "source_id": "SRC_FSR",
                "file_name": FSR_NAME,
                "relative_path": "docs/source-material/" + FSR_NAME,
                "page_count": 27,
                "role": "Financial Statements & Financial Modelling – Interview Questions and Answers",
                "extraction_method": "pypdf text extraction by page",
                "extraction_quality": "Text extraction returned readable question stems and answers across 27 pages. Page references are 1-based PDF pages.",
                "source_status": "source_derived",
                "approval_status": "draft",
                "review_status": "pending_finxl_review",
            },
        ],
        "curriculum_modules": module_records,
        "curriculum_topics": curriculum_topic_records,
        "supplemental_source_topics": supplemental_topic_records,
        "stages": stages,
        "competencies": competencies,
        "questions": questions,
        "expected_answer_evidence": evidence_records,
        "rubrics": rubrics,
        "follow_up_candidates": followups,
        "coverage_and_gaps": {
            "question_counts_by_stage": dict(question_counts),
            "question_counts_by_stage_and_difficulty": {
                f"{stage}:{difficulty}": count
                for (stage, difficulty), count in sorted(difficulty_counts.items())
            },
            "gaps": coverage_gaps,
        },
        "review_approval_register": [
            {
                "review_item_id": f"REVIEW_{row[key]}",
                "item_type": item_type,
                "item_id": row[key],
                "owner": "FINXL content owner / assessment reviewer",
                "status": "pending_finxl_review",
                "decision": None,
                "review_notes": note,
            }
            for item_type, rows, key, note in [
                (
                    "stage",
                    stages,
                    "stage_id",
                    "Confirm stage title, course mapping, learning objectives, and difficulty coverage.",
                ),
                (
                    "curriculum_module",
                    module_records,
                    "module_id",
                    "Confirm extracted module title, topic inventory, and source page.",
                ),
                (
                    "curriculum_topic",
                    curriculum_topic_records,
                    "topic_id",
                    "Confirm source wording and module/page traceability.",
                ),
                (
                    "supplemental_source_topic",
                    supplemental_topic_records,
                    "source_topic_id",
                    "Confirm topic restructuring and Q&A source/page linkage.",
                ),
                (
                    "competency",
                    competencies,
                    "competency_id",
                    "Confirm definition, source mapping, scope, and stage assignment.",
                ),
                (
                    "question",
                    questions,
                    "question_id",
                    "Confirm wording, assessment relevance, answer evidence, technical accuracy, and assessment authorization.",
                ),
                (
                    "rubric",
                    rubrics,
                    "rubric_id",
                    "Confirm dimensions, weights, 0-4 performance indicators, and insufficient-evidence criteria.",
                ),
                (
                    "follow_up",
                    followups,
                    "follow_up_id",
                    "Confirm relevance, naturalness, evidence gap, and suitability as a bank candidate.",
                ),
            ]
            for row in rows
        ],
        "extraction_limitations": [
            "FM&ER PDF text extraction is corrupted by custom font encoding. Visual render review of curriculum pages 6-9 was used to transcribe modules and topics; source wording is retained where readable.",
            "The brochure's statements about course coverage do not establish that each listed activity is an interview assessment item.",
            "The question-and-answer document contains 35 extracted question stems. Question-answer segmentation and page references require FINXL review before any import.",
            "The course documents do not establish official mapping to the application's stage identifiers, nor do they define scoring rubrics.",
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "finxl_assessment_content_v1.json").write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_reports(content)
    print(
        f"questions={len(questions)} source_questions={len(extracted)} competencies={len(competencies)} topics={len(content['curriculum_topics'])} rubrics={len(rubrics)} followups={len(followups)}"
    )


if __name__ == "__main__":
    main()
