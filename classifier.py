# classifier.py
import re
from datetime import datetime

# Bilingual mapping for Block detection
BLOCK_MAPPING = {
    "Hilsa": ["hilsa", "हिलसा"],
    "Islampur": ["islampur", "इस्लामपुर"],
    "Biharsharif": ["biharsharif", "bihar sharif", "बिहारशरीफ", "बिहार शरीफ"],
    "Rajgir": ["rajgir", "राजगीर"],
    "Harnaut": ["harnaut", "हरनौत"],
    "Noorsarai": ["noorsarai", "नूरसराय"],
    "Rahui": ["rahui", "रहुई"],
    "Asthawan": ["asthawan", "अस्थावां", "अस्थावन"],
    "Chandi": ["chandi", "चंडी"],
    "Ekangarsarai": ["ekangarsarai", "एकंगरसराय"],
    "Bind": ["bind", "बिंद"],
    "Silao": ["silao", "सिलाव"],
    "Giriyak": ["giriyak", "गिरियक"],
    "Tharthari": ["tharthari", "थरथरी"],
    "Karai Parsurai": ["karai parsurai", "कराई परसुराय", "कराई"],
    "Katrisarai": ["katrisarai", "कतरीसराय"],
    "Ben": ["ben", "बेन"],
    "Sarmera": ["sarmera", "सरमेरा"],
    "Parbalpur": ["parbalpur", "परवलपुर", "परबलपुर"],
    "Warisaliganj": ["warisaliganj", "वारिसलीगंज"]
}

SCHEMA = {
    "Water / Jal": {
        "department": "Public Health Engineering Dept. (PHED)",
        "icon": "💧",
        "jurisdiction": "Ward Implementation Committee ➔ Panchayat Secretary ➔ Junior Engineer (PHED)",
        "central_schemes": ["Jal Jeevan Mission (JJM)", "National Rural Drinking Water Programme"],
        "bihar_schemes": ["Mukhyamantri Nishchay Har Ghar Nal-Ka-Jal Yojana", "Saat Nischay Part 1 & 2"],
        "keywords": {
            "जल जीवन मिशन": 3, "हैंडपम्प": 3, "हैंडपंप": 3, "जलापूर्ति": 3,
            "drinking water": 3, "handpump": 3, "water supply": 3,
            "पेयजल": 3, "jal jeevan": 3, "pipe leakage": 3,
            "पानी": 2, "जल": 2, "नल": 2, "पम्प": 2, "बोरिंग": 2,
            "पाइप": 2, "water": 2, "pump": 2, "boring": 2, "pipe": 2,
            "नाला": 2, "drainage": 2, "पीना": 1, "supply": 1, "बर्बाद": 1, "गंदा": 1,
        },
        "priority_keywords": ["contaminated", "गंदा पानी", "बीमारी", "disease", "no water", "पानी नहीं"],
    },
    "Roads / Sadak": {
        "department": "Rural Works Dept. (RWD) / Local Urban Body",
        "icon": "🛣️",
        "jurisdiction": "Gram Panchayat ➔ Block Assistant Engineer ➔ Executive Engineer (RWD)",
        "central_schemes": ["Pradhan Mantri Gram Sadak Yojana (PMGSY)"],
        "bihar_schemes": ["Mukhyamantri Gram Sampark Yojana (MMGSY)", "Ghar Tak Pakki Gali-Nali Nishchay"],
        "keywords": {
            "सड़क निर्माण": 3, "पक्की सड़क": 3, "road construction": 3,
            "pothole": 3, "गड्ढे": 3, "bridge damaged": 3,
            "सड़क": 2, "रास्ता": 2, "पुल": 2, "निर्माण": 2,
            "road": 2, "path": 2, "bridge": 2, "sadak": 2,
            "टूटी": 1, "broken": 1, "खराब": 1, "कच्चा": 1,
        },
        "priority_keywords": ["दुर्घटना", "accident", "खतरनाक", "dangerous", "blocked", "बंद"],
    },
    "Ration / PDS": {
        "department": "Food and Consumer Protection Dept.",
        "icon": "🌾",
        "jurisdiction": "Fair Price Shop (FPS) Dealer ➔ Block Supply Officer (BSO) ➔ Sub-Divisional Officer (SDO)",
        "central_schemes": ["Pradhan Mantri Garib Kalyan Anna Yojana (PMGKAY)", "National Food Security Act (NFSA)"],
        "bihar_schemes": ["Bihar State PDS Rules", "SFC Doorstep Delivery Scheme"],
        "keywords": {
            "राशन कार्ड": 3, "उचित मूल्य दुकान": 3, "fair price shop": 3,
            "बीपीएल कार्ड": 3, "ration card": 3, "pds": 3,
            "राशन": 2, "अनाज": 2, "चावल": 2, "गेहूं": 2,
            "दुकान": 2, "ration": 2, "grain": 2, "rice": 2, "wheat": 2,
            "food": 1, "card": 1, "बीपीएल": 1, "bpl": 1,
        },
        "priority_keywords": ["भूख", "hunger", "starving", "नहीं मिल रहा", "महीनों से"],
    },
    "Land / Bhumi": {
        "department": "Revenue and Land Reforms Dept.",
        "icon": "🏡",
        "jurisdiction": "Revenue Karamchari ➔ Circle Inspector ➔ Circle Officer (CO) ➔ DCLR",
        "central_schemes": ["SVAMITVA Scheme (Property Cards)", "Digital India Land Records Modernization (DILRMP)"],
        "bihar_schemes": ["Mukhyamantri Vas Sthal Kray Yojana", "Bihar Land Mutation Rules"],
        "keywords": {
            "दाखिल खारिज": 3, "जमाबंदी": 3, "lpc": 3, "mutation": 3,
            "encroachment": 3, "अतिक्रमण": 3, "land dispute": 3,
            "जमीन": 2, "भूमि": 2, "खाता": 2, "खसरा": 2,
            "पट्टा": 2, "land": 2, "plot": 2, "survey": 2,
            "बंटवारा": 1, "partition": 1, "register": 1,
        },
        "priority_keywords": ["कब्जा", "occupation", "विवाद", "dispute", "धमकी", "threat", "forceful"],
    },
    "Health / Swasthya": {
        "department": "Health Dept. / Civil Surgeon Office",
        "icon": "🏥",
        "jurisdiction": "ASHA/ANM Worker ➔ PHC Medical Officer ➔ In-Charge Medical Officer ➔ Civil Surgeon",
        "central_schemes": ["Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY)", "National Health Mission (NHM)"],
        "bihar_schemes": ["Mukhyamantri Chikitsa Sahayata Kosh", "Bihar Health Road Map Initiatives"],
        "keywords": {
            "प्राथमिक स्वास्थ्य केंद्र": 3, "phc": 3, "ambulance": 3,
            "vaccination": 3, "टीकाकरण": 3, "प्रसव": 3, "anm": 3,
            "अस्पताल": 2, "डॉक्टर": 2, "दवाई": 2, "इलाज": 2,
            "hospital": 2, "doctor": 2, "medicine": 2, "health": 2,
            "nurse": 1, "asha": 1, "आशा": 1, "स्वास्थ्य": 1,
        },
        "priority_keywords": ["मृत्यु", "death", "emergency", "गंभीर", "serious", "बच्चा बीमार"],
    },
    "Electricity / Bijli": {
        "department": "BSPHCL (South Bihar Power Distribution Co.)",
        "icon": "⚡",
        "jurisdiction": "Line Man ➔ Junior Engineer (JE, Electrical) ➔ Assistant Engineer (AE, Electricity)",
        "central_schemes": ["Revamped Distribution Sector Scheme (RDSS)", "Deen Dayal Upadhyaya Gram Jyoti Yojana"],
        "bihar_schemes": ["Har Ghar Bijli Nishchay Yojana", "Mukhyamantri Vidyut Upbhokta Sahayata Scheme"],
        "keywords": {
            "ट्रांसफार्मर": 3, "transformer": 3, "bijli connection": 3,
            "load shedding": 3, "बिजली कटौती": 3, "meter reading": 3,
            "बिजली": 2, "लाइट": 2, "तार": 2, "खम्भा": 2,
            "electricity": 2, "light": 2, "wire": 2, "pole": 2, "meter": 2,
            "current": 1, "power": 1, "कटौती": 1,
        },
        "priority_keywords": ["आग", "fire", "shock", "करंट", "खतरा", "danger", "जल रहा"],
    },
    "Education / Shiksha": {
        "department": "Education Dept. / District Education Officer",
        "icon": "📚",
        "jurisdiction": "School Headmaster ➔ Block Education Officer (BEO) ➔ District Education Officer (DEO)",
        "central_schemes": ["Samagra Shiksha Abhiyan", "Pradhan Mantri Poshan Shakti Nirman (PM-POSHAN / MDM)"],
        "bihar_schemes": ["Mukhyamantri Balak/Balika Cycle + Uniform Yojana", "Saat Nischay Student Credit Card"],
        "keywords": {
            "मिड डे मील": 3, "mid day meal": 3, "छात्रवृत्ति": 3,
            "scholarship": 3, "नामांकन": 3, "enrollment": 3,
            "स्कूल": 2, "शिक्षक": 2, "पढ़ाई": 2, "किताब": 2,
            "school": 2, "teacher": 2, "book": 2, "uniform": 2,
            "शिक्षा": 1, "education": 1, "यूनिफॉर्म": 1,
        },
        "priority_keywords": ["बंद", "closed", "absent", "अनुपस्थित", "नहीं पढ़ाते"],
    },
    "MGNREGA / Rozgar": {
        "department": "Rural Development Dept. (Block BDO Office)",
        "icon": "👷",
        "jurisdiction": "Panchayat Rozgar Sevak (PRS) ➔ Program Officer (PO) ➔ Block Development Officer (BDO)",
        "central_schemes": ["Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA)"],
        "bihar_schemes": ["Jal-Jeevan-Hariyali Mission (MGNREGA convergence link)", "Saat Nischay Yuva Shakti"],
        "keywords": {
            "मनरेगा": 3, "mgnrega": 3, "जॉब कार्ड": 3, "job card": 3,
            "मस्टर रोल": 3, "muster roll": 3, "100 दिन": 3,
            "मजदूरी": 2, "काम": 2, "भुगतान": 2, "रोजगार": 2,
            "wages": 2, "work": 2, "payment": 2, "employment": 2,
            "rozgar": 1, "labour": 1, "मजदूर": 1,
        },
        "priority_keywords": ["भुगतान नहीं", "payment pending", "महीनों से", "months pending", "3 महीने"],
    },
    "Pension / Samajik Suraksha": {
        "department": "Social Welfare Dept.",
        "icon": "👴",
        "jurisdiction": "Panchayat Secretary ➔ Block Social Security Officer (BSSO) ➔ District Social Security Cell",
        "central_schemes": ["National Social Assistance Programme (NSAP) — Indira Gandhi Old Age/Widow Pension"],
        "bihar_schemes": ["Mukhyamantri Vridhajan Pension Yojana (MVPY)", "Laxmibai Social Security Pension"],
        "keywords": {
            "वृद्धावस्था पेंशन": 3, "विधवा पेंशन": 3, "old age pension": 3,
            "widow pension": 3, "लक्ष्मीबाई": 3, "विकलांग पेंशन": 3,
            "पेंशन": 2, "pension": 2, "विधवा": 2, "वृद्धावस्था": 2,
            "disabled": 2, "विकलांग": 2, "social welfare": 2,
            "beneficiary": 1, "लाभार्थी": 1,
        },
        "priority_keywords": ["बंद हो गई", "stopped", "नहीं आ रही", "not receiving", "बुजुर्ग"],
    },
    "Other / Anya": {
        "department": "General Administration / SDO Office",
        "icon": "📄",
        "jurisdiction": "Block Development Officer (BDO) ➔ Sub-Divisional Officer (SDO) ➔ District Magistrate (DM)",
        "central_schemes": ["Public Grievance Redressal Portal (CPGRAMS)"],
        "bihar_schemes": ["Bihar Right to Public Grievance Redressal Act (BPGRA)"],
        "keywords": {},
        "priority_keywords": [],
    },
}

def _score_text(text, keywords):
    score = 0.0
    text_lower = text.lower()
    for kw, weight in keywords.items():
        count = text_lower.count(kw.lower())
        if count > 0:
            bonus = 1.5 if len(kw.split()) > 1 else 1.0
            score += weight * count * bonus
    return score

def classify_complaint(text):
    scores = {}
    for category, data in SCHEMA.items():
        if category == "Other / Anya":
            continue
        s = _score_text(text, data["keywords"])
        if s > 0:
            scores[category] = s

    if not scores:
        best = "Other / Anya"
        confidence = 0.0
    else:
        best = max(scores, key=scores.get)
        top_weights = sorted(SCHEMA[best]["keywords"].values(), reverse=True)[:3]
        max_possible = sum(top_weights) * 1.5
        confidence = min(scores[best] / max_possible, 1.0)

    cat_data = SCHEMA[best]
    priority = "Normal"
    text_lower = text.lower()
    if best != "Other / Anya":
        if any(kw.lower() in text_lower for kw in cat_data["priority_keywords"]):
            priority = "High"

    return {
        "category": best,
        "icon": cat_data["icon"],
        "department": cat_data["department"],
        "priority": priority,
        "confidence": round(confidence, 2),
        "jurisdiction": cat_data["jurisdiction"],
        "central_schemes": cat_data["central_schemes"],
        "bihar_schemes": cat_data["bihar_schemes"],
        "block": _extract_block(text),
        "village": _extract_village(text),
        "complainant_name": _extract_name(text),
        "date_filed": _extract_date(text),
        "all_scores": scores,
    }

def _extract_block(text):
    text_lower = text.lower()
    for std_block, variants in BLOCK_MAPPING.items():
        for variant in variants:
            if variant in text_lower:
                return std_block
    return "Unknown"

def _extract_village(text):
    patterns = [
        r'ग्राम[:\s]+(\S+)', r'गाँव[:\s]+(\S+)',
        r'गांव[:\s]+(\S+)', r'village[:\s]+([a-zA-Z]+)',
        r'gram[:\s]+([a-zA-Z]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip('.,।')
    return "Unknown"

def _extract_name(text):
    patterns = [
        r'(?:मेरा नाम|मैं)\s+([\w\s]{3,25})',
        r'(?:श्री|श्रीमती|सुश्री)\s+([\w\s]{3,25})',
        r'(?:I am|My name is)\s+([A-Za-z\s]{3,25})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return ' '.join(m.group(1).strip().split()[:4])
    return "Unknown"

def _extract_date(text):
    patterns = [
        r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}',
        r'\d{1,2}\s+(?:जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितम्बर|अक्टूबर|नवम्बर|दिसम्बर)\s+\d{4}',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return datetime.now().strftime('%Y-%m-%d')

def get_all_categories():
    return list(SCHEMA.keys())