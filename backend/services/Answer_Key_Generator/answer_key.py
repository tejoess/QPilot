import json
import os
import tempfile
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT

load_dotenv()

# ── Prompt Builder ────────────────────────────────────────────────────────────

def build_prompt(question_data: dict, syllabus: str = "") -> str:
    question_json = json.dumps(question_data, indent=2)

    syllabus_section = ""
    if syllabus:
        syllabus_section = f"""
Syllabus / Course Objectives (use this for better context):
{syllabus}
"""

    prompt = f"""
You are a strict and experienced university examiner creating an answer key.
{syllabus_section}
Question:
{question_json}

Generate a strict answer key in the following JSON format:
{{
  "sub_question_no": "<e.g. Q1.1>",
  "question": "<question text>",
  "full_marks": <marks>,
  "keywords": ["<keyword1>", "<keyword2>", "<keyword3>"],
  "expected_points": ["<point1>", "<point2>", "<point3>"],
  "marking_scheme": {{
    "full_marks_criteria": "<Exact, strict criteria — list every concept, comparison, step, or explanation required to earn full marks. Be specific, not vague.>",
    "partial_marks": [
      {{ "marks": <marks>, "criteria": "<specific criteria for this partial mark>" }}
    ],
    "deductions": ["<specific reason to cut marks>", "<another reason>"]
  }}
}}

STRICT RULES:
- full_marks_criteria must be detailed and specific — mention exact concepts, terms, or steps needed
- partial_marks must have clear thresholds (e.g. "mentions 2 out of 4 required points")
- deductions must be concrete (e.g. "missing definition", "no example given", "incorrect formula used")
- expected_points: maximum 3 points, each must be a complete, meaningful statement
- keywords: 3 to 5 most important technical terms for this answer
- Return ONLY a valid JSON object. No extra text or markdown.
"""
    return prompt


# ── LangChain OpenAI Call ─────────────────────────────────────────────────────

def call_openai(prompt: str) -> dict:
    from backend.services.llm_service import openai_llm
    from langchain_core.messages import HumanMessage

    response = openai_llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()

    return json.loads(content)


# ── Answer Key Generator ──────────────────────────────────────────────────────

def _normalise_to_questions_list(input_json: dict) -> list:
    """
    The QPilot pipeline produces a *sections-based* format:
        { "sections": [ { "section_name": ..., "questions": [ { "question_text": ..., "marks": ... } ] } ] }

    The original answer_key.py expected a *questions-based* format:
        { "questions": [ { "question_no": ..., "sub_questions": [...] } ] }

    This helper detects which format we have and returns a normalised list of
    question dicts that the generator loop can consume in the same way.
    """
    # ── Sections-based format (pipeline output) ───────────────────────────────
    if "sections" in input_json:
        questions = []
        q_counter = 1
        for section in input_json.get("sections", []):
            section_name = section.get("section_name", "S")
            for q in section.get("questions", []):
                question_text = q.get("question_text") or q.get("text") or q.get("question", "")
                marks = q.get("marks", 0)
                questions.append({
                    "question_no": f"Q{q_counter}",
                    "type": section.get("section_type", ""),
                    "marks_each": marks,
                    "total_marks": marks,
                    # Wrap the single question as one sub_question so the loop
                    # below works without modification.
                    "sub_questions": [{"question": question_text, "marks": marks}],
                })
                q_counter += 1
        return questions

    # ── Original questions-based format ───────────────────────────────────────
    return input_json.get("questions", [])


def generate_answer_key(input_json: dict, syllabus: str = "") -> dict:
    answer_key = []

    questions = _normalise_to_questions_list(input_json)

    for question in questions:
        question_no = question.get("question_no", "Q?")
        marks_each = question.get("marks_each")
        question_type = question.get("type", "")
        sub_questions = question.get("sub_questions", [])

        answer_key_question = {
            "question_no": question_no,
            "type": question_type,
            "sub_questions": []
        }
        if marks_each:
            answer_key_question["marks_each"] = marks_each
        if question.get("total_marks"):
            answer_key_question["total_marks"] = question["total_marks"]

        for idx, sub_q in enumerate(sub_questions, start=1):
            sub_question_no = f"{question_no}.{idx}"

            if isinstance(sub_q, str):
                question_text = sub_q
                marks = marks_each or (question.get("total_marks", 20) // max(len(sub_questions), 1))
                parts = None
            elif isinstance(sub_q, dict):
                question_text = sub_q.get("question", "")
                marks = sub_q.get("marks", marks_each)
                parts = sub_q.get("parts", None)
            else:
                continue

            question_data = {"sub_question_no": sub_question_no, "question": question_text, "marks": marks}
            if parts:
                question_data["parts"] = parts

            print(f"Generating answer key for {sub_question_no}...")
            try:
                prompt = build_prompt(question_data, syllabus)
                answer = call_openai(prompt)
                answer_key_question["sub_questions"].append(answer)
            except Exception as e:
                print(f"Error for {sub_question_no}: {e}")
                answer_key_question["sub_questions"].append({
                    "sub_question_no": sub_question_no,
                    "question": question_text,
                    "error": str(e)
                })

        answer_key.append(answer_key_question)

    return {"answer_key": answer_key}


# ── PDF Generator ─────────────────────────────────────────────────────────────

def safe_text(text):
    if not isinstance(text, str):
        text = str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pdf(answer_key_json: dict, output_path: str = "answer_key.pdf"):
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    # Styles
    DARK   = colors.HexColor("#1a1a2e")
    RED    = colors.HexColor("#e94560")
    LGRAY  = colors.HexColor("#f5f5f5")
    GRAY   = colors.HexColor("#888888")
    BORDER = colors.HexColor("#dddddd")

    title_s    = ParagraphStyle("T",  fontSize=20, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4, textColor=DARK)
    subtitle_s = ParagraphStyle("ST", fontSize=10, fontName="Helvetica", alignment=TA_CENTER, spaceAfter=20, textColor=GRAY)
    qhead_s    = ParagraphStyle("QH", fontSize=12, fontName="Helvetica-Bold", textColor=colors.white, backColor=DARK, leftIndent=8, rightIndent=8, spaceBefore=16, spaceAfter=6, leading=18)
    subq_s     = ParagraphStyle("SQ", fontSize=11, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=2, textColor=DARK)
    qtext_s    = ParagraphStyle("QT", fontSize=9,  fontName="Helvetica-Oblique", spaceAfter=8, textColor=colors.HexColor("#555555"), leftIndent=8)
    label_s    = ParagraphStyle("L",  fontSize=8,  fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3, textColor=RED)
    body_s     = ParagraphStyle("B",  fontSize=9,  fontName="Helvetica", spaceAfter=3, textColor=colors.black, leftIndent=10)
    criteria_s = ParagraphStyle("C",  fontSize=9,  fontName="Helvetica-Bold", spaceAfter=2, textColor=DARK, leftIndent=10)
    tbl_hdr_s  = ParagraphStyle("TH", fontSize=9,  fontName="Helvetica-Bold", textColor=colors.white)
    tbl_body_s = ParagraphStyle("TB", fontSize=9,  fontName="Helvetica", textColor=colors.black)

    PAGE_W = A4[0] - 4*cm  # usable width

    story = []

    # Header
    story.append(Paragraph("Answer Key", title_s))
    story.append(Paragraph("Auto-generated Examination Answer Key", subtitle_s))
    story.append(HRFlowable(width="100%", thickness=2, color=RED, spaceAfter=10))

    for question in answer_key_json.get("answer_key", []):
        q_no        = question.get("question_no", "")
        q_type      = question.get("type", "")
        marks_each  = question.get("marks_each", "")
        total_marks = question.get("total_marks", "")

        header = q_no
        if q_type:      header += f"   |   {q_type}"
        if marks_each:  header += f"   |   {marks_each} Marks Each"
        if total_marks: header += f"   |   Total: {total_marks} Marks"

        story.append(Paragraph(safe_text(header), qhead_s))

        for sub_q in question.get("sub_questions", []):
            sub_no        = sub_q.get("sub_question_no", "")
            full_marks    = sub_q.get("full_marks", "")
            question_text = sub_q.get("question", "")
            keywords      = sub_q.get("keywords", [])
            expected_pts  = sub_q.get("expected_points", [])
            marking       = sub_q.get("marking_scheme", {})
            error         = sub_q.get("error")

            block = []

            # Sub-question title
            block.append(Paragraph(
                safe_text(f"{sub_no}   [{full_marks} Marks]" if full_marks else sub_no),
                subq_s
            ))

            # Question text
            if question_text:
                block.append(Paragraph(safe_text(question_text), qtext_s))

            if error:
                block.append(Paragraph(f"Error: {safe_text(error)}", body_s))
                story.append(KeepTogether(block))
                story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=6, spaceAfter=6))
                continue

            # Keywords row
            if keywords:
                block.append(Paragraph("KEYWORDS", label_s))
                kw_text = "   |   ".join([safe_text(k) for k in keywords])
                block.append(Paragraph(kw_text, ParagraphStyle("KW", fontSize=9, fontName="Helvetica-Bold",
                             textColor=RED, leftIndent=10, spaceAfter=4)))

            # Expected Points
            if expected_pts:
                block.append(Paragraph("EXPECTED POINTS", label_s))
                for i, pt in enumerate(expected_pts[:3], 1):
                    block.append(Paragraph(f"{i}.  {safe_text(pt)}", body_s))

            # Marking Scheme
            if marking:
                block.append(Paragraph("MARKING SCHEME", label_s))

                # Full marks criteria box
                full_criteria = marking.get("full_marks_criteria", "")
                if full_criteria:
                    fc_table = Table(
                        [[Paragraph("<b>Full Marks Criteria</b>", tbl_hdr_s)],
                         [Paragraph(safe_text(full_criteria), tbl_body_s)]],
                        colWidths=[PAGE_W]
                    )
                    fc_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), DARK),
                        ("BACKGROUND", (0, 1), (-1, 1), LGRAY),
                        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
                        ("TEXTCOLOR",  (0, 1), (-1, 1), colors.black),
                        ("BOX",        (0, 0), (-1,-1), 0.5, BORDER),
                        ("TOPPADDING",    (0, 0), (-1,-1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1,-1), 5),
                        ("LEFTPADDING",   (0, 0), (-1,-1), 8),
                    ]))
                    block.append(fc_table)
                    block.append(Spacer(1, 6))

                # Partial marks table
                partial = marking.get("partial_marks", [])
                if partial:
                    rows = [[
                        Paragraph("<b>Marks</b>", tbl_hdr_s),
                        Paragraph("<b>Criteria</b>", tbl_hdr_s)
                    ]]
                    for item in partial:
                        rows.append([
                            Paragraph(str(item.get("marks", "")), tbl_body_s),
                            Paragraph(safe_text(item.get("criteria", "")), tbl_body_s)
                        ])
                    pm_table = Table(rows, colWidths=[1.8*cm, PAGE_W - 1.8*cm])
                    pm_table.setStyle(TableStyle([
                        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
                        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                        ("BACKGROUND",    (0, 1), (-1, -1), colors.white),
                        ("TEXTCOLOR",     (0, 1), (-1, -1), colors.black),
                        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, LGRAY]),
                        ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
                        ("ALIGN",         (0, 0), (0, -1), "CENTER"),
                        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING",    (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                    ]))
                    block.append(pm_table)
                    block.append(Spacer(1, 6))

                # Deductions
                deductions = marking.get("deductions", [])
                if deductions:
                    block.append(Paragraph("DEDUCTIONS", label_s))
                    for d in deductions:
                        block.append(Paragraph(f"- {safe_text(d)}", body_s))

            story.append(KeepTogether(block))
            story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=8, spaceAfter=4))

    doc.build(story)
    print("PDF saved to:", output_path)
    return output_path
