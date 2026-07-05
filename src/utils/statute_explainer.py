from typing import Dict

STATUTE_EXPLAINER = {
    "IPC 420": {
        "name": "Cheating and dishonestly inducing delivery of property",
        "description": "Cheating and dishonestly inducing delivery of property, or altering or destroying a valuable security.",
        "punishment": "Imprisonment of either description for a term which may extend to 7 years, and shall also be liable to fine.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Non-Bailable (Bail is a matter of court discretion)"
    },
    "IPC 468": {
        "name": "Forgery for purpose of cheating",
        "description": "Committing forgery, intending that the forged document or electronic record shall be used for the purpose of cheating.",
        "punishment": "Imprisonment of either description for a term which may extend to 7 years, and shall also be liable to fine.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Non-Bailable (Bail is a matter of court discretion)"
    },
    "IPC 471": {
        "name": "Using as genuine a forged document or electronic record",
        "description": "Whoever fraudulently or dishonestly uses as genuine any document or electronic record which he knows or has reason to believe to be forged.",
        "punishment": "Punished in the same manner as if he had forged such document (Up to 7 years and fine under Sec 468).",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Non-Bailable (Depends on the forged document's nature)"
    },
    "IT ACT 66C": {
        "name": "Punishment for identity theft",
        "description": "Fraudulently or dishonestly making use of the electronic signature, password or any other unique identification feature of any other person.",
        "punishment": "Imprisonment of either description for a term which may extend to 3 years, and fine up to Rs. 1 lakh.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Bailable (Bail is a matter of right)"
    },
    "IT ACT 66D": {
        "name": "Punishment for cheating by personation by using computer resource",
        "description": "Cheating by personation by means of any communication device or computer resource.",
        "punishment": "Imprisonment of either description for a term which may extend to 3 years, and fine up to Rs. 1 lakh.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Bailable (Bail is a matter of right)"
    },
    "IPC 120B": {
        "name": "Punishment of criminal conspiracy",
        "description": "Party to a criminal conspiracy to commit an offence punishable with death, imprisonment for life or rigorous imprisonment.",
        "punishment": "Same as abetment of the offence if no express provision is made (Up to 7 years for cheating).",
        "cognizability": "Cognizable (If the target offence is cognizable)",
        "bailability": "Non-Bailable (If the target offence is non-bailable)"
    },
    "IPC 406": {
        "name": "Punishment for criminal breach of trust",
        "description": "Criminal breach of trust by misappropriation or conversion of property for personal use.",
        "punishment": "Imprisonment of either description for a term which may extend to 3 years, or with fine, or with both.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Non-Bailable (Bail is a matter of court discretion)"
    },
    "IPC 506": {
        "name": "Punishment for criminal intimidation",
        "description": "Threatening a person with injury to their person, reputation, or property, to cause alarm.",
        "punishment": "Imprisonment of either description for a term which may extend to 2 years, or with fine, or with both.",
        "cognizability": "Non-Cognizable (Generally, but varies by state/offence severity)",
        "bailability": "Bailable (Bail is a matter of right)"
    },
    "IPC 379": {
        "name": "Punishment for theft",
        "description": "Dishonestly taking any movable property out of the possession of any person without consent.",
        "punishment": "Imprisonment of either description for a term which may extend to 3 years, or with fine, or with both.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Non-Bailable (Bail is a matter of court discretion)"
    },
    "IPC 34": {
        "name": "Common intention",
        "description": "Acts done by several persons in furtherance of a common intention, making each liable as if done by him alone.",
        "punishment": "Same as the principal offence committed in furtherance of the common intention.",
        "cognizability": "Cognizable (If the target offence is cognizable)",
        "bailability": "Non-Bailable (If the target offence is non-bailable)"
    },
    "IPC 302": {
        "name": "Punishment for murder",
        "description": "Committing murder by causing death with intention or knowledge.",
        "punishment": "Death or imprisonment for life, and shall also be liable to fine.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Non-Bailable (Bail is a matter of court discretion)"
    },
    "IPC 304": {
        "name": "Punishment for culpable homicide not amounting to murder",
        "description": "Causing death with the intention of causing death or such bodily injury as is likely to cause death, but without murder intent.",
        "punishment": "Imprisonment for life, or imprisonment of either description for a term up to 10 years, and fine.",
        "cognizability": "Cognizable (Police can arrest without a warrant)",
        "bailability": "Non-Bailable (Bail is a matter of court discretion)"
    }
}

def get_explainer_details(section_code: str) -> Dict[str, str]:
    """
    Get explainer details for a specific statute section code (e.g. 'IPC 420').
    """
    key = section_code.strip().upper()
    # Handle variations in spacing/formatting
    key_normalized = key.replace("IT ACT", "IT ACT").replace("SECTION", "").replace("SEC", "").strip()
    
    if key_normalized in STATUTE_EXPLAINER:
        return STATUTE_EXPLAINER[key_normalized]
        
    # Check for loose containment
    for k, v in STATUTE_EXPLAINER.items():
        if k in key_normalized or key_normalized in k:
            return v
            
    # Default fallback description if section is not pre-defined
    return {
        "name": f"Section {section_code}",
        "description": "Specific statutory provision under Indian penal code or relevant cyber acts.",
        "punishment": "As prescribed by the magistrate court under applicable schedules.",
        "cognizability": "Generally Cognizable",
        "bailability": "Subject to judicial discretion (Check Code of Criminal Procedure schedule)"
    }
