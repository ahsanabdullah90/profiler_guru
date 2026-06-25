import os
import re
import io
from pathlib import Path
from datetime import datetime, timezone
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ReportLab imports
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

from src.utils.config import config
from src.utils.logger import logger

def analyze_monthly_data(chat_name: str, start_month: str | None = None, end_month: str | None = None):
    """Retrieves message counts and estimates bilingual sentiment scores for each month."""
    chats_dir = Path(config.CHATS_DIR) / chat_name / "Chats"
    if not chats_dir.exists():
        return [], [], []
        
    md_files = sorted([f for f in os.listdir(chats_dir) if f.endswith(".md")])
    
    months = []
    message_counts = []
    sentiment_scores = []
    
    # English & Urdu bilingual sentiment words
    pos_words = {"good", "great", "awesome", "happy", "love", "nice", "best", "thanks", "thank", 
                 "sweet", "perfect", "amazing", "glad", "haha", "hahaha", "accha", "acha", 
                 "sahi", "khush", "shukriya", "pyar", "muhabbat", "zabardast", "umdah", "khoob", "yara"}
    neg_words = {"bad", "sad", "angry", "hate", "sorry", "worst", "broken", "hurt", "annoyed", 
                 "wrong", "difficult", "boring", "disappointed", "afsos", "gussa", "nafrat", 
                 "kharab", "bura", "rula", "pareshan", "ro", "rona"}
                 
    for file in md_files:
        month_key = file[:-3]  # YYYY_MM
        if start_month and month_key < start_month:
            continue
        if end_month and month_key > end_month:
            continue
            
        file_path = chats_dir / file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Count messages by separator
            msg_count = content.count("---")
            
            # Simple keyword sentiment scoring
            content_lower = content.lower()
            words = re.findall(r'\b\w+\b', content_lower)
            
            pos_count = sum(1 for w in words if w in pos_words)
            neg_count = sum(1 for w in words if w in neg_words)
            
            total_sentiment_words = pos_count + neg_count
            if total_sentiment_words > 0:
                sentiment = (pos_count - neg_count) / total_sentiment_words
            else:
                sentiment = 0.0
                
            months.append(month_key.replace("_", "-"))
            message_counts.append(msg_count)
            sentiment_scores.append(sentiment)
        except Exception as e:
            logger.error(f"Failed to analyze month {file}: {e}")
            
    return months, message_counts, sentiment_scores

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
    
    for file in md_files:
        month_key = file[:-3]
        if start_month and month_key < start_month:
            continue
        if end_month and month_key > end_month:
            continue
            
        file_path = chats_dir / file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            blocks = [b.strip() for b in content.split("---") if b.strip()]
            all_blocks.extend(blocks)
        except Exception as e:
            logger.error(f"Failed to read snippets from {file}: {e}")
            
    return all_blocks[-max_snippets:]

def parse_markdown_to_story(text: str, styles) -> list:
    """Parses basic markdown features to ReportLab Paragraph flowables."""
    story = []
    lines = text.split("\n")
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            story.append(Spacer(1, 6))
            continue
            
        # Clean markdown formatting and convert to HTML tags that ReportLab Paragraph supports (<b>, <i>, etc.)
        cleaned = line
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cleaned)
        cleaned = re.sub(r'\*(.*?)\*', r'<i>\1</i>', cleaned)
        cleaned = re.sub(r'`(.*?)`', r'<font face="Courier">\1</font>', cleaned)
        
        # Heading 1: # Header
        if line_strip.startswith("# "):
            story.append(Paragraph(cleaned.replace("# ", "", 1), styles['CustomH1']))
            story.append(Spacer(1, 6))
        # Heading 2: ## Header
        elif line_strip.startswith("## "):
            story.append(Paragraph(cleaned.replace("## ", "", 1), styles['CustomH2']))
            story.append(Spacer(1, 6))
        # Heading 3: ### Header
        elif line_strip.startswith("### "):
            story.append(Paragraph(cleaned.replace("### ", "", 1), styles['CustomH3']))
            story.append(Spacer(1, 4))
        # Bullet list: - item or * item
        elif line_strip.startswith("- ") or line_strip.startswith("* "):
            bullet_text = cleaned.replace("- ", "", 1).replace("* ", "", 1)
            story.append(Paragraph(f"&bull; {bullet_text}", styles['CustomBullet']))
        # Standard paragraph
        else:
            story.append(Paragraph(cleaned, styles['CustomNormal']))
            
    return story

class ReportGenerator:
    def create_assessment_pdf(self, contact: str, start_month: str, end_month: str, content: str, settings: dict, out_path: Path) -> None:
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
        
        # Setup custom, professional typography stylesheet
        styles = getSampleStyleSheet()
        
        # Modify existing or create unique styles to avoid collision
        styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
            spaceAfter=8
        ))
        
        styles.add(ParagraphStyle(
            name='CustomH1',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#007AFF"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True
        ))
        
        styles.add(ParagraphStyle(
            name='CustomH2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#32D74B"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        ))

        styles.add(ParagraphStyle(
            name='CustomH3',
            parent=styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#555555"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        ))

        styles.add(ParagraphStyle(
            name='CustomBullet',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333"),
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=4
        ))
        
        styles.add(ParagraphStyle(
            name='SnippetHeader',
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#555555")
        ))

        styles.add(ParagraphStyle(
            name='SnippetBody',
            fontName='Helvetica',
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#222222")
        ))
        
        story = []
        
        # 1. Premium Cover Header
        story.append(Paragraph(f"Profile_Guru &bull; Psychological Profile Report", ParagraphStyle(
            name='TopHeader',
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=colors.HexColor("#007AFF"),
            spaceAfter=15
        )))
        
        title_text = f"Personality Assessment: {contact}"
        story.append(Paragraph(title_text, ParagraphStyle(
            name='DocTitle',
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#111111"),
            spaceAfter=5
        )))
        
        # Date and Metadata Subtitle
        date_range_str = f"{start_month.replace('_', '-')} to {end_month.replace('_', '-')}" if start_month and end_month else "Full Conversation History"
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_text = f"<b>Analysis Range:</b> {date_range_str} | <b>Generated:</b> {gen_time}"
        story.append(Paragraph(meta_text, ParagraphStyle(
            name='DocMeta',
            fontName='Helvetica',
            fontSize=9.5,
            textColor=colors.HexColor("#666666"),
            spaceAfter=20
        )))
        
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
                # CHARTS SECTION
                months, message_counts, sentiment_scores = analyze_monthly_data(contact, start_month, end_month)
                if months:
                    buf_freq, buf_sent = generate_charts(months, message_counts, sentiment_scores)
                    if buf_freq and buf_sent:
                        story.append(Paragraph("2. Communication Trends & Sentiment Analysis", styles['CustomH1']))
                        story.append(Paragraph("The following charts display message frequency and estimated emotional sentiment trends over the selected analysis range.", styles['CustomNormal']))
                        
                        # Pack images into a side-by-side or stacked grid table
                        img_freq = Image(buf_freq, width=240, height=120)
                        img_sent = Image(buf_sent, width=240, height=120)
                        
                        charts_table = Table([[img_freq, img_sent]], colWidths=[252, 252])
                        charts_table.setStyle(TableStyle([
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                            ('TOPPADDING', (0,0), (-1,-1), 0),
                        ]))
                        
                        story.append(KeepTogether([charts_table]))
                        story.append(Spacer(1, 20))
                        
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
                    
                    for idx, block in enumerate(snippets):
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
                            
                        # Clean body text
                        body_text = body_text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
                        
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
            canvas.drawString(54, 36, f"Confidential &bull; Profile_Guru Report")
            canvas.drawRightString(558, 36, f"Page {page_num}")
            canvas.restoreState()

        # Build PDF
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        logger.info(f"Successfully generated PDF report at {out_path}")

report_generator = ReportGenerator()
