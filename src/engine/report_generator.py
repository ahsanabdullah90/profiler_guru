import html
import io
import os
import re
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use('Agg')


import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

# ReportLab imports
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.utils.config import config
from src.utils.logger import logger
from src.utils.markdown import filter_month_files, parse_message_blocks



def analyze_sentiment_keyword(blocks: list[str]) -> float:
    """Negation-aware keyword sentiment analysis for English & Urdu bilingual messages.
    Returns a score between -1.0 (negative) and 1.0 (positive).
    Shares word lists and negation logic between assessment and chart generation.
    """
    pos_words = {"good", "great", "awesome", "happy", "love", "nice", "best", "thanks", "thank",
                 "sweet", "perfect", "amazing", "glad", "haha", "hahaha", "accha", "acha",
                 "sahi", "khush", "shukriya", "pyar", "muhabbat", "zabardast", "umdah", "khoob", "yara"}
    neg_words = {"bad", "sad", "angry", "hate", "sorry", "worst", "broken", "hurt", "annoyed",
                 "wrong", "difficult", "boring", "disappointed", "afsos", "gussa", "nafrat",
                 "kharab", "bura", "rula", "pareshan", "ro", "rona"}
    negations = {"not", "no", "never", "nahi", "na", "ghair", "bin", "nhi", "nahin"}

    total_score = 0.0
    block_count = 0

    for block in blocks:
        content_lower = block.lower()
        words = re.findall(r'\b\w+\b', content_lower)
        pos_count = 0
        neg_count = 0

        for i, w in enumerate(words):
            if w in pos_words:
                negated = False
                for check_idx in range(max(0, i - 2), i):
                    if words[check_idx] in negations:
                        negated = True
                        break
                if negated:
                    neg_count += 1
                else:
                    pos_count += 1
            elif w in neg_words:
                negated = False
                for check_idx in range(max(0, i - 2), i):
                    if words[check_idx] in negations:
                        negated = True
                        break
                if negated:
                    pos_count += 1
                else:
                    neg_count += 1

        total_sentiment_words = pos_count + neg_count
        if total_sentiment_words > 0:
            total_score += (pos_count - neg_count) / total_sentiment_words
            block_count += 1

    return total_score / block_count if block_count > 0 else 0.0


def analyze_monthly_data(chat_name: str, start_month: str | None = None, end_month: str | None = None):
    """Retrieves message counts and estimates bilingual sentiment scores for each month."""
    chats_dir = Path(config.CHATS_DIR) / chat_name / "Chats"
    if not chats_dir.exists():
        return [], [], []

    md_files = sorted([f for f in os.listdir(chats_dir) if f.endswith(".md")])

    months = []
    message_counts = []
    sentiment_scores = []

    for file in filter_month_files(md_files, start_month, end_month):
        month_key = file[:-3]

        file_path = chats_dir / file
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Count messages by separator
            msg_count = content.count("---")

            # Keyword-based sentiment analysis (bilingual English & Urdu)
            blocks = parse_message_blocks(content)
            sentiment = analyze_sentiment_keyword(blocks)

            months.append(month_key.replace("_", "-"))
            message_counts.append(msg_count)
            sentiment_scores.append(sentiment)
        except Exception as e:
            logger.error(f"Failed to analyze month {file}: {e}")

    return months, message_counts, sentiment_scores

def generate_score_chart(scores: dict, framework_id: str, classification: str | None = None) -> bytes | None:
    """Generates a framework-specific score chart as a PNG bytes buffer.

    - big_five: radar chart
    - communication_style / emotional_intelligence: horizontal bar chart
    - attachment: horizontal bar chart + classification label
    """
    if not scores:
        return None

    framework_labels = {
        "big_five": ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"],
        "communication_style": ["Directness", "Expressiveness", "Responsiveness", "Formality", "Conflict Style"],
        "emotional_intelligence": ["Self-awareness", "Self-regulation", "Motivation", "Empathy", "Social Skills"],
        "attachment": ["Secure", "Anxious", "Avoidant", "Disorganized"],
    }

    labels = framework_labels.get(framework_id)
    if not labels:
        return None

    # Map labels to score keys (label -> score_key: "Self-awareness" -> "self_awareness")
    def label_to_key(label: str) -> str:
        return label.lower().replace(" ", "_").replace("-", "_")

    values = [scores.get(label_to_key(label), 0) for label in labels]

    if framework_id == "big_five":
        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={"polar": True})
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values_closed = values + [values[0]]
        angles_closed = angles + [angles[0]]

        ax.fill(angles_closed, values_closed, alpha=0.15, color='#007AFF')
        ax.plot(angles_closed, values_closed, color='#007AFF', linewidth=2)
        ax.set_xticks(angles)
        ax.set_xticklabels([label[:4] for label in labels], fontsize=8, color='#333333')
        ax.set_ylim(0, 10)
        ax.set_yticks([2, 4, 6, 8, 10])
        ax.set_yticklabels(['2', '4', '6', '8', '10'], fontsize=7, color='#999999')
        ax.set_title('Big Five / OCEAN Profile', fontsize=11, fontweight='bold', color='#333333', pad=20)
        plt.tight_layout()
    else:
        # Horizontal bar chart
        fig, ax = plt.subplots(figsize=(6, 3))
        colors_bar = ['#007AFF', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']
        bars = ax.barh(labels, values, color=colors_bar[:len(labels)], edgecolor='none', height=0.5)
        ax.set_xlim(0, 10)
        ax.set_xlabel('Score (1-10)', fontsize=8, color='#666666')
        ax.tick_params(axis='y', labelsize=8, colors='#333333')
        ax.tick_params(axis='x', labelsize=8, colors='#666666')
        for spine in ['top', 'right']:
            ax.spines[spine].set_visible(False)
        for spine in ['left', 'bottom']:
            ax.spines[spine].set_color('#cccccc')
        ax.grid(axis='x', linestyle='--', alpha=0.3)
        # Show values on bars
        for bar, val in zip(bars, values, strict=False):
            ax.text(val + 0.2, bar.get_y() + bar.get_height() / 2, str(val),
                    va='center', fontsize=8, color='#333333', fontweight='bold')

        title = framework_id.replace('_', ' ').title()
        if classification:
            title += f"  |  Classification: {classification}"
        ax.set_title(title, fontsize=10, fontweight='bold', color='#333333', pad=10)
        plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def generate_charts(months, message_counts, sentiment_scores):
    """Generates message frequency and sentiment trend charts as BytesIO PNGs."""
    if not months:
        return None, None

    # 1. Message Frequency per Month (Bar Chart)
    fig_freq, ax_freq = plt.subplots(figsize=(6, 3))
    ax_freq.bar(months, message_counts, color='#007AFF', alpha=0.8, edgecolor='none', width=0.4)
    ax_freq.set_title('Message Frequency per Month', fontsize=10, fontweight='bold', color='#333333', pad=10)
    ax_freq.set_xlabel('Month', fontsize=8, color='#666666')
    ax_freq.set_ylabel('Messages', fontsize=8, color='#666666')
    ax_freq.tick_params(axis='both', labelsize=8, colors='#666666')
    for spine in ['top', 'right']:
        ax_freq.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax_freq.spines[spine].set_color('#cccccc')
    ax_freq.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

    buf_freq = io.BytesIO()
    fig_freq.savefig(buf_freq, format='png', dpi=150, bbox_inches='tight')
    buf_freq.seek(0)
    plt.close(fig_freq)

    # 2. Sentiment over Time (Line Plot)
    fig_sent, ax_sent = plt.subplots(figsize=(6, 3))
    ax_sent.plot(months, sentiment_scores, color='#32D74B', marker='o', linewidth=2, markersize=5)
    ax_sent.axhline(0, color='#cccccc', linestyle='--', linewidth=0.8)
    ax_sent.set_title('Sentiment Trend over Time', fontsize=10, fontweight='bold', color='#333333', pad=10)
    ax_sent.set_xlabel('Month', fontsize=8, color='#666666')
    ax_sent.set_ylabel('Sentiment Score (-1 to +1)', fontsize=8, color='#666666')
    ax_sent.set_ylim(-1.1, 1.1)
    ax_sent.tick_params(axis='both', labelsize=8, colors='#666666')
    for spine in ['top', 'right']:
        ax_sent.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax_sent.spines[spine].set_color('#cccccc')
    ax_sent.grid(True, linestyle='--', alpha=0.3)
    plt.tight_layout()

    buf_sent = io.BytesIO()
    fig_sent.savefig(buf_sent, format='png', dpi=150, bbox_inches='tight')
    buf_sent.seek(0)
    plt.close(fig_sent)

    return buf_freq, buf_sent

def extract_raw_snippets_for_report(chat_name: str, start_month: str | None = None, end_month: str | None = None, max_snippets: int = 10) -> list:
    """Extracts the latest N message snippets from the monthly logs within range."""
    chats_dir = Path(config.CHATS_DIR) / chat_name / "Chats"
    if not chats_dir.exists():
        return []

    md_files = sorted([f for f in os.listdir(chats_dir) if f.endswith(".md")])
    all_blocks = []

    for file in filter_month_files(md_files, start_month, end_month):

        file_path = chats_dir / file
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            blocks = parse_message_blocks(content)
            all_blocks.extend(blocks)
        except Exception as e:
            logger.error(f"Failed to read snippets from {file}: {e}")

    return all_blocks[-max_snippets:]

def parse_markdown_to_story(text: str, styles) -> list:
    """Parses basic markdown features to ReportLab Paragraph flowables.
    Lines are XML-escaped before markdown tag substitution to prevent
    ReportLab's Paragraph parser from crashing on raw < / > characters.

    Supported features: headings (#/##/###), bold, italic, inline code,
    bullet lists (*/-), numbered lists (1.), and tables (| col | col |).
    """
    story = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]
        line_strip = line.strip()

        # Skip separator lines inside tables (| --- | --- |)
        if re.match(r'^\|[\s\-:]+\|$', line_strip):
            i += 1
            continue

        if not line_strip:
            story.append(Spacer(1, 6))
            i += 1
            continue

        # Detect markdown table (line starts with |)
        if line_strip.startswith("|"):
            table_rows = []
            # Collect all consecutive table lines
            while i < len(lines) and lines[i].strip().startswith("|"):
                row_text = lines[i].strip()
                # Skip separator rows (| --- | --- |)
                if not re.match(r'^\|[\s\-:]+\|$', row_text):
                    cells = [c.strip() for c in row_text.split("|")[1:-1]]
                    table_rows.append(cells)
                i += 1

            if table_rows:
                # Build ReportLab Table with header row styled differently
                from reportlab.lib import colors
                header_style = ParagraphStyle('TableHeader', parent=styles['CustomNormal'], textColor=colors.white, fontSize=8, leading=10, alignment=1)
                body_style = ParagraphStyle('TableBody', parent=styles['CustomNormal'], fontSize=7.5, leading=9)
                col_count = max(len(r) for r in table_rows)
                col_width = 460 / col_count  # 460pt available width

                table_data = []
                for row_idx, row_cells in enumerate(table_rows):
                    style = header_style if row_idx == 0 else body_style
                    row_paras = [Paragraph(html.escape(c), style) for c in row_cells]
                    # Pad to col_count
                    while len(row_paras) < col_count:
                        row_paras.append(Paragraph("", body_style))
                    table_data.append(row_paras)

                tbl = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
                tbl_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#007AFF')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ])
                tbl.setStyle(tbl_style)
                story.append(tbl)
                story.append(Spacer(1, 8))
            continue

        # Step 1: XML-escape the raw line
        escaped = html.escape(line)

        # Step 2: Re-apply intentional markdown → safe HTML tag replacements
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', escaped)
        cleaned = re.sub(r'\*(.*?)\*', r'<i>\1</i>', cleaned)
        cleaned = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', cleaned)

        # Step 3: Route to appropriate paragraph style
        if line_strip.startswith("# "):
            cleaned = cleaned.replace("# ", "", 1)
            story.append(Paragraph(cleaned, styles['CustomH1']))
            story.append(Spacer(1, 6))
        elif line_strip.startswith("## "):
            cleaned = cleaned.replace("## ", "", 1)
            story.append(Paragraph(cleaned, styles['CustomH2']))
            story.append(Spacer(1, 6))
        elif line_strip.startswith("### "):
            cleaned = cleaned.replace("### ", "", 1)
            story.append(Paragraph(cleaned, styles['CustomH3']))
            story.append(Spacer(1, 4))
        elif line_strip.startswith("- ") or line_strip.startswith("* "):
            bullet_text = cleaned.replace("- ", "", 1).replace("* ", "", 1)
            story.append(Paragraph(f"&bull; {bullet_text}", styles['CustomBullet']))
        elif re.match(r'^\d+\.\s', line_strip):
            numbered_text = cleaned[cleaned.index(' ')+1:] if ' ' in cleaned else cleaned
            story.append(Paragraph(f"{line_strip.split('.')[0]}. {numbered_text}", styles['CustomNormal']))
        else:
            story.append(Paragraph(cleaned, styles['CustomNormal']))

        i += 1

    return story

# ---------------------------------------------------------------------------
# Module-level style cache — built once per process lifetime.
#
# ReportLab's getSampleStyleSheet() returns a *global process-level singleton*.
# Calling styles.add(ParagraphStyle(name='CustomNormal', ...)) inside
# create_assessment_pdf() mutates that singleton permanently.  On the *second*
# call in the same server session every styles.add() raises:
#     KeyError: 'CustomNormal already exists'
#
# Fix: build all ParagraphStyle objects once and store them in a plain dict.
# Internal ReportLab names are prefixed with 'pg_' to be permanently distinct
# from any current or future base-stylesheet names.
# ---------------------------------------------------------------------------
_STYLES_CACHE: "dict | None" = None


def _build_styles() -> dict:
    """Build and return a dict of all custom ParagraphStyles, memoised for the
    lifetime of the Python process.

    Safe to call from multiple threads — the dict is immutable after construction
    and the assignment of ``_STYLES_CACHE`` is atomic in CPython.
    """
    global _STYLES_CACHE
    if _STYLES_CACHE is not None:
        return _STYLES_CACHE

    base = getSampleStyleSheet()

    _STYLES_CACHE = {
        "CustomNormal": ParagraphStyle(
            name="pg_CustomNormal",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
            spaceAfter=8,
        ),
        "CustomH1": ParagraphStyle(
            name="pg_CustomH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#007AFF"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "CustomH2": ParagraphStyle(
            name="pg_CustomH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#32D74B"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "CustomH3": ParagraphStyle(
            name="pg_CustomH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#555555"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "CustomBullet": ParagraphStyle(
            name="pg_CustomBullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4,
        ),
        "SnippetHeader": ParagraphStyle(
            name="pg_SnippetHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#555555"),
        ),
        "SnippetBody": ParagraphStyle(
            name="pg_SnippetBody",
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#222222"),
        ),
        "Disclaimer": ParagraphStyle(
            name="pg_Disclaimer",
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#777777"),
            spaceBefore=15,
            spaceAfter=5,
            alignment=1,  # Centre-aligned
        ),
        # Cover-page one-off styles (previously created inline per call)
        "TopHeader": ParagraphStyle(
            name="pg_TopHeader",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=colors.HexColor("#007AFF"),
            spaceAfter=15,
        ),
        "DocTitle": ParagraphStyle(
            name="pg_DocTitle",
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#111111"),
            spaceAfter=5,
        ),
        "DocMeta": ParagraphStyle(
            name="pg_DocMeta",
            fontName="Helvetica",
            fontSize=9.5,
            textColor=colors.HexColor("#666666"),
            spaceAfter=20,
        ),
    }
    return _STYLES_CACHE


class ReportGenerator:
    def create_assessment_pdf(self, contact: str, start_month: str, end_month: str, content: str, settings: dict, out_path: Path, scores: dict | None = None, framework_id: str | None = None, classification: str | None = None) -> None:
        """Generates a highly polished psychological profiling PDF report using reportlab."""
        # Setup document template
        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )

        # Retrieve the process-level cached styles dict (built once, reused safely
        # across all PDF calls in the same server session — see _build_styles()).
        styles = _build_styles()

        story = []

        # 1. Premium Cover Header — use cached styles (no inline ParagraphStyle construction)
        story.append(Paragraph("Profile_Guru \u2022 Psychological Profile Report", styles["TopHeader"]))

        title_text = f"Personality Assessment: {contact}"
        story.append(Paragraph(title_text, styles["DocTitle"]))

        # Date and Metadata Subtitle
        date_range_str = f"{start_month.replace('_', '-')} to {end_month.replace('_', '-')}" if start_month and end_month else "Full Conversation History"
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_text = f"<b>Analysis Range:</b> {date_range_str} | <b>Generated:</b> {gen_time}"
        story.append(Paragraph(meta_text, styles["DocMeta"]))

        # Horizontal Rule accent
        story.append(Table([[""]], colWidths=[504], rowHeights=[2], style=TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#007AFF")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ])))
        story.append(Spacer(1, 15))

        # Get order of sections from settings
        sections_order = settings.get("report_sections_order", ["textual_profile", "charts", "snippets"])

        for section in sections_order:
            if section == "textual_profile" and settings.get("pdf_include_textual_profile", True):
                # TEXTUAL PROFILE SECTION
                story.append(Paragraph("1. Executive Summary & Psychological Analysis", styles['CustomH1']))
                profile_story = parse_markdown_to_story(content, styles)
                story.extend(profile_story)
                story.append(Spacer(1, 15))

            elif section == "charts" and settings.get("pdf_include_charts", True):
                # CHARTS SECTION — score chart (if available)
                if scores:
                    score_chart_bytes = generate_score_chart(scores, framework_id or "", classification)
                    if score_chart_bytes:
                        score_img = Image(io.BytesIO(score_chart_bytes), width=440, height=280)
                        story.append(Paragraph("2. Score Profile", styles['CustomH1']))
                        story.append(score_img)
                        story.append(Spacer(1, 20))

                story.append(Paragraph("3. Communication Trends & Sentiment Analysis", styles['CustomH1']))
                months, message_counts, sentiment_scores = analyze_monthly_data(contact, start_month, end_month)
                has_charts = False
                if months:
                    buf_freq, buf_sent = generate_charts(months, message_counts, sentiment_scores)
                    if buf_freq and buf_sent:
                        has_charts = True
                        story.append(Paragraph("The following charts display message frequency and estimated emotional sentiment trends over the selected analysis range.", styles['CustomNormal']))

                        # Pack images into a side-by-side or stacked grid table
                        # Extract bytes eagerly so the buffers are not garbage-collected
                        # between Image() construction and the lazy doc.build() read.
                        img_freq = Image(io.BytesIO(buf_freq.getvalue()), width=240, height=120)
                        img_sent = Image(io.BytesIO(buf_sent.getvalue()), width=240, height=120)

                        charts_table = Table([[img_freq, img_sent]], colWidths=[252, 252])
                        charts_table.setStyle(TableStyle([
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                            ('TOPPADDING', (0,0), (-1,-1), 0),
                        ]))

                        story.append(KeepTogether([charts_table]))
                        story.append(Spacer(1, 20))

                if not has_charts:
                    story.append(Paragraph("<i>No communication trend charts generated: Insufficient monthly dialogue volume.</i>", styles['CustomNormal']))
                    story.append(Spacer(1, 15))

            elif section == "snippets" and settings.get("pdf_include_raw_snippets", True):
                # RAW SNIPPETS SECTION
                snippets = extract_raw_snippets_for_report(contact, start_month, end_month)
                if snippets:
                    story.append(Paragraph("3. Representative Conversation Snippets", styles['CustomH1']))
                    story.append(Paragraph("A curated selection of conversation history blocks reflecting the contact's typical communication style and dialectic patterns.", styles['CustomNormal']))

                    table_data = []
                    # Header Row
                    table_data.append([
                        Paragraph("Timestamp & Sender", styles['SnippetHeader']),
                        Paragraph("Conversation Content", styles['SnippetHeader'])
                    ])

                    for _idx, block in enumerate(snippets):
                        lines = block.split('\n')
                        header_line = lines[0].strip() if lines else ""
                        body_text = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

                        # Format header: ### [time_str] sender
                        time_sender = "Unknown"
                        if header_line.startswith("### ["):
                            closing_bracket_idx = header_line.find("]")
                            if closing_bracket_idx != -1:
                                time_str = header_line[5:closing_bracket_idx]
                                sender = header_line[closing_bracket_idx + 2:].strip()
                                time_sender = f"<b>{sender}</b><br/><font color='#777777'>{time_str}</font>"

                        # Limit snippet length
                        if len(body_text) > 300:
                            body_text = body_text[:300] + "..."

                        # Filter out chunk comments from snippets
                        body_text = re.sub(r'<!--.*?-->', '', body_text, flags=re.DOTALL).strip()

                        # Clean body text using html.escape to safely escape &, <, >, ", '
                        body_text = html.escape(body_text).replace("\n", "<br/>")

                        table_data.append([
                            Paragraph(time_sender, styles['SnippetBody']),
                            Paragraph(body_text, styles['SnippetBody'])
                        ])

                    # Create styled table
                    snippet_table = Table(table_data, colWidths=[130, 374])
                    snippet_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (1,0), colors.HexColor("#f5f5f7")),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                        ('TOPPADDING', (0,0), (-1,-1), 8),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e5e5ea")),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
                    ]))

                    story.append(KeepTogether([snippet_table]))
                    story.append(Spacer(1, 15))

        # Footer builder helper (adds page numbers dynamically)
        def add_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor("#888888"))

            # Draw running header
            canvas.drawString(54, 750, f"Personality Assessment: {contact}")
            canvas.setStrokeColor(colors.HexColor("#e5e5ea"))
            canvas.setLineWidth(0.5)
            canvas.line(54, 742, 558, 742)

            # Draw running footer
            page_num = canvas.getPageNumber()
            # Use literal bullet (•) — canvas.drawString() is plain-text, not HTML.
            canvas.drawString(54, 36, "Confidential \u2022 Profile_Guru Report")
            canvas.drawRightString(558, 36, f"Page {page_num}")
            canvas.restoreState()

        # Add Disclaimer at the end of the report
        story.append(Spacer(1, 15))
        story.append(Paragraph("<b>Disclaimer:</b> This report is AI-generated analysis based on text communication patterns. It is not a clinical or diagnostic assessment.", styles['Disclaimer']))

        # Build PDF
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        logger.info(f"Successfully generated PDF report at {out_path}")

report_generator = ReportGenerator()
