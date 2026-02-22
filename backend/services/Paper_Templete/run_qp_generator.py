import json, sys, re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_JUSTIFY

def safe(text):
    if not isinstance(text, str): text = str(text)
    return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def generate_pdf(meta, questions, output="question_paper.pdf"):
    qMap = {q["qid"]: q["question"] for q in questions}

    # Q1 has 5 sub-questions (qid 1-5)
    # Q2-Q6 each have 2 sub-questions (a, b)
    slots = {
        "Q1a": qMap.get(1,  ""), "Q1b": qMap.get(2,  ""),
        "Q1c": qMap.get(3,  ""), "Q1d": qMap.get(4,  ""),
        "Q1e": qMap.get(5,  ""),
        "Q2a": qMap.get(6,  ""), "Q2b": qMap.get(7,  ""),
        "Q3a": qMap.get(8,  ""), "Q3b": qMap.get(9,  ""),
        "Q4a": qMap.get(10, ""), "Q4b": qMap.get(11, ""),
        "Q5a": qMap.get(12, ""), "Q5b": qMap.get(13, ""),
        "Q6a": qMap.get(14, ""), "Q6b": qMap.get(15, ""),
    }

    doc = SimpleDocTemplate(output, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)

    PAGE_W = A4[0] - 4*cm
    B = "Helvetica-Bold"
    N = "Helvetica"

    COL_Q   = 1.0*cm
    COL_SUB = 0.8*cm
    COL_TXT = PAGE_W - 1.0*cm - 0.8*cm - 1.2*cm
    COL_MRK = 1.2*cm

    hdr_s  = ParagraphStyle("H",  fontSize=13, fontName=B, alignment=TA_CENTER, spaceAfter=3)
    meta_s = ParagraphStyle("M",  fontSize=10, fontName=N, alignment=TA_CENTER, spaceAfter=2)
    nb_s   = ParagraphStyle("NB", fontSize=10, fontName=N, spaceAfter=1, leading=15)
    qt_s   = ParagraphStyle("QT", fontSize=10, fontName=N, leading=15, alignment=TA_JUSTIFY)
    qb_s   = ParagraphStyle("QB", fontSize=10, fontName=B, leading=15)
    mk_s   = ParagraphStyle("MK", fontSize=10, fontName=B, alignment=TA_RIGHT)

    BASE_STYLE = TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ])

    def row(q_label, sub_label, text, marks):
        t = Table([[
            Paragraph(f'<b>{q_label}</b>' if q_label else '', qb_s),
            Paragraph(f'<b>{sub_label}</b>' if sub_label else '', qb_s),
            Paragraph(safe(text), qt_s),
            Paragraph(f'<b>{marks}</b>' if marks else '', mk_s),
        ]], colWidths=[COL_Q, COL_SUB, COL_TXT, COL_MRK])
        t.setStyle(BASE_STYLE)
        return t

    story = [
        Paragraph(f'Paper / Subject Code: {meta["subject_code"]} / {safe(meta["subject_name"])}', hdr_s),
        Spacer(1, 4),
        Paragraph(f'{meta["date"]}  &nbsp;&nbsp;&nbsp;  Duration: {meta["duration"]}  &nbsp;&nbsp;&nbsp;  [Max Marks: {meta["max_marks"]}]', meta_s),
        Paragraph(f'QP CODE: {meta["qp_code"]}', meta_s),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.5, color=colors.black),
        Spacer(1, 8),

        Paragraph('<b>N.B.:</b>  (1) Question No. 1 is Compulsory.', nb_s),
        Paragraph('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(2) Attempt any THREE questions out of the remaining FIVE.', nb_s),
        Paragraph('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(3) All questions carry equal marks.', nb_s),
        Paragraph('&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;(4) Assume suitable data, if required and state it clearly.', nb_s),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1, color=colors.black),
        Spacer(1, 10),

        # Q1 — Attempt any FOUR with 5 sub-questions
        row("Q1.", "", "Attempt any FOUR", "[20]"),
        row("",    "a)", slots["Q1a"], "[05]"),
        row("",    "b)", slots["Q1b"], "[05]"),
        row("",    "c)", slots["Q1c"], "[05]"),
        row("",    "d)", slots["Q1d"], "[05]"),
        row("",    "e)", slots["Q1e"], "[05]"),
        Spacer(1, 10),

        # Q2 - Q6
        *[item for qnum, ka, kb in [
            ("Q2.", "Q2a", "Q2b"), ("Q3.", "Q3a", "Q3b"),
            ("Q4.", "Q4a", "Q4b"), ("Q5.", "Q5a", "Q5b"),
            ("Q6.", "Q6a", "Q6b"),
        ] for item in [
            row(qnum, "a)", slots[ka], "[10]"),
            row("",   "b)", slots[kb], "[10]"),
            Spacer(1, 8),
        ]],

        HRFlowable(width="100%", thickness=1, color=colors.black),
    ]

    doc.build(story)
    print("PDF saved:", output)

if __name__ == "__main__":
    meta_path = sys.argv[1] if len(sys.argv) > 1 else "meta.json"
    q_path    = sys.argv[2] if len(sys.argv) > 2 else "questions.json"
    out       = sys.argv[3] if len(sys.argv) > 3 else "question_paper.pdf"
    with open(meta_path) as f: meta = json.load(f)
    with open(q_path) as f: questions = json.load(f)["questions"]
    generate_pdf(meta, questions, out)