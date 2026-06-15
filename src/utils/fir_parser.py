import re
from typing import Dict, List

class RegexFIRParser:
    """
    Regex-based FIR Parser for extracting structured fields from raw OCR text.
    No LLM is used in this stage.
    """
    
    @staticmethod
    def extract_fir_number(text: str) -> str:
        patterns = [
            r'(?:FIR|F\.I\.R\.|First\s+Information\s+Report)\s*(?:No\.?|Number|No|Code)?\s*[:\-]*\s*([A-Za-z0-9\-\/\\_]+)',
            r'(?:No\.?|Number|No|Code)?\s*[:\-]*\s*\b([0-9]{1,5}\/[0-9]{4})\b',
            r'\b([0-9]{1,5}\/(?:19|20)[0-9]{2})\b'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if '/' in val or val.isdigit():
                    return val
        return "Not found"

    @staticmethod
    def extract_police_station(text: str) -> str:
        patterns = [
            r'(?:Police\s+Station|P\.S\.|PS)\s*(?:\([^\)]+\))?\s*[:\-]+\s*([^\n\r,;]+)',
            r'(?:Police\s+Station|P\.S\.|PS)\s*[:\-]+\s*([^\n\r,;]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                val = re.sub(r'\s{2,}', ' ', val)
                if len(val) > 2:
                    return val
        return "Not found"

    @staticmethod
    def extract_complainant(text: str) -> str:
        patterns = [
            r'(?:Complainant|Informant|Complainant/Informant|Name\s+of\s+Complainant|Name\s+of\s+Informant)\s*(?:Name)?\s*[:\-]+\s*([^\n\r,;]+)',
            r'(?:Complainant|Informant)\s*[:\-]+\s*([^\n\r,;]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                val = re.sub(r'\s{2,}', ' ', val)
                if len(val) > 2 and not any(k in val.lower() for k in ['unknown', 'not found', 'address', 'details']):
                    return val
        return "Not found"

    @staticmethod
    def extract_accused(text: str) -> str:
        patterns = [
            r'(?:Accused|Name\s+of\s+Accused|Details\s+of\s+Accused|Accused\s+Person\(s\))\s*[:\-]+\s*([^\n\r;]+)',
            r'(?:Accused)\s*[:\-]+\s*([^\n\r;]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                val = re.sub(r'\s{2,}', ' ', val)
                if len(val) > 2:
                    return val
        return "Unknown"

    @staticmethod
    def extract_sections(text: str) -> Dict[str, List[str]]:
        ipc_sections = []
        bns_sections = []
        
        lines = text.split('\n')
        for line in lines:
            is_bns = any(k in line.lower() for k in ['bns', 'bharatiya nyaya'])
            is_ipc = any(k in line.lower() for k in ['ipc', 'indian penal']) or not is_bns
            
            matches = re.findall(r'(?:section|sec\.?|u/s|under section)\s*([0-9a-zA-Z,\s&\/\\_]+)', line, re.IGNORECASE)
            for m in matches:
                parts = re.split(r'[,|and|&|\s]+', m)
                for part in parts:
                    part_cleaned = re.sub(r'[^0-9A-Za-z]', '', part).strip()
                    if part_cleaned and part_cleaned[0].isdigit():
                        if is_bns:
                            bns_sections.append(part_cleaned)
                        else:
                            ipc_sections.append(part_cleaned)
                            
        if not ipc_sections and not bns_sections:
            matches_ipc = re.findall(r'\b([0-9]{2,3}[A-Za-z]?)\s*(?:of)?\s*IPC\b', text, re.IGNORECASE)
            ipc_sections.extend(matches_ipc)
            matches_bns = re.findall(r'\b([0-9]{2,3}[A-Za-z]?)\s*(?:of)?\s*BNS\b', text, re.IGNORECASE)
            bns_sections.extend(matches_bns)

        return {
            "ipc_sections": list(dict.fromkeys(ipc_sections)),
            "bns_sections": list(dict.fromkeys(bns_sections))
        }

    @staticmethod
    def extract_date(text: str) -> str:
        patterns = [
            r'(?:Date\s*(?:of|&|and)?\s*(?:Incident|Occurence|Offence)|Date\s+of\s+occurrence)\s*[:\-]+\s*([^\n\r,;]+)',
            r'Date\s*:\s*([^\n\r,;]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                val = re.sub(r'\s{2,}', ' ', val)
                if len(val) > 5:
                    return val
        
        date_match = re.search(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b', text)
        if date_match:
            return date_match.group(0)
        return "Not found"

    @staticmethod
    def extract_place(text: str) -> str:
        patterns = [
            r'(?:Place\s+of\s*(?:Occurrence|Incident|Offence)|Location|Place\s+of\s+Incident)\s*[:\-]+\s*([^\n\r;]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                val = re.sub(r'\s{2,}', ' ', val)
                if len(val) > 3:
                    return val
        return "Not found"

    @staticmethod
    def extract_incident_description(text: str) -> str:
        headings = [
            r'(?:Brief\s+facts\s+of\s+the\s+case|Incident\s+Summary|Description\s+of\s+Incident|Incident\s+Description|Brief\s+History|Content\s+of\s+Complaint|Statement\s+of\s+Complainant|Occurrence\s+Details|Factual\s+Matrix)',
            r'(?:Complaint\s+Text|Detailed\s+Description|Offence\s+Details|Facts\s+of\s+Incident)'
        ]
        
        for heading in headings:
            match = re.search(heading, text, re.IGNORECASE)
            if match:
                start_idx = match.end()
                desc = text[start_idx:].strip()
                end_match = re.search(r'(?:Signature|Thumb\s+impression|P\.S\.|Date|Place|True\s+Copy)\b', desc, re.IGNORECASE)
                if end_match:
                    desc = desc[:end_match.start()].strip()
                
                desc = re.sub(r'\s+', ' ', desc)
                if len(desc) > 30:
                    return desc
                    
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        if paragraphs:
            longest = max(paragraphs, key=len)
            longest_clean = re.sub(r'\s+', ' ', longest)
            return longest_clean
            
        fallback_text = re.sub(r'\s+', ' ', text[:1000])
        return fallback_text if fallback_text else "Not found"

    @classmethod
    def parse(cls, text: str) -> Dict[str, any]:
        sections_dict = cls.extract_sections(text)
        incident_desc = cls.extract_incident_description(text)
        
        nature = "Not found"
        if sections_dict["ipc_sections"]:
            nature = f"Offence u/s {', '.join(sections_dict['ipc_sections'])} IPC"
        elif sections_dict["bns_sections"]:
            nature = f"Offence u/s {', '.join(sections_dict['bns_sections'])} BNS"
            
        return {
            "fir_number": cls.extract_fir_number(text),
            "police_station": cls.extract_police_station(text),
            "complainant": cls.extract_complainant(text),
            "accused": cls.extract_accused(text),
            "ipc_sections": sections_dict["ipc_sections"],
            "bns_sections": sections_dict["bns_sections"],
            "incident_summary": incident_desc[:800] if len(incident_desc) > 800 else incident_desc,
            "incident_description": incident_desc,
            "date_of_incident": cls.extract_date(text),
            "location": cls.extract_place(text),
            "nature_of_offence": nature
        }
