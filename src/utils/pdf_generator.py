import io
from datetime import datetime
from fpdf import FPDF
try:
    from src.utils.statute_explainer import get_explainer_details
except ImportError:
    try:
        from utils.statute_explainer import get_explainer_details
    except ImportError:
        get_explainer_details = None

class LegalReportPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(100, 110, 120)
        self.cell(0, 10, 'LEGAL INTELLIGENCE PLATFORM - CONFIDENTIAL ANALYSIS BRIEF', 0, 0, 'L')
        self.cell(0, 10, f'GENERATED: {datetime.now().strftime("%Y-%m-%d")}', 0, 1, 'R')
        self.set_draw_color(200, 200, 200)
        self.line(10, 18, 200, 18)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(120, 130, 140)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}} - Strictly for informational and advisory research only.', 0, 0, 'C')

class PDFGenerator:
    """
    Generates a professional PDF report from the legal analysis output.
    """
    
    @staticmethod
    def generate_report(res: dict) -> bytes:
        pdf = LegalReportPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        # Title Section
        pdf.set_font('Helvetica', 'B', 22)
        pdf.set_text_color(26, 54, 93)  # Dark Blue
        pdf.cell(0, 15, 'LEGAL RESEARCH & ANALYSIS REPORT', 0, 1, 'L')
        pdf.ln(2)
        
        # Section 1: FIR Information Table
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 10, '1. FIR METADATA & PROFILE', 0, 1, 'L')
        pdf.ln(1)
        
        # Write metadata fields
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(74, 85, 104)
        
        metadata = [
            ("FIR Number", res.get("fir_number", "N/A")),
            ("Police Station", res.get("police_station", "N/A")),
            ("Location", res.get("location", "N/A")),
            ("Registration Date", res.get("date_of_registration", "Review Required")),
            ("Incident Date", res.get("date_of_incident", "Review Required")),
            ("Complainant", res.get("complainant", "N/A")),
            ("Accused Details", res.get("accused", "N/A")),
            ("Investigating Officer", res.get("officer_details", "Review Required")),
            ("Evidence Submitted", res.get("evidence_submitted", "None noted"))
        ]
        
        for label, val in metadata:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(45, 6, f"{label}:", 0, 0)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, str(val), 0, 1)
            
        pdf.ln(5)
        
        # Section 2: Witnesses
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 10, '2. INVOLVED WITNESSES', 0, 1, 'L')
        pdf.ln(1)
        
        witnesses = res.get("witnesses", [])
        pdf.set_font('Helvetica', '', 10)
        if isinstance(witnesses, list) and witnesses:
            for idx, w in enumerate(witnesses, 1):
                pdf.cell(0, 6, f"  {idx}. {w}", 0, 1)
        else:
            w_str = str(witnesses) if witnesses else "None explicitly listed in FIR"
            pdf.cell(0, 6, f"  {w_str}", 0, 1)
            
        pdf.ln(5)
        
        # Section 3: Legal Risk Assessment Dashboard
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 10, '3. LEGAL RISK PROFILE', 0, 1, 'L')
        pdf.ln(1)
        
        risk = res.get("risk_assessment", {})
        risk_fields = [
            ("Overall Severity Level", risk.get("severity", res.get("risk_level", "Medium"))),
            ("Estimated Financial Risk", risk.get("financial_risk", "Medium")),
            ("Criminal Penalty Exposure", risk.get("criminal_exposure", "Medium")),
            ("Investigation Complexity", risk.get("complexity", "Medium")),
            ("Strength of Collected Evidence", risk.get("evidence_strength", "Medium"))
        ]
        
        for label, val in risk_fields:
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(60, 6, f"{label}:", 0, 0)
            pdf.set_font('Helvetica', 'B', 10)
            # Highlight Critical/High in red, Low in green
            if str(val).upper() in ['CRITICAL', 'HIGH']:
                pdf.set_text_color(197, 48, 48)
            elif str(val).upper() == 'LOW':
                pdf.set_text_color(56, 161, 105)
            else:
                pdf.set_text_color(214, 158, 46)
            pdf.cell(0, 6, str(val).upper(), 0, 1)
            pdf.set_text_color(74, 85, 104)  # Reset
            
        pdf.ln(5)
        
        # Section 4: Timeline of Events
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 10, '4. DOCUMENT TIMELINE', 0, 1, 'L')
        pdf.ln(1)
        
        timeline = res.get("timeline", [])
        pdf.set_font('Helvetica', '', 10)
        if timeline:
            for item in timeline:
                date = item.get("date", "N/A")
                event = item.get("event", "N/A")
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(30, 6, f" {date}:", 0, 0)
                pdf.set_font('Helvetica', '', 10)
                pdf.multi_cell(0, 6, event)
        else:
            pdf.cell(0, 6, "  Timeline details are unavailable or not explicitly cited.", 0, 1)
            
        pdf.ln(5)
        
        # Section 5: Legal Sections Explainer
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 10, '5. LEGAL PROVISIONS EXPLAINER', 0, 1, 'L')
        pdf.ln(1)
        
        sections = res.get("legal_sections", [])
        if not sections:
            sections = res.get("sections", [])
            
        if sections:
            for sec in sections:
                if get_explainer_details:
                    exp = get_explainer_details(sec)
                else:
                    exp = {
                        "name": "N/A",
                        "description": "Explanations Currently Unavailable",
                        "punishment": "N/A",
                        "cognizability": "N/A",
                        "bailability": "N/A"
                    }
                pdf.set_font('Helvetica', 'B', 11)
                pdf.set_text_color(26, 54, 93)
                pdf.cell(0, 6, f"• {sec}: {exp.get('name', 'N/A')}", 0, 1)
                pdf.set_text_color(74, 85, 104)
                
                pdf.set_font('Helvetica', 'I', 9)
                pdf.multi_cell(0, 5, f"Description: {exp.get('description', 'N/A')}")
                pdf.set_font('Helvetica', '', 9)
                pdf.cell(0, 5, f"Punishment: {exp.get('punishment', 'N/A')}", 0, 1)
                pdf.cell(0, 5, f"Cognizability: {exp.get('cognizability', 'N/A')} | Bailability: {exp.get('bailability', 'N/A')}", 0, 1)
                pdf.ln(2)
        else:
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, "  No legal sections extracted.", 0, 1)
            
        pdf.ln(3)
        
        # Section 6: AI Advisory Analysis
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 10, '6. AI RESEARCH SUMMARY & ANALYSIS', 0, 1, 'L')
        pdf.ln(1)
        
        advice = res.get("legal_advice", "")
        pdf.set_font('Helvetica', '', 10)
        # Handle newlines in advice properly
        pdf.multi_cell(0, 6, advice if advice else "Advisory analysis is unavailable.")
        pdf.ln(5)
        
        # Section 7: Precedents
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(45, 55, 72)
        pdf.cell(0, 10, '7. MATCHED CASE PRECEDENTS', 0, 1, 'L')
        pdf.ln(1)
        
        precedents = res.get("precedents", [])
        if precedents:
            pdf.set_font('Helvetica', '', 10)
            for idx, prec in enumerate(precedents, 1):
                case_name = prec.get("case_name", "Unknown Case")
                court = prec.get("court", "Court")
                year = prec.get("year", "Year")
                holding = prec.get("holding", "")
                score = prec.get("similarity_score", 0.0)
                
                pdf.set_font('Helvetica', 'B', 10)
                pdf.cell(0, 6, f"  {idx}. {case_name} ({court}, {year}) [Similarity: {score*100:.1f}%]", 0, 1)
                pdf.set_font('Helvetica', '', 9)
                pdf.multi_cell(0, 5, f"     Holding: {holding}")
                pdf.ln(2)
        else:
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(0, 6, "  No direct matching precedents located in vector database.", 0, 1)
            
        pdf.ln(5)
        
        # Disclaimer
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(110, 120, 130)
        pdf.cell(0, 5, 'DISCLAIMER:', 0, 1, 'L')
        pdf.multi_cell(0, 4, 'This platform provides legal research assistance and informational analysis only. It does not constitute formal legal advice or create an attorney-client relationship. Users should consult a qualified advocate for professional legal guidance.')
        
        # Return bytes
        out_stream = io.BytesIO()
        pdf.output(out_stream)
        return out_stream.getvalue()

    @staticmethod
    def clean_unicode_for_pdf(text: str) -> str:
        """
        Replace or remove characters that are not supported by standard PDF fonts (Latin-1).
        """
        if not text:
            return ""
        # Common unicode replacements
        replacements = {
            '\u2018': "'",  # Left single quote
            '\u2019': "'",  # Right single quote
            '\u201c': '"',  # Left double quote
            '\u201d': '"',  # Right double quote
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u2022': '*',  # Bullet point
            '\u2122': 'TM',
            '\u00a9': '(c)',
            '\u00ae': '(r)',
            '\u20b9': 'Rs.',  # Indian Rupee symbol
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
            
        # Encode to Latin-1, ignoring characters we cannot encode
        return text.encode('latin-1', 'ignore').decode('latin-1')
