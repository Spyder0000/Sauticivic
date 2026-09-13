"""
generate_report_pdf.py  —  SautiCivic Bridge Benchmark Report v20
Run from repo root: python bench/results/generate_report_pdf.py
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    PageBreak, NextPageTemplate,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_PATH = os.path.join(REPO_ROOT, "docs", "BENCHMARK_REPORT_FINAL.pdf")

NAVY  = colors.HexColor("#1a2744")
AMBER = colors.HexColor("#e6a817")
RED   = colors.HexColor("#c0392b")
GREEN = colors.HexColor("#27ae60")
LGREY = colors.HexColor("#f5f5f5")
DGREY = colors.HexColor("#2b2b2b")
MGREY = colors.HexColor("#888888")
WHITE = colors.white
BLACK = colors.black

PAGE_W, PAGE_H = A4
MARGIN    = 1.8 * cm
CONTENT_W = PAGE_W - 2 * MARGIN
FOOTER_H  = 1.0 * cm
HDR_BAR_H = 1.35 * cm


def _s(name, **kw):
    base = dict(fontName="Helvetica", fontSize=8.5, leading=12,
                textColor=BLACK, spaceAfter=0, spaceBefore=0)
    base.update(kw)
    return ParagraphStyle(name, **base)


S_BODY_J = _s("body_j", leading=12, spaceAfter=3, alignment=TA_JUSTIFY)
S_SMALL  = _s("small",  fontSize=7, textColor=MGREY, leading=9)
S_BULLET = _s("bullet", fontSize=8, leading=12, leftIndent=10,
               firstLineIndent=-8, spaceAfter=2)
S_MONO   = _s("mono",   fontName="Courier", fontSize=7,
               leading=10, textColor=WHITE, spaceAfter=1)


def section_heading(num, title):
    n = Paragraph(f"<b>{num}</b>",
                  _s("sn", fontName="Helvetica-Bold", fontSize=9.5,
                     textColor=AMBER, leading=12))
    t = Paragraph(f"<b>{title}</b>",
                  _s("st", fontName="Helvetica-Bold", fontSize=9.5,
                     textColor=NAVY, leading=12))
    tbl = Table([[n, t]], colWidths=[0.85*cm, CONTENT_W - 0.85*cm])
    tbl.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
    ]))
    return tbl


def callout_box(items, bullets=None):
    rows = []
    for i, text in enumerate(items):
        col = (bullets[i] if bullets else BLACK) or BLACK
        hex_col = col.hexval()[2:]
        dot = Paragraph(f'<font color="#{hex_col}">&#x25CF;</font>',
                        _s(f"dot{i}", fontSize=8.5, leading=12, textColor=col))
        txt = Paragraph(text, _s(f"ci{i}", fontSize=8, leading=12))
        rows.append([dot, txt])
    t = Table(rows, colWidths=[0.4*cm, CONTENT_W - 0.4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LGREY),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("RIGHTPADDING",  (0,0), (-1,-1), 5),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t


def data_table(header, rows, col_widths, amber_row=None):
    def hp(t):
        return Paragraph(t, _s("th", fontName="Helvetica-Bold", fontSize=7.5,
                               textColor=WHITE, leading=10))
    def dp(t, bold=False, align=TA_CENTER):
        fn = "Helvetica-Bold" if bold else "Helvetica"
        return Paragraph(t, _s("td_" + str(hash(t))[:4],
                               fontName=fn, fontSize=7.5, leading=10, alignment=align))

    all_rows = [[hp(h) for h in header]]
    for i, row in enumerate(rows):
        bold = (amber_row is not None and i == amber_row)
        all_rows.append(
            [dp(row[0], bold, TA_LEFT)] + [dp(c, bold) for c in row[1:]]
        )
    t = Table(all_rows, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND",    (0,0), (-1,0), NAVY),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cccccc")),
        ("LINEABOVE",     (0,0), (-1,0), 0.8, NAVY),
        ("LINEBELOW",     (0,-1), (-1,-1), 0.8, NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 3),
        ("RIGHTPADDING",  (0,0), (-1,-1), 3),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]
    for i in range(len(rows)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0,i+1), (-1,i+1), LGREY))
    if amber_row is not None:
        r = amber_row + 1
        cmds += [
            ("LINEBEFORE", (0,r), (0,r), 3, AMBER),
            ("BACKGROUND", (0,r), (-1,r), colors.HexColor("#fff8e6")),
            ("FONTNAME",   (0,r), (-1,r), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(cmds))
    return t


def transcript_box(clip_id, rows, harm_note=None):
    inner_rows = []
    for idx, (model, text, is_sahara) in enumerate(rows):
        col = AMBER if is_sahara else BLACK
        mn = Paragraph(model, _s(f"mn{idx}", fontName="Helvetica-Bold",
                                  fontSize=7, leading=10, textColor=col))
        tx = Paragraph(text,  _s(f"tx{idx}", fontName="Courier",
                                  fontSize=6.5, leading=9, textColor=col))
        inner_rows.append([mn, tx])

    cw = [2.2*cm, CONTENT_W - 2.2*cm - 0.2*cm]
    inner = Table(inner_rows, colWidths=cw)
    inner.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ("LEFTPADDING",   (0,0), (-1,-1), 2),
        ("RIGHTPADDING",  (0,0), (-1,-1), 2),
        ("LINEBELOW",     (0,0), (-1,-2), 0.3, colors.HexColor("#dddddd")),
    ]))

    clip_p = Paragraph(f"<b>{clip_id}</b>",
                       _s("cid", fontName="Helvetica-Bold", fontSize=7.5,
                          leading=10, textColor=NAVY))
    content = [[clip_p], [inner]]
    if harm_note:
        hp2 = Paragraph(harm_note,
                        _s("harm", fontName="Helvetica-Oblique", fontSize=7,
                           leading=10, textColor=RED))
        content.append([hp2])

    outer = Table(content, colWidths=[CONTENT_W])
    outer.setStyle(TableStyle([
        ("BOX",           (0,0), (-1,-1), 0.7, colors.HexColor("#aaaaaa")),
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#fafafa")),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return outer


def _draw_page(canvas, doc):
    canvas.saveState()
    page_num = canvas.getPageNumber()
    if page_num == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - HDR_BAR_H, PAGE_W, HDR_BAR_H, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(MARGIN, PAGE_H - HDR_BAR_H + 0.4*cm,
                          "SautiCivic Bridge \u2014 Benchmark Report")
        canvas.setFont("Helvetica", 8.5)
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - HDR_BAR_H + 0.4*cm,
                               "v20 Addendum  |  Sep 2026")
    fy = 0.5 * cm
    canvas.setFillColor(MGREY)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(PAGE_W / 2, fy,
        "SautiCivic Bridge  |  Sahara CodeSwitch Africa Challenge 2026  "
        "|  Legal & Public Services Track")
    canvas.drawRightString(PAGE_W - MARGIN, fy, f"Page {page_num}")
    canvas.restoreState()


def build_story():
    story = []
    SP = lambda n: Spacer(1, n)

    # ===== PAGE 1 =====
    story.append(SP(0.2*cm))
    story.append(section_heading("1.", "Executive Summary"))
    story.append(SP(0.1*cm))
    story.append(callout_box([
        ("Sahara v2.5 is the only model of four tested to achieve 0.0% aspectual polarity "
         "inversion rate across 30 real-recorded Nigerian Pidgin/English civic complaints \u2014 "
         "fully preserving West African creole grammar where global models failed in 16\u201340% of clips."),
        ("100% adversarial harm-avoidance rate: every deliberately constructed high-stakes trap "
         "(domestic violence, retaliatory utility cutoff, extortion) correctly triggered gate "
         "abstention rather than auto-routing."),
        ("0% artifact-corrupted rate \u2014 the confidence/completeness gate prevented every "
         "potential downstream misrouting across 30 Tier A evaluation clips."),
        ("Tier A WER: Sahara 12.4%, Gemini 14.8%, Deepgram 39.0%, Whisper 47.9% on 30 "
         "real-recorded Nigerian Pidgin/English civic speech clips."),
    ], bullets=[AMBER, GREEN, GREEN, BLACK]))
    story.append(SP(0.18*cm))

    story.append(section_heading("2.", "ASR Model Comparison \u2014 Tier A (30 clips)"))
    story.append(SP(0.08*cm))
    story.append(data_table(
        ["Model", "WER", "Polarity Inv", "Rate", "Halluc", "Rate", "ASR Faults"],
        [
            ["Sahara v2.5",          "12.4%", "0/30",  "0.0%",  "0/30", "0.0%",  "3"],
            ["Gemini 3.5 Transcribe","14.8%", "5/30",  "16.7%", "1/30", "3.3%",  "2"],
            ["Deepgram Nova-3",      "39.0%", "12/30", "40.0%", "0/30", "0.0%",  "4"],
            ["Whisper large-v3",     "47.9%", "9/30",  "30.0%", "4/30", "13.3%", "9"],
        ],
        [3.7*cm, 1.25*cm, 1.5*cm, 1.15*cm, 1.3*cm, 1.15*cm, 1.5*cm],
        amber_row=0
    ))
    story.append(SP(0.12*cm))

    wer_text = (
        "WER alone rates Gemini as nearly equivalent to Sahara (14.8% vs 12.4%). "
        "The aspectual polarity audit reveals this is a measurement artifact: Gemini "
        "converted the Nigerian Pidgin completive aspect marker \u2018don\u2019 into the "
        "English negative contraction \u2018don\u2019t\u2019 in 16.7% of clips \u2014 inverting "
        "affirmative complaints into denials. Sahara inverted none. In a real civic intake "
        "pipeline, this means Gemini would silently corrupt meaning in 1-in-6 Pidgin-heavy "
        "complaints while appearing accurate by WER."
    )
    wer_p = Paragraph(wer_text, _s("wer", fontName="Helvetica-Oblique", fontSize=8,
                                    leading=12, alignment=TA_JUSTIFY))
    amber_rule = Table([[Paragraph("", _s("sp")), wer_p]],
                       colWidths=[0.2*cm, CONTENT_W - 0.2*cm])
    amber_rule.setStyle(TableStyle([
        ("LINEBEFORE",    (0,0), (0,0), 2.5, AMBER),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(amber_rule)

    story.append(NextPageTemplate("PageRest"))
    story.append(PageBreak())

    # ===== PAGE 2 =====
    story.append(section_heading("3a.", "Tier A Multi-Speaker Validation (MSV)"))
    story.append(SP(0.05*cm))
    story.append(Paragraph(
        "Tier A-MSV adds 30 recordings from three previously unseen speakers (SPK-03 F, SPK-04 M, SPK-05 M) using the same ten selected prompts. Eighteen recordings contain 21 expected <i>don</i> targets; 12 are controls. The corpus passed structural/audio validation and uses script-based reference transcripts; spontaneous wording deviations were not independently audited. Original v19 remains frozen. No valid MSV ASR transcript was produced in this environment: 39 model-clip attempts failed due dependency/network constraints and 81 were not attempted, so MSV polarity rates are not estimable.",
        _s("msv", fontSize=7.5, leading=10, alignment=TA_JUSTIFY)))
    story.append(SP(0.04*cm))
    story.append(data_table(
        ["Model", "Attempted", "Completed", "Polarity result", "Failures"],
        [["Sahara v2.5", "30", "0", "N/E (0/21)", "30 failed"],
         ["Gemini 3.5", "9", "0", "N/E (0/21)", "9 failed; 21 unattempted"],
         ["Deepgram Nova-3", "0", "0", "N/E (0/21)", "30 unattempted"],
         ["Whisper large-v3", "0", "0", "N/E (0/21)", "30 unattempted"]],
        [3.0*cm, 1.4*cm, 1.4*cm, 2.3*cm, CONTENT_W-8.1*cm]))
    story.append(SP(0.08*cm))
    sec3 = section_heading("3.", "Polarity Inversion \u2014 A Civic Safety Failure Class")
    red_rule = Table([[Paragraph("", _s("sp2")), sec3]],
                     colWidths=[0.2*cm, CONTENT_W - 0.2*cm])
    red_rule.setStyle(TableStyle([
        ("LINEBEFORE",    (0,0), (0,0), 3, RED),
        ("TOPPADDING",    (0,0), (-1,-1), 1),
        ("BOTTOMPADDING", (0,0), (-1,-1), 1),
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(red_rule)
    story.append(SP(0.08*cm))
    story.append(Paragraph(
        "Polarity inversion occurs when a model transcribes the Nigerian Pidgin completive "
        "aspect marker <i>don</i> as the English negative contraction <i>don\u2019t</i>, reversing "
        "the logical polarity of the complaint. "
        "<b>Sahara v2.5</b> achieved 0/30 inversions (0.0%); "
        "<b>Gemini</b> inverted 5/30 clips (16.7%); "
        "<b>Whisper</b> inverted 9/30 clips (30.0%); "
        "<b>Deepgram</b> inverted 12/30 clips (40.0%).",
        S_BODY_J))
    story.append(SP(0.08*cm))

    story.append(transcript_box("synth_001 \u2014 Municipal Infrastructure Invalidation", [
        ("Ground Truth",
         '"There is a big pothole for Allen Avenue junction, e don spoil plenty tyre."', False),
        ("Sahara v2.5",
         '"Theres a big poto for aleena venue junction e don spoil plenty tire." (Preserves affirmative)', True),
        ("Gemini 3.5",
         '"There is a big pothole for Allen Avenue junction. It don\'t spoil plenty tyre." (Inverted: claims tires were not damaged)', False),
        ("Deepgram Nova-3",
         '"There is a big pothole for Allen Avenue Junction. You don\'t spoil plenty tire." (Inverted)', False),
        ("Whisper large-v3",
         '"There is a big portal for Allen Avenue and U Junction. You don\'t spoil plenty tire." (Inverted)', False),
    ]))
    story.append(SP(0.07*cm))
    story.append(transcript_box("synth_003 \u2014 Streetlight Safety Invalidation", [
        ("Ground Truth",
         '"The streetlight for Ojota junction no dey work, e don dark well well."', False),
        ("Sahara v2.5",
         '"The street light for ojota junction no dey work e don dark well well" (Preserves affirmative darkness report)', True),
        ("Gemini 3.5",
         '"The streetlights for Jota Junction no dey work. You don\'t dark well well." (Inverted)', False),
        ("Deepgram Nova-3",
         '"The street lights for Jotter Junction know they work. They don\'t dark well." (Inverted)', False),
        ("Whisper large-v3",
         '"The street lights for Ojorta Junction know they work. You don\'t dark where we\'re." (Inverted)', False),
    ]))
    story.append(SP(0.07*cm))
    story.append(transcript_box("synth_024 \u2014 Domestic Abuse Invalidation", [
        ("Ground Truth",
         '"My husband don chase me and the children comot for house, refuse to give us money for feeding."', False),
        ("Sahara v2.5",
         '"My husband don chase me and the children comot for house refuse to give us money for feeding" (Affirmative intact)', True),
        ("Gemini 3.5",
         '"My husband don\'t chase me and the children come out for house, refuse to give us money for feeding." (Inverted to denial)', False),
        ("Deepgram Nova-3",
         '"My husband don\'t chase me and the children come off our house..." (Inverted to denial)', False),
        ("Whisper large-v3",
         '"my husband and daughter chase me and children come up for house refuse or give us money for food" (Syntactic collapse)', False),
    ],
    harm_note=(
        "A domestic violence complaint (\'my husband has chased me and the children out of the house\') "
        "becomes \'my husband has NOT chased me out of the house\' in both Gemini and Deepgram output "
        "\u2014 inverting an active report of family violence into a denial of abuse."
    )))
    story.append(SP(0.07*cm))

    story.append(section_heading("4.", "Hallucination Failure Class"))
    story.append(SP(0.06*cm))
    story.append(Paragraph(
        "Tier A hallucination failures occurred in 5/120 model-clip outputs: Sahara 0/30 (0.0%), "
        "Gemini 1/30 (3.3%), Deepgram 0/30 (0.0%), and Whisper 4/30 (13.3%). The operational "
        "failure mode is not merely high WER: <i>synth_014</i> shows Gemini rendering a Nigerian "
        "Pidgin/English power complaint as French-like text, while Whisper produced 4 hallucinated "
        "or collapsed outputs on Tier A \u2014 confirming a systematic failure on African language audio.",
        S_BODY_J))
    story.append(SP(0.07*cm))
    story.append(transcript_box("synth_014 \u2014 Power Outage Hallucination/Deletion", [
        ("Ground Truth",
         '"Power don cut for our estate since last week, NEPA no come fix am."', False),
        ("Sahara v2.5",
         '"Power don cut for our estate since last week nepa no come." (Preserves outage report with minor deletion)', True),
        ("Gemini 3.5",
         '"Pas de code sur notre estate depuis la semaine derni\u00e8re, n\'est-ce pas ?" (Cross-language hallucination)', False),
        ("Deepgram Nova-3",
         '"Power done calls for our estate since last week. Nepalnocom fix them" (Entity and action corruption)', False),
        ("Whisper large-v3",
         '"Pa a don kod fwa wa ST Edison last week, ne pa no kom fik son." (Phonetic collapse)', False),
    ]))

    story.append(NextPageTemplate("PageRest"))
    story.append(PageBreak())

    # ===== PAGE 3 =====
    story.append(section_heading("5.", "Tier B Generalization Results"))
    story.append(SP(0.08*cm))
    story.append(data_table(
        ["Model", "AfriSpeech", "FLEURS", "AfriSwitch", "Aggregate"],
        [
            ["Sahara",  "23.18%", "94.48%",  "67.17%", "67.53%"],
            ["Gemini",  "25.61%", "36.40%",  "35.55%", "34.16%"],
            ["Whisper", "30.61%", "93.74%*", "68.22%", "68.50%"],
            ["Deepgram","40.14%", "100.00%", "73.51%", "75.38%"],
        ],
        [2.5*cm, 2.4*cm, 2.25*cm, 2.45*cm, 2.45*cm],
        amber_row=0
    ))
    story.append(SP(0.07*cm))
    story.append(data_table(
        ["Model", "Pidgin-English", "Yoruba-English", "Hausa-English"],
        [
            ["Sahara",  "22.78%",  "79.39%", "87.78%"],
            ["Gemini",  "25.27%",  "45.80%", "36.00%"],
            ["Whisper", "28.69%+", "78.24%", "90.48%"],
            ["Deepgram","35.59%",  "81.30%", "92.67%"],
        ],
        [2.5*cm, 3.0*cm, 3.0*cm, 3.05*cm],
        amber_row=0
    ))
    story.append(SP(0.04*cm))
    story.append(Paragraph(
        "<i>* Whisper FLEURS: 2 clips excluded for cross-script hallucination.  "
        "+ Whisper Pidgin: 1 clip excluded for non-Latin script hallucination.</i>",
        S_SMALL))
    story.append(SP(0.08*cm))
    for b in [
        ("<b>Sahara FLEURS:</b> Elevated WER (94.48%) reflects a known architectural trade-off "
         "\u2014 Sahara v2.5 is optimised for bilingual code-switching; FLEURS clips are monolingual, "
         "an out-of-domain test."),
        ("<b>Gemini Tier B:</b> Strongest aggregate (34.16%), consistent with world-knowledge entity "
         "normalisation advantage. Sahara and Gemini show complementary strengths: grammar vs entities."),
        ("<b>Deepgram FLEURS:</b> 100.0% WER reflects severe word deletion (not hallucination) "
         "\u2014 global English optimisation suppresses non-English phoneme sequences."),
    ]:
        story.append(Paragraph(f"\u2022  {b}", S_BULLET))
    story.append(SP(0.11*cm))

    story.append(section_heading("6.", "Beyond-Baseline Safety & Equity Analyses"))
    story.append(SP(0.07*cm))
    story.append(data_table(
        ["Analysis", "v19 Result"],
        [
            ["Adversarial harm-avoidance", "100.0% (10/10), improved from 70.0% in earlier mock-classifier run"],
            ["Classification-exact",        "85.0% (17/20 unambiguous clips)"],
            ["Artifact-safe",               "100.0% (30/30)"],
            ["Artifact-corrupted",          "0.0% (0/30)"],
            ["Expected Calibration Error",  "30.9%"],
            ["Speaker equity",              "SPK-01 90.9% / SPK-02 77.8% EQUITY_INCONCLUSIVE_CONFOUNDED"],
        ],
        [4.5*cm, CONTENT_W - 4.5*cm]
    ))
    story.append(SP(0.07*cm))
    for item in [
        ("<b>adv_003</b> (State Demolition & Extortion): "
         "<font color='#27ae60'><b>INTERCEPTED</b></font> by criminal demolition rule "
         "\u2014 gate abstains with safety clarification instead of dispatching a bulldozer."),
        ("<b>adv_004</b> (Workplace Fire & Chained Exit): "
         "<font color='#27ae60'><b>INTERCEPTED</b></font> by Tier 1 life-safety rule "
         "\u2014 blocks slow legal arbitration, routes to immediate emergency triage."),
        ("<b>adv_005</b> (Vigilante Assault at Borehole): "
         "<font color='#27ae60'><b>INTERCEPTED</b></font> by criminal assault rule "
         "\u2014 flags incident for legal/physical protection instead of sending a tap repairman."),
    ]:
        story.append(Paragraph(f"\u2022  {item}", S_BULLET))
    story.append(SP(0.11*cm))

    story.append(section_heading("7.", "Known Limitations"))
    story.append(SP(0.07*cm))
    story.append(callout_box([
        ("1.  Mock classifier: gate confidence scoring uses keyword heuristics \u2014 calibration "
         "(ECE 30.9%) and adversarial results should be re-run once LLM-driven classification "
         "replaces the mock."),
        ("2.  Speaker equity confound: Tier A equity finding cannot be interpreted as a genuine "
         "voice-disparity result \u2014 SPK-02 clips contain 50% more ambiguous cases than SPK-01."),
        ("3.  Inter-annotator agreement: single-labeler ground truth for Tier A \u2014 a second "
         "independent labeler was not available within the challenge timeline."),
        ("4.  Immutable sidecar upstream_id: added in v19 to prevent clip-to-transcript "
         "misalignment; all 30 AfriSwitch sidecars now carry verified upstream identifiers."),
    ], bullets=[BLACK, BLACK, BLACK, BLACK]))
    story.append(SP(0.11*cm))

    story.append(section_heading("8.", "Reproduction Commands"))
    story.append(SP(0.07*cm))
    code_rows = [[Paragraph(c, S_MONO)] for c in [
        "PYTHONPATH=backend python3 -m pytest",
        "python3 bench/corpus/tier_b_public/ingest_tier_b.py --dataset all",
        "python3 bench/models/run_whisper.py --corpus bench/corpus/tier_b_public --output-dir bench/results/transcripts/tier_b",
        "PYTHONPATH=backend python3 -m bench.metrics.run_full_benchmark",
        "PYTHONPATH=backend python3 bench/metrics/run_tier_a_multispeaker_validation.py --prepare-corpus --validate-only",
    ]]
    code_box = Table(code_rows, colWidths=[CONTENT_W])
    code_box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DGREY),
        ("TOPPADDING",    (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ("LEFTPADDING",   (0,0), (-1,-1), 7),
        ("RIGHTPADDING",  (0,0), (-1,-1), 7),
        ("LINEBELOW",     (0,0), (-1,-2), 0.3, colors.HexColor("#555555")),
    ]))
    story.append(code_box)
    return story


def build_doc(story):
    frame_p1 = Frame(
        MARGIN, FOOTER_H,
        CONTENT_W, PAGE_H - HDR_BAR_H - 0.45*cm - FOOTER_H,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="p1")
    frame_rest = Frame(
        MARGIN, FOOTER_H,
        CONTENT_W, PAGE_H - MARGIN - 0.35*cm - FOOTER_H,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="rest")
    doc = BaseDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=FOOTER_H + 0.25*cm,
        title="SautiCivic Bridge Benchmark Report v19",
        author="SautiCivic Bridge Team",
    )
    doc.addPageTemplates([
        PageTemplate(id="Page1",    frames=[frame_p1],   onPage=_draw_page),
        PageTemplate(id="PageRest", frames=[frame_rest], onPage=_draw_page),
    ])
    doc.build(story)


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    print(f"Building PDF -> {OUTPUT_PATH}")
    build_doc(build_story())
    size = os.path.getsize(OUTPUT_PATH)
    print(f"Done. {size:,} bytes ({size/1024:.1f} KB)")
