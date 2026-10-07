import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("AI_API_KEY")

if not API_KEY:
    raise Exception("AI_API_KEY is not set")

client = genai.Client(api_key=API_KEY)

MODEL = "gemini-3.8-flash"

OUTPUT_FILE = PROJECT_ROOT / "tests" / "gemini_resume_output.json"


# ============================================================
# ORIGINAL STRUCTURED RESUME
# ============================================================

ORIGINAL_RESUME = {
    "personal_info": {
        "name": "UJMA MULANI",
        "location": "Pune, Maharashtra",
        "phone": "7798492771",
        "email": "ujma2111@gmail.com",
        "linkedin": "linkedin.com/in/ujma-mulani-63423b201",
        "github": "github.com/Ujma21"
    },

    "headline": "MCA STUDENT | DATA ANALYSIS | SOFTWARE DEVELOPMENT",

    "summary": (
        "MCA student with a strong foundation in Python, SQL, data management, "
        "software development, and analytical problem solving. Experienced in "
        "developing data-driven applications involving structured databases, "
        "assessment data, dashboards, API integration, and real-time systems. "
        "Strong academic performance with an interest in financial markets, "
        "research, quantitative problem solving, and data-driven decision making."
    ),

    "skills": {
        "Data & Analysis": [
            "Python",
            "SQL",
            "Data Management",
            "Data Interpretation",
            "Quantitative Problem Solving"
        ],

        "Programming": [
            "Java",
            "Python",
            "C++",
            "JavaScript",
            "SQL"
        ],

        "Backend & APIs": [
            "Spring Boot",
            "FastAPI",
            "REST APIs",
            "Hibernate",
            "Spring Data JPA",
            "WebSockets",
            "JWT Authentication"
        ],

        "Databases": [
            "MySQL",
            "MongoDB Atlas"
        ],

        "Frontend": [
            "React.js",
            "HTML5",
            "CSS3",
            "Thymeleaf",
            "Bootstrap",
            "Tailwind CSS"
        ],

        "Core": [
            "Object-Oriented Programming",
            "Data Structures & Algorithms",
            "MVC Architecture",
            "Database Management",
            "Authentication & Authorization"
        ],

        "Tools": [
            "Git",
            "GitHub",
            "Maven",
            "Postman",
            "Judge0 API",
            "VS Code",
            "Eclipse",
            "Spring Tool Suite (STS)"
        ],

        "Operating Systems": [
            "Windows",
            "Linux (Basic)"
        ]
    },

    "projects": [
        {
            "name": "SkillSphere",
            "subtitle": "Intelligent Career Readiness & Placement Ecosystem",
            "technologies": [
                "React.js",
                "Node.js",
                "Express.js",
                "MongoDB Atlas",
                "JWT",
                "Tailwind CSS",
                "Cloudinary",
                "OpenAI API",
                "Multer",
                "Nodemailer",
                "Recharts",
                "Axios",
                "Git"
            ],
            "bullets": [
                "Developed an AI-powered career readiness platform for student placement preparation, incorporating assessment data, skill tracking, resume management, and placement analytics.",
                "Implemented career assessments and personalized learning roadmaps to organize student readiness information and support data-driven career recommendations.",
                "Developed role-based dashboards for presenting structured career and placement information.",
                "Integrated MongoDB Atlas for persistent data management and Recharts for analytics-oriented data visualization."
            ]
        },

        {
            "name": "CodeX Arena",
            "subtitle": "Real-Time Competitive Coding Battle Platform",
            "technologies": [
                "Python",
                "FastAPI",
                "React.js",
                "MongoDB Atlas",
                "WebSockets",
                "JWT",
                "Judge0 API",
                "Tailwind CSS",
                "PyMongo",
                "Git"
            ],
            "bullets": [
                "Developed a real-time competitive coding platform for programming challenges, competitions, and user activity.",
                "Built REST APIs using FastAPI and MongoDB Atlas to manage structured user, competition, and submission data.",
                "Integrated Judge0 API for multi-language code execution and programming-result processing.",
                "Implemented WebSockets for real-time matchmaking and JWT-based authentication for secure platform access."
            ]
        },

        {
            "name": "Fuel Agency Management System",
            "technologies": [
                "Java",
                "Spring Boot",
                "Hibernate",
                "Thymeleaf",
                "MySQL",
                "Maven"
            ],
            "bullets": [
                "Developed a full-stack LPG gas booking and management system with customer, supplier, cylinder, and booking management modules.",
                "Integrated MySQL with Hibernate to manage structured relational application data and persistent booking information.",
                "Implemented role-based authentication and authorization for Admin and Customer users.",
                "Developed automated email notifications supporting registration and login-related workflows."
            ]
        }
    ],

    "education": [
        {
            "degree": "Master of Computer Application (MCA)",
            "dates": "2025–2027",
            "institution": "School of Computer Studies, Sri Balaji University, Pune",
            "gpa": "8.71"
        },
        {
            "degree": "Bachelor of Computer Application (BCA)",
            "dates": "2022–2025",
            "institution": "Alard College of Business Studies, Pune",
            "gpa": "8.6"
        }
    ],

    "certifications": [
        "MERN Full Stack Development — SmartBridge, NASSCOM FutureSkills Prime",
        "SAP Certified Associate — Back-End Developer (ABAP Cloud) — In Progress, Expected 2026"
    ],

    "achievements": [
        "1st Place — Chess, Intra-College Event."
    ],

    "leadership": [
        "Academic Coordinator for Semester III, supporting the smooth conduct of academic activities."
    ]
}


# ============================================================
# SAMPLE JOB DESCRIPTION
# ============================================================

JOB_DESCRIPTION = """
Financial Analyst

Responsibilities:
- Perform financial analysis and data analysis.
- Prepare reports, forecasts, and budgets.
- Work with Excel, SQL, and Power BI.
- Analyze financial and business data.
- Support quantitative problem solving and decision making.
- Communicate analytical findings clearly.

Requirements:
- Strong analytical and problem-solving skills.
- Knowledge of SQL and data analysis.
- Understanding of financial analysis and reporting.
- Knowledge of Excel and Power BI.
- Good communication skills.
"""


# ============================================================
# GEMINI PROMPT
# ============================================================

PROMPT = f"""
You are an AI resume optimization engine.

Your task is to optimize the resume for the provided job description.

CRITICAL RULE:
You are NOT allowed to reconstruct, redesign, reorganize, or invent
the candidate's resume data.

You may improve wording of:
- Professional summary
- Project bullet points

You may improve keyword alignment where the candidate already has
the relevant skill or experience.

You MUST preserve all factual information.

DO NOT:
- Invent skills
- Invent experience
- Invent projects
- Invent certifications
- Invent achievements
- Invent education
- Invent employers or institutions
- Change GPA
- Change dates
- Change project names
- Remove institutions
- Remove certifications
- Move achievements into certifications
- Move leadership into another section
- Flatten skill categories
- Rename skill categories
- Merge skill categories
- Delete skill categories
- Add skills merely because they appear in the job description

IMPORTANT:
The candidate does NOT automatically possess every skill in the
job description.

If the JD contains Excel, Power BI, financial analysis, etc. but the
candidate's resume does not explicitly contain those skills, DO NOT
add them to the resume.

The output MUST preserve this exact top-level structure:

personal_info
headline
summary
skills
projects
education
certifications
achievements
leadership

The skills object MUST preserve every existing category and its
existing skills.

Education must preserve:
- degree
- dates
- institution
- GPA

Projects must preserve:
- project name
- technologies
- factual project information

Return ONLY valid JSON.

JOB DESCRIPTION:
{JOB_DESCRIPTION}

ORIGINAL STRUCTURED RESUME:
{json.dumps(ORIGINAL_RESUME, indent=2)}
"""


# ============================================================
# CALL GEMINI
# ============================================================

print("=" * 70)
print("FINXL GEMINI RESUME OPTIMIZATION TEST")
print("=" * 70)

print("\nAPI key loaded successfully")
print("Model:", MODEL)

print("\nSending structured resume to Gemini...")

interaction = client.interactions.create(
    model=MODEL,
    input=PROMPT
)

response_text = interaction.output_text.strip()

print("Gemini response received.")


# ============================================================
# PARSE JSON
# ============================================================

try:
    optimized_resume = json.loads(response_text)
    json_valid = True

except json.JSONDecodeError:

    # Gemini sometimes wraps valid JSON inside Markdown
    # code fences such as ```json ... ```.
    cleaned_response = response_text.strip()

    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[len("```json"):].strip()

    elif cleaned_response.startswith("```"):
        cleaned_response = cleaned_response[3:].strip()

    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3].strip()

    try:
        optimized_resume = json.loads(cleaned_response)
        json_valid = True

        print("\nGemini returned valid JSON inside Markdown code fences.")
        print("Markdown wrapper removed successfully.")

    except json.JSONDecodeError:
        json_valid = False
        optimized_resume = {}

        print("\nFAIL: Gemini did not return valid JSON.")
        print("\nRaw Gemini response:")
        print(response_text)

# ============================================================
# SAVE GEMINI OUTPUT
# ============================================================

OUTPUT_FILE.write_text(
    json.dumps(
        optimized_resume if json_valid else {
            "raw_response": response_text
        },
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print(f"\nGemini output saved to:")
print(OUTPUT_FILE)


# ============================================================
# TEST HELPERS
# ============================================================

passed = 0
failed = 0


def test(name, condition, details=""):
    global passed, failed

    if condition:
        print(f"PASS  | {name}")
        passed += 1
    else:
        print(f"FAIL  | {name}")
        if details:
            print(f"      {details}")
        failed += 1


# ============================================================
# JSON TEST
# ============================================================

print("\n" + "=" * 70)
print("1. OUTPUT FORMAT")
print("=" * 70)

test(
    "Gemini returned valid JSON",
    json_valid
)

if not json_valid:
    print("\nTesting cannot continue because Gemini returned invalid JSON.")
    print(f"\nRESULT: {passed} PASSED | {failed} FAILED")
    raise SystemExit(1)


# ============================================================
# TOP-LEVEL STRUCTURE
# ============================================================

print("\n" + "=" * 70)
print("2. RESUME STRUCTURE")
print("=" * 70)

required_sections = [
    "personal_info",
    "headline",
    "summary",
    "skills",
    "projects",
    "education",
    "certifications",
    "achievements",
    "leadership"
]

for section in required_sections:
    test(
        f"Section exists: {section}",
        section in optimized_resume
    )


# ============================================================
# EDUCATION TESTS
# ============================================================

print("\n" + "=" * 70)
print("3. EDUCATION PRESERVATION")
print("=" * 70)

original_education = ORIGINAL_RESUME["education"]
optimized_education = optimized_resume.get("education", [])

test(
    "Education count preserved",
    len(optimized_education) == len(original_education),
    f"Expected {len(original_education)}, got {len(optimized_education)}"
)

for original in original_education:

    degree_found = any(
        item.get("degree") == original["degree"]
        for item in optimized_education
    )

    test(
        f"Degree preserved: {original['degree']}",
        degree_found
    )

    institution_found = any(
        item.get("institution") == original["institution"]
        for item in optimized_education
    )

    test(
        f"Institution preserved: {original['institution']}",
        institution_found
    )

    dates_found = any(
        item.get("dates") == original["dates"]
        for item in optimized_education
    )

    test(
        f"Dates preserved: {original['dates']}",
        dates_found
    )

    gpa_found = any(
        item.get("gpa") == original["gpa"]
        for item in optimized_education
    )

    test(
        f"GPA preserved: {original['gpa']}",
        gpa_found
    )


# ============================================================
# SKILLS TESTS
# ============================================================

print("\n" + "=" * 70)
print("4. TECHNICAL SKILLS PRESERVATION")
print("=" * 70)

original_skills = ORIGINAL_RESUME["skills"]
optimized_skills = optimized_resume.get("skills", {})

for category, original_items in original_skills.items():

    category_exists = category in optimized_skills

    test(
        f"Skill category preserved: {category}",
        category_exists
    )

    if not category_exists:
        continue

    optimized_items = optimized_skills.get(category, [])

    for skill in original_items:

        skill_found = skill.lower() in [
            str(x).lower()
            for x in optimized_items
        ]

        test(
            f"Skill preserved: {category} → {skill}",
            skill_found
        )


# ============================================================
# DETECT INVENTED SKILLS
# ============================================================

print("\n" + "=" * 70)
print("5. INVENTED SKILL DETECTION")
print("=" * 70)

original_skill_set = set()

for items in original_skills.values():
    for skill in items:
        original_skill_set.add(skill.lower())

invented_skills = []

for category, items in optimized_skills.items():

    for skill in items:

        if str(skill).lower() not in original_skill_set:

            # Ignore obvious formatting variants only if the
            # original skill exists as a substring.
            normalized = str(skill).lower().strip()

            if not any(
                normalized == original
                for original in original_skill_set
            ):
                invented_skills.append(
                    f"{category}: {skill}"
                )

test(
    "No new/invented technical skills",
    len(invented_skills) == 0,
    f"Potentially invented skills: {invented_skills}"
)


# ============================================================
# PROJECT TESTS
# ============================================================

print("\n" + "=" * 70)
print("6. PROJECT PRESERVATION")
print("=" * 70)

original_projects = ORIGINAL_RESUME["projects"]
optimized_projects = optimized_resume.get("projects", [])

test(
    "Project count preserved",
    len(optimized_projects) == len(original_projects),
    f"Expected {len(original_projects)}, got {len(optimized_projects)}"
)

for original in original_projects:

    project_found = any(
        item.get("name") == original["name"]
        for item in optimized_projects
    )

    test(
        f"Project preserved: {original['name']}",
        project_found
    )

    matching_project = next(
        (
            item for item in optimized_projects
            if item.get("name") == original["name"]
        ),
        None
    )

    if matching_project:

        optimized_technologies = [
            str(x).lower()
            for x in matching_project.get("technologies", [])
        ]

        for technology in original["technologies"]:

            test(
                f"Technology preserved: {original['name']} → {technology}",
                technology.lower() in optimized_technologies
            )


# ============================================================
# CERTIFICATION TESTS
# ============================================================

print("\n" + "=" * 70)
print("7. CERTIFICATION PRESERVATION")
print("=" * 70)

original_certifications = ORIGINAL_RESUME["certifications"]
optimized_certifications = optimized_resume.get("certifications", [])

for certification in original_certifications:

    found = certification in optimized_certifications

    test(
        f"Certification preserved: {certification}",
        found
    )


# ============================================================
# ACHIEVEMENT TESTS
# ============================================================

print("\n" + "=" * 70)
print("8. ACHIEVEMENT PRESERVATION")
print("=" * 70)

original_achievements = ORIGINAL_RESUME["achievements"]
optimized_achievements = optimized_resume.get("achievements", [])

for achievement in original_achievements:

    found = achievement in optimized_achievements

    test(
        "Achievement preserved",
        found,
        achievement
    )


# ============================================================
# LEADERSHIP TESTS
# ============================================================

print("\n" + "=" * 70)
print("9. LEADERSHIP PRESERVATION")
print("=" * 70)

original_leadership = ORIGINAL_RESUME["leadership"]
optimized_leadership = optimized_resume.get("leadership", [])

for leadership in original_leadership:

    found = leadership in optimized_leadership

    test(
        "Leadership entry preserved",
        found,
        leadership
    )


# ============================================================
# SECTION SEPARATION TEST
# ============================================================

print("\n" + "=" * 70)
print("10. SECTION SEPARATION")
print("=" * 70)

for achievement in original_achievements:

    in_certifications = achievement in optimized_certifications

    test(
        "Achievement not moved into Certifications",
        not in_certifications,
        achievement
    )

for leadership in original_leadership:

    in_certifications = leadership in optimized_certifications

    test(
        "Leadership not moved into Certifications",
        not in_certifications,
        leadership
    )


# ============================================================
# FACTUAL FIELD TESTS
# ============================================================

print("\n" + "=" * 70)
print("11. CRITICAL FACTUAL DATA")
print("=" * 70)

critical_values = [
    ("MCA GPA", "8.71"),
    ("BCA GPA", "8.6"),
    ("MCA dates", "2025–2027"),
    ("BCA dates", "2022–2025"),
    ("MCA institution", "School of Computer Studies, Sri Balaji University, Pune"),
    ("BCA institution", "Alard College of Business Studies, Pune"),
]

optimized_text = json.dumps(
    optimized_resume,
    ensure_ascii=False
)

for name, value in critical_values:

    test(
        f"{name} preserved",
        value in optimized_text,
        f"Missing value: {value}"
    )


# ============================================================
# FINAL REPORT
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST RESULT")
print("=" * 70)

print(f"\nPASSED : {passed}")
print(f"FAILED : {failed}")

if failed == 0:

    print("\nOVERALL RESULT: PASS")
    print("Gemini preserved the tested resume structure and facts.")

else:

    print("\nOVERALL RESULT: FAIL")
    print("Gemini changed or removed one or more protected resume elements.")

print("\nFull Gemini output:")
print(OUTPUT_FILE)