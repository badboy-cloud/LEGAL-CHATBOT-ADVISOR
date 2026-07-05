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
        return "Review Required"

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
        return "Review Required"

    @staticmethod
    def extract_complainant(text: str) -> str:
        comp_section_match = re.search(
            r'(?:Complainant|Informant|Complainant/Informant|Informant/Complainant|Details\s+of\s+Complainant|Details\s+of\s+Informant)[\s\S]{1,150}?Name\s*[:\-]+\s*([^\n\r,;]+)', 
            text, 
            re.IGNORECASE
        )
        if comp_section_match:
            val = comp_section_match.group(1).strip()
            if len(val) > 2 and not any(k in val.lower() for k in ['unknown', 'not found', 'address', 'details']):
                return val
                
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
                    
        name_match = re.search(r'\bName\s*[:\-]+\s*([A-Za-z\s]+)\b', text, re.IGNORECASE)
        if name_match:
            val = name_match.group(1).strip()
            if "complainant" in text.lower() or "informant" in text.lower():
                if len(val) > 2 and not any(k in val.lower() for k in ['unknown', 'not found', 'address', 'details']):
                    return val

        return "Review Required"

    @staticmethod
    def extract_accused(text: str) -> str:
        acc_section_match = re.search(
            r'(?:Accused|Accused\s+Details|Accused\s+Person\(s\))[\s\S]{1,150}?Name\s*[:\-]+\s*([^\n\r,;]+)', 
            text, 
            re.IGNORECASE
        )
        if acc_section_match:
            val = acc_section_match.group(1).strip()
            if len(val) > 2:
                if 'unknown' in val.lower():
                    return "Unknown"
                return val

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
                    if 'unknown' in val.lower():
                        return "Unknown"
                    return val
        
        return "Unknown"

    @staticmethod
    def extract_place(text: str) -> str:
        patterns = [
            r'(?:District|Dist\.?)\s*[:\-]+\s*([A-Za-z ]+)',
            r'(?:Place\s+of\s*(?:Occurrence|Incident|Offence)|Location|Place\s+of\s+Incident)\s*[:\-]+\s*([^\n\r;]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if ',' in val:
                    parts = [p.strip() for p in val.split(',')]
                    parts = [p for p in parts if p]
                    if parts:
                        val = parts[-1]
                val = re.sub(r'\s{2,}', ' ', val)
                if len(val) > 2:
                    return val
                    
        cities = [
            'Chennai', 'Mumbai', 'Delhi', 'New Delhi', 'Kolkata', 'Bangalore', 'Bengaluru', 
            'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow', 'Kanpur', 'Nagpur', 
            'Indore', 'Thane', 'Bhopal', 'Visakhapatnam', 'Patna', 'Vadodara', 'Ghaziabad', 
            'Ludhiana', 'Agra', 'Nashik', 'Faridabad', 'Meerut', 'Rajkot', 'Varanasi', 
            'Srinagar', 'Amritsar', 'Ranchi', 'Coimbatore', 'Noida', 'Gurgaon', 'Chandigarh'
        ]
        for city in cities:
            if re.search(r'\b' + re.escape(city) + r'\b', text, re.IGNORECASE):
                return city
                
        return "Review Required"

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
        return fallback_text if fallback_text else "Review Required"

    @staticmethod
    def extract_witnesses(text: str) -> List[str]:
        pattern_header = r'\b(?:Witnesses|Witness|Name\s+of\s+Witnesses|Details\s+of\s+Witnesses|Witness\s+Details|List\s+of\s+Witnesses)\b'
        match = re.search(pattern_header, text, re.IGNORECASE)
        
        witnesses = []
        if match:
            start_idx = match.end()
            block = text[start_idx:start_idx+400].strip()
            
            # Stop extraction before encountering stopping boundary phrases
            stop_patterns = [
                r'applicable\s+sections',
                r'evidence\s+submitted',
                r'action\s+taken',
                r'investigating\s+officer',
                r'officer\s+details',
                r'signature',
                r'acts\s+&\s+sections',
                r'acts\s+and\s+sections',
                r'brief\s+facts',
                r'statement\s+of',
                r'complainant',
                r'accused',
                r'place\s+of\s+occurrence',
                r'date\s+of\s+occurrence'
            ]
            block_lower = block.lower()
            earliest_stop = len(block)
            for pat in stop_patterns:
                m = re.search(pat, block, re.IGNORECASE)
                if m and m.start() < earliest_stop:
                    earliest_stop = m.start()
            block = block[:earliest_stop].strip()
                
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            for line in lines:
                # Clean prefix numbers/symbols
                num_match = re.match(r'^(?:\d+[\.\)]|\-|\*)\s*([^\n\r]+)$', line)
                if num_match:
                    val = num_match.group(1).strip()
                else:
                    val = line
                val = val.strip(',.; ')
                if len(val) > 3 and not any(k in val.lower() for k in ['none', 'nil', 'not applicable', 'n/a', 'no witness', 'unknown']):
                    if val.lower() in text.lower() and val not in witnesses:
                        witnesses.append(val)
                        
            if not witnesses and lines:
                first_line = lines[0]
                if ',' in first_line:
                    parts = [p.strip() for p in first_line.split(',')]
                    for p in parts:
                        p_clean = re.sub(r'^(?:\d+[\.\)]|\-|\*)\s*', '', p).strip()
                        p_clean = p_clean.strip(',.; ')
                        if len(p_clean) > 3 and not any(k in p_clean.lower() for k in ['none', 'nil', 'n/a', 'not applicable']):
                            if p_clean.lower() in text.lower() and p_clean not in witnesses:
                                witnesses.append(p_clean)
                                
        return witnesses

    @staticmethod
    def extract_legal_sections(text: str) -> List[str]:
        # 1. Try to find the specific Acts & Sections block
        block = None
        block_match = re.search(
            r'\b(?:Acts?\s*(?:&|and)\s*Sections?|Acts?|Sections?)\s*[:\-]+([\s\S]+?)(?=\n\s*\n|\n\s*[A-Z][a-z]+:|\bComplainant\b|\bInformant\b|\bAccused\b|\bPlace\b|\bDate\b|\bWitnesses\b|\bBrief\b|$)', 
            text, 
            re.IGNORECASE
        )
        if block_match:
            block = block_match.group(1).strip()
        
        if block:
            search_text = re.sub(r'\s+', ' ', block)
            is_block_search = True
        else:
            search_text = re.sub(r'\s+', ' ', text)
            is_block_search = False
            
        # Define Acts and their patterns
        act_patterns = [
            ("IPC", r'\b(?:IPC|Indian\s+Penal\s+Code)\b'),
            ("BNS", r'\b(?:BNS|Bharatiya\s+Nyaya\s+Sanhita)\b'),
            ("IT Act", r'\b(?:IT\s+Act|Information\s+Technology\s+Act|IT\s+Sections?|IT)\b')
        ]
        
        # Find all Act occurrences
        act_occurrences = []
        for act_name, pattern in act_patterns:
            for match in re.finditer(pattern, search_text, re.IGNORECASE):
                act_occurrences.append({
                    "name": act_name,
                    "start": match.start(),
                    "end": match.end()
                })
        act_occurrences.sort(key=lambda x: x["start"])
        
        # Find all candidate section numbers
        candidates = []
        for match in re.finditer(r'\b([0-9]{2,4}[A-Za-z]?)\b', search_text):
            cand = match.group(1)
            # Skip years
            if cand.isdigit() and len(cand) == 4 and 1900 <= int(cand) <= 2100:
                continue
            candidates.append({
                "code": cand,
                "start": match.start(),
                "end": match.end()
            })
            
        sections = []
        for cand in candidates:
            cand_start = cand["start"]
            cand_end = cand["end"]
            cand_code = cand["code"]
            
            associated_act = None
            
            if is_block_search:
                # Find the nearest preceding Act occurrence
                preceding_act = None
                for act in reversed(act_occurrences):
                    if act["end"] <= cand_start:
                        preceding_act = act["name"]
                        break
                
                if preceding_act:
                    associated_act = preceding_act
                else:
                    # Check if there is a following Act within 30 chars
                    following_act = None
                    for act in act_occurrences:
                        if act["start"] >= cand_end and act["start"] - cand_end <= 30:
                            following_act = act["name"]
                            break
                    if following_act:
                        associated_act = following_act
            else:
                # Tight proximity
                preceding_act = None
                for act in reversed(act_occurrences):
                    if act["end"] <= cand_start:
                        if cand_start - act["end"] <= 25:
                            preceding_act = act["name"]
                            break
                
                if preceding_act:
                    associated_act = preceding_act
                else:
                    following_act = None
                    for act in act_occurrences:
                        if act["start"] >= cand_end and act["start"] - cand_end <= 25:
                            following_act = act["name"]
                            break
                    if following_act:
                        associated_act = following_act
                        
            if associated_act:
                sections.append(f"{associated_act} {cand_code.upper()}")
                
        # Filter duplicates and validate each section exists as a distinct word in raw text
        validated = []
        for sec in sections:
            parts = sec.split()
            code = parts[-1]
            if re.search(r'\b' + re.escape(code) + r'\b', text, re.IGNORECASE):
                # Verify we never use hardcoded fallback values IPC 302/304 if they don't exist in source document
                if code in ["302", "304"] and not re.search(r'\b' + re.escape(code) + r'\b', text):
                    continue
                if sec not in validated:
                    validated.append(sec)
                    
        return validated

    @staticmethod
    def extract_crpc_sections(text: str) -> List[str]:
        patterns = [
            r'\b(?:CrPC|Cr\.P\.C\.|BNSS|Code\s+of\s+Criminal\s+Procedure|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita)\s*(?:Sections?|Sec\.?|u/s|under\s+section)?\s*([0-9]{2,4}[A-Za-z]?)\b',
            r'\b(?:Sections?|Sec\.?|u/s|under\s+section)\s*([0-9]{2,4}[A-Za-z]?)\s*(?:of\s*(?:the\s*)?)?(?:CrPC|Cr\.P\.C\.|BNSS|Code\s+of\s+Criminal\s+Procedure)\b'
        ]
        sections = []
        norm_text = re.sub(r'\s+', ' ', text)
        for pat in patterns:
            for m in re.finditer(pat, norm_text, re.IGNORECASE):
                sect = m.group(1).strip().upper()
                if sect.lower() in text.lower() and f"Section {sect} CrPC" not in sections:
                    sections.append(f"Section {sect} CrPC")
                    
        if not sections:
            if "154" in text:
                sections.append("Section 154 CrPC")
        return sections

    @staticmethod
    def extract_officer_details(text: str) -> str:
        # Match pattern for Investigating Officer / Inspector etc.
        patterns = [
            r'(?:Investigating\s+Officer|I\.O\.|Officer\s+in\s+Charge|Case\s+Assigned\s+to|HC|ASI|SI|Inspector|Investigated\s+by)\s*[:\-]+\s*([^\n\r]+)',
            r'\b(?:Investigating\s+Officer|I\.O\.)\s+([^\n\r]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                
                # Stop extraction before Signature, Station House Officer, Police Station, PS
                stop_patterns = [
                    r'signature',
                    r'station\s+house\s+officer',
                    r'police\s+station',
                    r'ps:',
                    r'p\.s\.',
                    r'cyber\s+crime',
                    r'\bsho\b'
                ]
                earliest_stop = len(val)
                for pat in stop_patterns:
                    m = re.search(pat, val, re.IGNORECASE)
                    if m and m.start() < earliest_stop:
                        earliest_stop = m.start()
                val = val[:earliest_stop].strip()
                
                # Clean trailing punctuation and OCR artifacts
                val = val.strip(',.;\-#/* ')
                val = re.sub(r'\s{2,}', ' ', val)
                if len(val) > 3 and not any(k in val.lower() for k in ['yes', 'no', 'nil', 'none', 'n/a']):
                    return val
                    
        # Fallback search for Sub-Inspector, Inspector, HC, ASI, SI followed by name
        m_inspect = re.search(r'\b(Inspector|HC|ASI|SI|Sub\-Inspector)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', text)
        if m_inspect:
            val = m_inspect.group(0).strip()
            # Stop before boundaries
            stop_patterns = [
                r'signature',
                r'station\s+house\s+officer',
                r'police\s+station',
                r'cyber\s+crime',
                r'\bsho\b'
            ]
            earliest_stop = len(val)
            for pat in stop_patterns:
                m = re.search(pat, val, re.IGNORECASE)
                if m and m.start() < earliest_stop:
                    earliest_stop = m.start()
            val = val[:earliest_stop].strip()
            val = val.strip(',.;\-#/* ')
            if len(val) > 3:
                return val

        return "Review Required"

    @staticmethod
    def extract_evidence_submitted(text: str) -> str:
        pattern = r'\b(?:Evidence\s+Submitted|Evidence|Seized\s+Material|Seizure\s+Memo|Seizure\s+List|Articles\s+Seized|Articles\s+Recovered|Recovery|Items\s+Seized)\s*[:\-]+'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start_idx = match.end()
            block = text[start_idx:start_idx+500].strip()
            
            # Find end of section
            stop_patterns = [
                r'officer',
                r'signature',
                r'investigating\s+officer',
                r'station\s+house\s+officer',
                r'police\s+station',
                r'acts\s+&\s+sections',
                r'brief\s+facts'
            ]
            earliest_stop = len(block)
            for pat in stop_patterns:
                m = re.search(pat, block, re.IGNORECASE)
                if m and m.start() < earliest_stop:
                    earliest_stop = m.start()
            block = block[:earliest_stop].strip()
            
            # Extract bullet points or line items
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            evidence_items = []
            for line in lines:
                # Clean bullet characters or numbers
                clean_line = re.sub(r'^(?:\d+[\.\)]|\-|\*)\s*', '', line).strip()
                clean_line = clean_line.strip(',.; ')
                if clean_line and len(clean_line) > 3:
                    evidence_items.append(clean_line)
            
            if evidence_items:
                return "\n".join([f"- {item}" for item in evidence_items])
                
        return "Review Required"

    @staticmethod
    def extract_registration_date(text: str) -> str:
        patterns = [
            r'(?:Date\s+(?:and\s+Time\s+)?of\s+Registration|Registration\s+Date|Registered\s+on)\s*[:\-]+\s*([^\n\r;]+)',
            r'(?:Date\s+of\s+Registration)\s*[:\-]+\s*([0-9A-Za-z\s]+)\b'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Find the actual date string inside val
                date_match = re.search(r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b', val, re.IGNORECASE)
                if date_match:
                    return date_match.group(0).strip()
                date_match_num = re.search(r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.](?:19|20)\d{2}\b', val)
                if date_match_num:
                    return date_match_num.group(0).strip()
        return "Review Required"

    @staticmethod
    def extract_incident_date(text: str) -> str:
        patterns = [
            r'(?:Date\s+and\s+Time\s+of\s+Occurrence|Occurrence\s+Date|Date\s+of\s+Incident|Incident\s+Date|Occurrence\s+Details)\s*[:\-]+\s*([^\n\r;]+)',
            r'(?:Date\s+(?:and\s+Time\s+)?of\s+Occurrence)\s*[:\-]+\s*([^\n\r]+)',
            r'(?:Date\s+of\s+Occurrence)\s*[:\-]+\s*([^\n\r;]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Stop extraction before place of occurrence or other headers
                end_pos = len(val)
                for marker in ["place of occurrence", "time of occurrence", "written/oral", "complainant", "accused", "brief facts"]:
                    pos = val.lower().find(marker)
                    if pos != -1 and pos < end_pos:
                        end_pos = pos
                val = val[:end_pos].strip()
                val_cleaned = re.sub(r'\s+', ' ', val)
                val_cleaned = val_cleaned.replace(" to ", " - ")
                if val_cleaned and len(val_cleaned) > 5:
                    return val_cleaned
        return "Review Required"

    @classmethod
    def parse(cls, text: str) -> Dict[str, any]:
        legal_sections = cls.extract_legal_sections(text)
        witnesses = cls.extract_witnesses(text)
        crpc_sections = cls.extract_crpc_sections(text)
        officer_details = cls.extract_officer_details(text)
        evidence_submitted = cls.extract_evidence_submitted(text)
        
        ipc_sections = [s.split()[1] for s in legal_sections if s.startswith("IPC ")]
        bns_sections = [s.split()[1] for s in legal_sections if s.startswith("BNS ")]
        
        incident_desc = cls.extract_incident_description(text)
        
        nature = "Review Required"
        if ipc_sections:
            nature = f"Offence u/s {', '.join(ipc_sections)} IPC"
        elif bns_sections:
            nature = f"Offence u/s {', '.join(bns_sections)} BNS"
            
        registration_date = cls.extract_registration_date(text)
        incident_date = cls.extract_incident_date(text)
        
        parsed_dict = {
            "fir_number": cls.extract_fir_number(text),
            "police_station": cls.extract_police_station(text),
            "complainant": cls.extract_complainant(text),
            "accused": cls.extract_accused(text),
            "witnesses": witnesses,
            "witnesses_list": witnesses,
            "ipc_sections": ipc_sections,
            "bns_sections": bns_sections,
            "legal_sections": legal_sections,
            "crpc_sections": crpc_sections,
            "officer_details": officer_details,
            "evidence_submitted": evidence_submitted,
            "dates": [registration_date] if registration_date != "Review Required" else [],
            "date_of_registration": registration_date,
            "date_of_incident": incident_date,
            "location": cls.extract_place(text),
            "incident_summary": incident_desc[:800] if len(incident_desc) > 800 else incident_desc,
            "incident_description": incident_desc,
            "nature_of_offence": nature,
            "raw_text": text
        }
        
        # Clean fallback values to "Review Required"
        for k in ["fir_number", "police_station", "complainant", "accused", "location", "officer_details", "evidence_submitted", "date_of_registration", "date_of_incident"]:
            val = parsed_dict.get(k)
            if k == "accused" and val == "Unknown":
                continue
            if not val or str(val).strip() in ["", "None", "N/A", "Not found", "None explicitly listed", "None noted"]:
                parsed_dict[k] = "Review Required"
                
        # Validate against raw source text
        for key in ["fir_number", "police_station", "complainant", "accused", "location", "officer_details", "evidence_submitted"]:
            val = parsed_dict.get(key)
            if val and val != "Review Required":
                if key == "evidence_submitted":
                    lines = [l.strip().replace("- ", "") for l in val.split("\n") if l.strip()]
                    all_found = True
                    for l in lines:
                        if l.lower() not in text.lower():
                            all_found = False
                            break
                    if not all_found:
                        parsed_dict[key] = "Review Required"
                else:
                    if val.lower() not in text.lower():
                        words = [w for w in re.split(r'\W+', val) if len(w) > 3]
                        if words and not any(w.lower() in text.lower() for w in words):
                            parsed_dict[key] = "Review Required"
                            
        # Validate witnesses list against raw text
        witnesses_valid = []
        if isinstance(witnesses, list) and witnesses:
            for w in witnesses:
                if w.lower() in text.lower():
                    witnesses_valid.append(w)
                else:
                    words = [word for word in re.split(r'\W+', w) if len(word) > 3]
                    if words and any(word.lower() in text.lower() for word in words):
                        witnesses_valid.append(w)
            
            if len(witnesses_valid) != len(witnesses):
                parsed_dict["witnesses"] = "Review Required"
                parsed_dict["witnesses_list"] = []
            else:
                parsed_dict["witnesses"] = witnesses_valid
                parsed_dict["witnesses_list"] = witnesses_valid
        else:
            if not witnesses:
                parsed_dict["witnesses"] = []
                parsed_dict["witnesses_list"] = []
            else:
                parsed_dict["witnesses"] = "Review Required"
                parsed_dict["witnesses_list"] = []

        # Validate legal sections list
        sections_valid = []
        if isinstance(legal_sections, list):
            for sec in legal_sections:
                code = sec.split()[-1]
                if re.search(r'\b' + re.escape(code) + r'\b', text, re.IGNORECASE):
                    sections_valid.append(sec)
            parsed_dict["legal_sections"] = sections_valid
            
        # Validate dates
        for key in ["date_of_registration", "date_of_incident"]:
            val = parsed_dict.get(key)
            if val and val != "Review Required":
                words = [w for w in re.split(r'\W+', val) if len(w) > 2]
                if words:
                    found_count = sum(1 for w in words if w.lower() in text.lower())
                    if found_count < len(words) * 0.5:
                        parsed_dict[key] = "Review Required"
                        
        # Recalculate dates list
        dates_list = []
        if parsed_dict["date_of_registration"] != "Review Required":
            dates_list.append(parsed_dict["date_of_registration"])
        parsed_dict["dates"] = dates_list
                        
        # Calculate confidence scores
        scores = {}
        for k in ["fir_number", "police_station", "complainant", "accused", "location", "officer_details", "evidence_submitted", "date_of_registration", "date_of_incident"]:
            val = parsed_dict.get(k)
            if val == "Review Required":
                scores[k] = 0.0
            else:
                scores[k] = 0.95
                
        scores["witnesses"] = 0.95 if parsed_dict["witnesses"] != "Review Required" else 0.0
        scores["legal_sections"] = 0.95 if parsed_dict["legal_sections"] != "Review Required" else 0.0
        scores["crpc_sections"] = 0.95 if crpc_sections else 0.5
        
        review_fields = [k for k, v in scores.items() if v < 0.7]
        
        parsed_dict["confidence_scores"] = scores
        parsed_dict["review_required_fields"] = review_fields
        
        return parsed_dict
