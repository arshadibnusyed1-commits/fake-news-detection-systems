import requests
import urllib.parse
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timezone, timedelta


# ============================================================
# TRUTHLENS AI - LIVE NEWS VERIFIER V12
# ============================================================

TRUSTED_SOURCES = [
    "the hindu",
    "indian express",
    "times of india",
    "hindustan times",
    "ndtv",
    "bbc",
    "reuters",
    "pib",
    "press information bureau",
    "pti",
    "ani",
    "deccan herald",
    "new indian express",
    "economic times",
    "india today",
    "news18",
    "the print",
    "news on air",
    "all india radio",
    "dt next",
    "livechennai"
]


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize(text):
    text = clean_text(text).lower()

    replacements = {
        "2026–27": "2026-27",
        "2025–26": "2025-26",
        "2024–25": "2024-25",
        "–": "-",
        "—": "-",
    }

    for a, b in replacements.items():
        text = text.replace(a, b)

    return text


# ============================================================
# GOOGLE NEWS RSS SEARCH
# ============================================================

def search_news(query, limit=10):

    try:
        encoded = urllib.parse.quote(query)

        url = (
            "https://news.google.com/rss/search?"
            + "q=" + encoded
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        response = requests.get(
            url,
            timeout=12,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)

        results = []

        for item in root.findall(".//item")[:limit]:

            title = clean_text(
                item.findtext("title", "")
            )

            link = clean_text(
                item.findtext("link", "")
            )

            pub_date = clean_text(
                item.findtext("pubDate", "")
            )

            description = clean_text(
                item.findtext("description", "")
            )

            source = ""

            source_node = item.find("source")

            if source_node is not None:
                source = clean_text(
                    source_node.text or ""
                )

            if title:
                results.append({
                    "title": title,
                    "link": link,
                    "date": pub_date,
                    "source": source,
                    "description": description
                })

        return results

    except Exception as e:
        print("SEARCH ERROR:", e)
        return []


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicates(results):

    seen = set()
    output = []

    for item in results:

        key = normalize(
            item.get("title", "")
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


# ============================================================
# DATE PARSING
# ============================================================

def parse_result_date(date_text):

    if not date_text:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%d %b %Y %H:%M:%S %Z",
        "%d %b %Y %H:%M:%S %z",
    ]

    for fmt in formats:

        try:
            dt = datetime.strptime(
                date_text,
                fmt
            )

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=timezone.utc
                )

            return dt

        except:
            pass

    return None


# ============================================================
# CLAIM DATE
# ============================================================

def extract_claim_date(text):

    text = normalize(text)

    patterns = [
        r"\b(\d{1,2})[/-](\d{1,2})[/-](202\d)\b",
        r"\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(202\d)\b",
        r"\b(september|october|november|december)\s+(\d{1,2}),?\s+(202\d)\b"
    ]

    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12
    }

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if not match:
            continue

        try:

            groups = match.groups()

            if len(groups) == 3:

                if groups[0].isdigit() and groups[1].isdigit():

                    day = int(groups[0])
                    month = int(groups[1])
                    year = int(groups[2])

                    return datetime(
                        year,
                        month,
                        day,
                        tzinfo=timezone.utc
                    )

                if groups[1].lower() in months:

                    day = int(groups[0])
                    month = months[
                        groups[1].lower()
                    ]
                    year = int(groups[2])

                    return datetime(
                        year,
                        month,
                        day,
                        tzinfo=timezone.utc
                    )

                if groups[0].lower() in months:

                    month = months[
                        groups[0].lower()
                    ]

                    day = int(groups[1])
                    year = int(groups[2])

                    return datetime(
                        year,
                        month,
                        day,
                        tzinfo=timezone.utc
                    )

        except:
            pass

    return None


# ============================================================
# CLAIM TYPE
# ============================================================

def detect_claim_type(text):

    text = normalize(text)

    if any(x in text for x in [
        "school",
        "schools",
        "school education",
        "quarterly examination",
        "quarterly exam"
    ]):
        return "school"

    if any(x in text for x in [
        "college",
        "universit",
        "campus"
    ]):
        return "college"

    if any(x in text for x in [
        "railway",
        "railways",
        "train",
        "trains"
    ]):
        return "railway"

    if any(x in text for x in [
        "bank",
        "banking"
    ]):
        return "bank"

    if any(x in text for x in [
        "hospital",
        "medical",
        "health department"
    ]):
        return "hospital"

    return "general"


# ============================================================
# STRONG CLAIM DETECTION
# ============================================================

def detect_strong_claim(text):

    text = normalize(text)

    phrases = [

        "permanently closed",
        "permanently shut",
        "closed permanently",
        "will remain closed permanently",

        "completely banned",
        "totally banned",
        "permanently banned",

        "all schools closed",
        "all schools will close",
        "all government schools closed",

        "all colleges closed",
        "all colleges will close",

        "completely cancelled",
        "permanently cancelled",

        "government has banned",
        "government has permanently banned",

    ]

    for phrase in phrases:

        if phrase in text:
            return True, phrase

    return False, ""


# ============================================================
# STOP WORDS
# ============================================================

STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "on",
    "for",
    "from",
    "with",
    "has",
    "have",
    "had",
    "is",
    "are",
    "was",
    "were",
    "will",
    "be",
    "been",
    "that",
    "this",
    "these",
    "those",
    "as",
    "by",
    "at",
    "it",
    "its",
    "their",
    "they",
    "them",
    "into",
    "after",
    "before",
    "during",
    "over",
    "under",
    "about",
    "according",
    "said",
    "says",
    "claim",
    "claims",
    "news",
    "report",
    "reports",
    "today",
    "latest",
    "current"
}


GENERIC_WORDS = {
    "government",
    "department",
    "official",
    "officials",
    "state",
    "country",
    "people",
    "students",
    "public",
    "information",
    "update",
    "details",
    "check",
    "announcement",
    "announced",
    "released",
    "schedule",
    "scheduled",
    "education",
    "school",
    "schools",
    "college",
    "colleges",
    "railway",
    "railways",
    "train",
    "trains"
}


# ============================================================
# KEYWORD EXTRACTION
# ============================================================

def extract_keywords(text):

    text = normalize(text)

    words = re.findall(
        r"[a-z0-9]+(?:-[a-z0-9]+)*",
        text
    )

    keywords = []

    for word in words:

        if len(word) < 3:
            continue

        if word in STOP_WORDS:
            continue

        if word in GENERIC_WORDS:
            continue

        if word not in keywords:
            keywords.append(word)

    return keywords[:20]


# ============================================================
# IMPORTANT PHRASES
# ============================================================

def extract_important_phrases(text):

    text = normalize(text)

    phrases = [

        "quarterly examination",
        "quarterly exam",
        "examination schedule",
        "exam schedule",
        "academic calendar",
        "academic year",

        "special trains",
        "special train",
        "ganpati special",
        "passenger demand",

        "school education department",
        "government schools",
        "government-aided schools",

        "school holiday",
        "school holidays",

        "board exam",
        "board examination",

        "heavy rainfall",
        "cyclone",
        "orange alert",

        "permanently closed",
        "permanently shut",
        "completely banned",
        "totally banned"
    ]

    found = []

    for phrase in phrases:

        if phrase in text:
            found.append(phrase)

    return found


# ============================================================
# CLAIM ACTIONS
# ============================================================

ACTION_GROUPS = {

    "release": [
        "released",
        "release",
        "publishes",
        "published",
        "publication",
        "issued",
        "issue"
    ],

    "announce": [
        "announced",
        "announce",
        "announcement",
        "declared",
        "declaration"
    ],

    "schedule": [
        "schedule",
        "scheduled",
        "timetable",
        "exam schedule",
        "examination schedule",
        "calendar",
        "academic calendar"
    ],

    "operate": [
        "operate",
        "operated",
        "operating",
        "will operate",
        "run",
        "running",
        "special trains"
    ],

    "open": [
        "open",
        "opened",
        "reopen",
        "reopened",
        "reopen",
        "resume",
        "resumed",
        "classes resume"
    ],

    "close": [
        "closed",
        "close",
        "closing",
        "shut",
        "shutdown",
        "closure"
    ],

    "ban": [
        "banned",
        "ban",
        "prohibited",
        "prohibition"
    ],

    "cancel": [
        "cancelled",
        "canceled",
        "cancel",
        "suspended",
        "suspension"
    ],

    "approve": [
        "approved",
        "approve",
        "approval"
    ],

    "start": [
        "started",
        "start",
        "began",
        "begin",
        "begins",
        "will begin"
    ]
}


def extract_claim_actions(text):

    text = normalize(text)

    actions = set()

    for action, words in ACTION_GROUPS.items():

        for word in words:

            if word in text:
                actions.add(action)
                break

    return actions


# ============================================================
# RESULT TEXT
# ============================================================

def get_result_text(result):

    return normalize(
        " ".join([
            result.get("title", ""),
            result.get("description", ""),
            result.get("source", "")
        ])
    )


# ============================================================
# TOPIC OVERLAP
# ============================================================

def calculate_topic_overlap(claim, result):

    claim_words = set(
        extract_keywords(claim)
    )

    result_words = set(
        extract_keywords(
            get_result_text(result)
        )
    )

    if not claim_words:
        return 0

    return len(
        claim_words.intersection(
            result_words
        )
    )


# ============================================================
# PHRASE OVERLAP
# ============================================================

def calculate_phrase_overlap(claim, result):

    claim_phrases = set(
        extract_important_phrases(claim)
    )

    result_text = get_result_text(result)

    count = 0

    for phrase in claim_phrases:

        if phrase in result_text:
            count += 1

    return count


# ============================================================
# ACTION OVERLAP
# ============================================================

def calculate_action_overlap(claim, result):

    claim_actions = extract_claim_actions(
        claim
    )

    result_actions = extract_claim_actions(
        get_result_text(result)
    )

    if not claim_actions:
        return 0

    return len(
        claim_actions.intersection(
            result_actions
        )
    )


# ============================================================
# NUMBER MATCH
# ============================================================

def extract_numbers(text):

    return set(
        re.findall(
            r"\b\d+(?:-\d+)?\b",
            normalize(text)
        )
    )


def number_overlap(claim, result):

    claim_numbers = extract_numbers(
        claim
    )

    result_numbers = extract_numbers(
        get_result_text(result)
    )

    if not claim_numbers:
        return 0

    return len(
        claim_numbers.intersection(
            result_numbers
        )
    )


# ============================================================
# ENTITY / SUBJECT MATCH
# ============================================================

def subject_match(claim, result):

    claim = normalize(claim)
    text = get_result_text(result)

    score = 0

    claim_type = detect_claim_type(
        claim
    )

    if claim_type == "school":

        if "tamil nadu" in text:
            score += 2

        if "school" in text or "schools" in text:
            score += 2

        if "school education" in text:
            score += 2

        if "government school" in text:
            score += 1

    elif claim_type == "college":

        if "tamil nadu" in text:
            score += 2

        if "college" in text:
            score += 3

    elif claim_type == "railway":

        if "railway" in text or "railways" in text:
            score += 3

        if "train" in text or "trains" in text:
            score += 2

    elif claim_type == "bank":

        if "bank" in text or "banking" in text:
            score += 3

    elif claim_type == "hospital":

        if "hospital" in text:
            score += 3

        if "health" in text:
            score += 1

    else:

        score = 1

    return score


# ============================================================
# TEMPORARY HOLIDAY PROTECTION
# ============================================================

def is_temporary_holiday_report(result):

    text = get_result_text(result)

    temporary_terms = [

        "holiday tomorrow",
        "school holiday tomorrow",
        "schools closed today",
        "schools closed tomorrow",
        "holiday due to rain",
        "closed due to heavy rain",
        "closed due to rainfall",
        "closed due to cyclone",
        "holiday due to cyclone",
        "holiday due to weather",
        "holiday extended",
        "reopening date"
    ]

    for term in temporary_terms:

        if term in text:
            return True

    return False


# ============================================================
# DATE RELEVANCE
# ============================================================

def date_is_relevant(claim, result):

    result_date = parse_result_date(
        result.get("date", "")
    )

    if not result_date:
        return True

    claim_date = extract_claim_date(
        claim
    )

    now = datetime.now(
        timezone.utc
    )

    # Future claim date
    if claim_date:

        # Evidence before claim can still support
        # if it is reasonably recent.
        if result_date < claim_date - timedelta(days=180):
            return False

    # Very old news should not be direct evidence
    if result_date < now - timedelta(days=450):
        return False

    return True


# ============================================================
# CLAIM-SPECIFIC CHECK
# ============================================================

def is_claim_specific(claim, result):

    text = get_result_text(result)

    topic = subject_match(
        claim,
        result
    )

    keyword_overlap = calculate_topic_overlap(
        claim,
        result
    )

    phrase_overlap = calculate_phrase_overlap(
        claim,
        result
    )

    action_overlap = calculate_action_overlap(
        claim,
        result
    )

    numbers = number_overlap(
        claim,
        result
    )

    claim_type = detect_claim_type(
        claim
    )

    # --------------------------------------------------------
    # SCHOOL
    # --------------------------------------------------------

    if claim_type == "school":

        entity_ok = (
            "tamil nadu" in text
            and (
                "school" in text
                or "schools" in text
            )
        )

        if not entity_ok:
            return False

        # Strong direct match
        if phrase_overlap >= 1 and action_overlap >= 1:
            return True

        # Very good keyword match
        if keyword_overlap >= 3 and action_overlap >= 1:
            return True

        # Exact department + action
        if (
            "school education" in text
            and action_overlap >= 1
            and keyword_overlap >= 2
        ):
            return True

        return False

    # --------------------------------------------------------
    # RAILWAY
    # --------------------------------------------------------

    if claim_type == "railway":

        entity_ok = (
            "railway" in text
            or "railways" in text
            or "train" in text
            or "trains" in text
        )

        if not entity_ok:
            return False

        if phrase_overlap >= 1 and action_overlap >= 1:
            return True

        if keyword_overlap >= 3 and action_overlap >= 1:
            return True

        return False

    # --------------------------------------------------------
    # COLLEGE
    # --------------------------------------------------------

    if claim_type == "college":

        if "college" not in text:
            return False

        if action_overlap >= 1 and keyword_overlap >= 2:
            return True

        if phrase_overlap >= 1:
            return True

        return False

    # --------------------------------------------------------
    # BANK
    # --------------------------------------------------------

    if claim_type == "bank":

        if "bank" not in text:
            return False

        if action_overlap >= 1 and keyword_overlap >= 2:
            return True

        return False

    # --------------------------------------------------------
    # HOSPITAL
    # --------------------------------------------------------

    if claim_type == "hospital":

        if "hospital" not in text:
            return False

        if action_overlap >= 1 and keyword_overlap >= 2:
            return True

        return False

    # --------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------

    return (
        keyword_overlap >= 4
        and action_overlap >= 1
    )


# ============================================================
# STRONG CLAIM SUPPORT CHECK
# ============================================================

def strong_claim_support(claim, result):

    strong, phrase = detect_strong_claim(
        claim
    )

    if not strong:
        return False

    text = get_result_text(result)

    # Source must contain equivalent strong language.
    strong_terms = [
        "permanently closed",
        "permanently shut",
        "closed permanently",
        "permanently banned",
        "completely banned",
        "totally banned"
    ]

    for term in strong_terms:

        if term in text:
            return True

    return False


# ============================================================
# DIRECT SUPPORT
# ============================================================

def is_direct_support(claim, result):

    if not date_is_relevant(
        claim,
        result
    ):
        return False

    if not is_claim_specific(
        claim,
        result
    ):
        return False

    if is_temporary_holiday_report(
        result
    ):
        return False

    strong, _ = detect_strong_claim(
        claim
    )

    action_overlap = calculate_action_overlap(
        claim,
        result
    )

    phrase_overlap = calculate_phrase_overlap(
        claim,
        result
    )

    keyword_overlap = calculate_topic_overlap(
        claim,
        result
    )

    # Strong claim needs matching strong language.
    if strong:

        return strong_claim_support(
            claim,
            result
        )

    # Normal claim.
    if phrase_overlap >= 1 and action_overlap >= 1:
        return True

    if action_overlap >= 1 and keyword_overlap >= 3:
        return True

    return False


# ============================================================
# OPERATIONAL EVIDENCE
# ============================================================

def operational_evidence(claim, result):

    text = get_result_text(result)

    claim_type = detect_claim_type(
        claim
    )

    if claim_type == "school":

        terms = [
            "quarterly exam",
            "quarterly examination",
            "examination schedule",
            "exam schedule",
            "academic calendar",
            "academic year",
            "working days",
            "school schedule",
            "school timings",
            "classes resume",
            "classes resumed",
            "schools reopen",
            "school reopen",
            "schools reopened",
            "schools are open",
            "schools remain open",
            "students attend",
            "students will attend",
            "schools will function",
            "schools functioning",
            "school functioning",
            "government schools",
            "government-aided schools"
        ]

    elif claim_type == "railway":

        terms = [
            "special trains",
            "special train",
            "trains will operate",
            "trains operate",
            "railways will operate",
            "railways operate",
            "additional trains",
            "extra trains",
            "passenger demand",
            "train services"
        ]

    elif claim_type == "college":

        terms = [
            "classes",
            "academic calendar",
            "semester",
            "examination",
            "college reopen",
            "colleges reopen"
        ]

    else:

        terms = []

    found = []

    for term in terms:

        if term in text:
            found.append(term)

    return found


# ============================================================
# CONTRADICTION
# ============================================================

def is_contradicting_source(claim, result):

    strong, strong_phrase = detect_strong_claim(
        claim
    )

    if not strong:
        return False

    if not date_is_relevant(
        claim,
        result
    ):
        return False

    if not is_claim_specific(
        claim,
        result
    ):
        return False

    # Temporary holiday article should NOT contradict
    # permanent closure.
    if is_temporary_holiday_report(
        result
    ):
        return False

    operational = operational_evidence(
        claim,
        result
    )

    if not operational:
        return False

    return True


# ============================================================
# FACT CHECK SPECIFICITY
# ============================================================

FACT_CHECK_WORDS = [
    "fact check",
    "fact-check",
    "factcheck",
    "fake claim",
    "false claim",
    "false news",
    "fake news",
    "hoax",
    "debunked",
    "misleading",
    "incorrect",
    "not true",
    "denied"
]


def is_fact_check_article(result):

    text = get_result_text(
        result
    )

    for word in FACT_CHECK_WORDS:

        if word in text:
            return True

    return False


def is_specific_fact_check(claim, result):

    if not is_fact_check_article(
        result
    ):
        return False

    if not date_is_relevant(
        claim,
        result
    ):
        return False

    if not is_claim_specific(
        claim,
        result
    ):
        return False

    topic = calculate_topic_overlap(
        claim,
        result
    )

    phrase = calculate_phrase_overlap(
        claim,
        result
    )

    action = calculate_action_overlap(
        claim,
        result
    )

    # Fact-check needs stronger matching than ordinary
    # supporting evidence.

    if phrase >= 1 and action >= 1:
        return True

    if topic >= 4 and action >= 1:
        return True

    # Exact strong claim language
    strong, strong_phrase = detect_strong_claim(
        claim
    )

    if strong and strong_phrase in get_result_text(result):
        return True

    return False


# ============================================================
# SOURCE TRUST
# ============================================================

def is_trusted_source(result):

    source = normalize(
        result.get("source", "")
    )

    title = normalize(
        result.get("title", "")
    )

    combined = source + " " + title

    for trusted in TRUSTED_SOURCES:

        if trusted in combined:
            return True

    return False


# ============================================================
# SOURCE SCORE
# ============================================================

def source_quality(result):

    source = normalize(
        result.get("source", "")
    )

    for trusted in TRUSTED_SOURCES:

        if trusted in source:
            return 2

    return 0


# ============================================================
# MATCH SCORE
# ============================================================

def calculate_match_score(
    claim,
    results
):

    score = 0

    for result in results:

        topic = calculate_topic_overlap(
            claim,
            result
        )

        phrase = calculate_phrase_overlap(
            claim,
            result
        )

        action = calculate_action_overlap(
            claim,
            result
        )

        score += topic
        score += phrase * 3
        score += action * 2

        if is_trusted_source(result):
            score += 2

    return score


# ============================================================
# QUERY BUILDER
# ============================================================

def build_queries(news):

    claim_type = detect_claim_type(
        news
    )

    queries = []

    # Exact claim
    queries.append(news)

    important = extract_important_phrases(
        news
    )

    keywords = extract_keywords(
        news
    )

    # Exact important phrase
    if important:

        queries.append(
            " ".join(
                important[:4]
            )
        )

    # Keyword search
    if keywords:

        queries.append(
            " ".join(
                keywords[:8]
            )
        )

    # Type-specific searches

    if claim_type == "school":

        queries.extend([
            "Tamil Nadu school education department 2026-27",
            "Tamil Nadu schools quarterly examination schedule 2026-27",
            "Tamil Nadu quarterly examination schedule released 2026",
            "Tamil Nadu school academic calendar 2026-27",
            "Tamil Nadu schools current status September 2026"
        ])

    elif claim_type == "railway":

        queries.extend([
            "Indian Railways special trains 2026",
            "Indian Railways additional trains 2026",
            "Ganpati special trains 2026",
            "railway passenger demand special trains 2026"
        ])

    elif claim_type == "college":

        queries.extend([
            "Tamil Nadu colleges current status 2026",
            "Tamil Nadu college academic calendar 2026"
        ])

    # Fact-check search
    queries.append(
        news + " fact check"
    )

    # Latest update
    queries.append(
        news + " latest update"
    )

    # Official
    queries.append(
        news + " official"
    )

    # Remove duplicates
    final = []

    seen = set()

    for q in queries:

        q = q.strip()

        key = normalize(q)

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        final.append(q)

    return final[:12]


# ============================================================
# EVIDENCE BUILDER
# ============================================================

def make_evidence_item(
    result,
    evidence_type,
    description
):

    return {
        "type": evidence_type,
        "title": result.get(
            "title",
            ""
        ),
        "source": result.get(
            "source",
            ""
        ),
        "date": result.get(
            "date",
            ""
        ),
        "link": result.get(
            "link",
            ""
        ),
        "description": description
    }


# ============================================================
# MAIN VERIFICATION
# ============================================================

def verify_news(news_text):

    news_text = news_text.strip()

    if not news_text:

        return {
            "status": "UNCERTAIN",
            "confidence": 40,
            "message": "Please enter some news to verify.",
            "why": "No news claim was provided.",
            "evidence": [],
            "sources": [],
            "related_sources": [],
            "ignored_sources": [],
            "trusted_count": 0,
            "matched_sources": 0,
            "match_score": 0
        }

    print("\n")
    print("===================================")
    print("TRUTHLENS AI LIVE VERIFICATION V12")
    print("===================================")
    print("CLAIM:")
    print(news_text)
    print("-----------------------------------")

    queries = build_queries(
        news_text
    )

    all_results = []

    for query in queries:

        print("SEARCH:", query)

        results = search_news(
            query,
            limit=8
        )

        all_results.extend(
            results
        )

    all_results = remove_duplicates(
        all_results
    )

    print("-----------------------------------")
    print(
        "TOTAL SEARCH RESULTS:",
        len(all_results)
    )

    direct_support = []
    contradictions = []
    fact_checks = []
    related_results = []
    ignored_results = []

    # ========================================================
    # CLASSIFY RESULTS
    # ========================================================

    for result in all_results:

        claim_specific = is_claim_specific(
            news_text,
            result
        )

        date_ok = date_is_relevant(
            news_text,
            result
        )

        direct = is_direct_support(
            news_text,
            result
        )

        contradiction = is_contradicting_source(
            news_text,
            result
        )

        fact_check = is_specific_fact_check(
            news_text,
            result
        )

        # ----------------------------------------------------
        # FACT CHECK
        # ----------------------------------------------------

        if fact_check:

            fact_checks.append(
                result
            )

            continue

        # ----------------------------------------------------
        # CONTRADICTION
        # ----------------------------------------------------

        if contradiction:

            contradictions.append(
                result
            )

            continue

        # ----------------------------------------------------
        # DIRECT SUPPORT
        # ----------------------------------------------------

        if direct:

            direct_support.append(
                result
            )

            continue

        # ----------------------------------------------------
        # RELATED
        # ----------------------------------------------------

        if claim_specific or (
            calculate_topic_overlap(
                news_text,
                result
            ) >= 2
        ):

            related_results.append(
                result
            )

            continue

        # ----------------------------------------------------
        # IGNORED
        # ----------------------------------------------------

        ignored_results.append(
            result
        )

    # Remove duplicates from categories
    direct_support = remove_duplicates(
        direct_support
    )

    contradictions = remove_duplicates(
        contradictions
    )

    fact_checks = remove_duplicates(
        fact_checks
    )

    related_results = remove_duplicates(
        related_results
    )

    ignored_results = remove_duplicates(
        ignored_results
    )

    # ========================================================
    # TRUSTED COUNTS
    # ========================================================

    trusted_support = sum(
        1
        for r in direct_support
        if is_trusted_source(r)
    )

    trusted_contradiction = sum(
        1
        for r in contradictions
        if is_trusted_source(r)
    )

    trusted_factcheck = sum(
        1
        for r in fact_checks
        if is_trusted_source(r)
    )

    # ========================================================
    # EVIDENCE
    # ========================================================

    evidence = []

    # Contradictions first
    for result in contradictions[:5]:

        evidence.append(
            make_evidence_item(
                result,
                "CONTRADICTION",
                "The source contains current operational information that conflicts with the specific claim."
            )
        )

    # Specific fact checks
    for result in fact_checks[:5]:

        evidence.append(
            make_evidence_item(
                result,
                "FACT CHECK",
                "The source is a claim-specific fact-check related to the submitted claim."
            )
        )

    # Supporting evidence
    for result in direct_support[:8]:

        evidence.append(
            make_evidence_item(
                result,
                "SUPPORTING",
                "The source directly matches the claim's subject and action."
            )
        )

    # ========================================================
    # FINAL DECISION
    # ========================================================

    strong_claim, strong_phrase = detect_strong_claim(
        news_text
    )

    # --------------------------------------------------------
    # 1. STRONG CONTRADICTION
    # --------------------------------------------------------

    if len(contradictions) >= 2:

        if trusted_contradiction >= 1:

            status = "LIKELY FAKE"
            confidence = 97

            message = (
                "Multiple current sources contradict "
                "the specific claim."
            )

            why = (
                "Current claim-specific reports contain "
                "operational evidence that conflicts with "
                "the claim."
            )

        else:

            status = "LIKELY FAKE"
            confidence = 88

            message = (
                "Multiple claim-specific reports contradict "
                "the claim."
            )

            why = (
                "More than one current claim-specific source "
                "contradicts the submitted claim."
            )

    # --------------------------------------------------------
    # 2. SPECIFIC FACT CHECK
    # --------------------------------------------------------

    elif len(fact_checks) >= 1:

        # Important:
        # Fact check only reaches here if it passed
        # strict claim-specific validation.

        if trusted_factcheck >= 1:

            status = "MISLEADING"
            confidence = 90

            message = (
                "A claim-specific fact-check was found."
            )

            why = (
                "A trusted source contains a fact-check "
                "directly related to the submitted claim."
            )

        else:

            status = "MISLEADING"
            confidence = 82

            message = (
                "A claim-specific fact-check was found."
            )

            why = (
                "A source contains a fact-check that "
                "directly relates to the submitted claim."
            )

    # --------------------------------------------------------
    # 3. STRONG DIRECT SUPPORT
    # --------------------------------------------------------

    elif strong_claim:

        # Strong claims require matching permanent language.
        strong_support = [
            r for r in direct_support
            if strong_claim_support(
                news_text,
                r
            )
        ]

        trusted_strong = sum(
            1
            for r in strong_support
            if is_trusted_source(r)
        )

        if len(strong_support) >= 3 and trusted_strong >= 2:

            status = "LIKELY REAL"
            confidence = 95

            message = (
                "Multiple current sources directly support "
                "the strong claim."
            )

            why = (
                "The claim's specific strong action and scope "
                "are directly matched by multiple trusted sources."
            )

        elif len(strong_support) >= 2:

            status = "LIKELY REAL"
            confidence = 88

            message = (
                "Current claim-specific sources support "
                "the strong claim."
            )

            why = (
                "More than one source directly matches "
                "the specific strong claim."
            )

        else:

            status = "UNCERTAIN"
            confidence = 40

            message = (
                "There is not enough direct evidence "
                "to verify this strong claim."
            )

            why = (
                "The claim makes a strong statement, but "
                "the search did not find enough direct "
                "claim-specific evidence."
            )

    # --------------------------------------------------------
    # 4. NORMAL DIRECT SUPPORT
    # --------------------------------------------------------

    elif (
        len(direct_support) >= 3
        and trusted_support >= 2
    ):

        status = "LIKELY REAL"
        confidence = 92

        message = (
            "Multiple current sources directly support "
            "the claim."
        )

        why = (
            "Several recent sources directly match the "
            "claim's subject and action, including "
            "trusted-source coverage."
        )

    elif (
        len(direct_support) >= 2
        and trusted_support >= 1
    ):

        status = "LIKELY REAL"
        confidence = 88

        message = (
            "Current claim-specific sources support "
            "the claim."
        )

        why = (
            "Recent sources directly match the claim's "
            "subject and action, with trusted-source support."
        )

    elif len(direct_support) >= 2:

        status = "LIKELY REAL"
        confidence = 80

        message = (
            "Multiple claim-specific sources support "
            "the claim."
        )

        why = (
            "More than one recent source directly matches "
            "the claim."
        )

    # --------------------------------------------------------
    # 5. UNCERTAIN
    # --------------------------------------------------------

    else:

        status = "UNCERTAIN"
        confidence = 40

        if related_results:

            message = (
                "Related information was found, but there "
                "is not enough direct evidence to verify the claim."
            )

            why = (
                "The search found articles about the same "
                "general topic, but they do not directly "
                "confirm or contradict the specific claim. "
                "Therefore, they were not treated as direct evidence."
            )

        else:

            message = (
                "No reliable direct evidence was found."
            )

            why = (
                "The search did not find enough recent "
                "claim-specific evidence to confirm or "
                "contradict the claim."
            )

    # ========================================================
    # CURRENT SOURCES
    # ========================================================

    current_sources = []

    combined_sources = (
        contradictions
        + fact_checks
        + direct_support
    )

    combined_sources = remove_duplicates(
        combined_sources
    )

    for result in combined_sources[:5]:

        current_sources.append(
            result
        )

    # ========================================================
    # MATCH SCORE
    # ========================================================

    match_results = (
        contradictions
        + fact_checks
        + direct_support
    )

    match_score = calculate_match_score(
        news_text,
        match_results
    )

    # ========================================================
    # PRINT RESULT
    # ========================================================

    print("\n")
    print("===================================")
    print("FINAL RESULT")
    print("===================================")

    print(
        "STATUS:",
        status
    )

    print(
        "CONFIDENCE:",
        confidence
    )

    print(
        "DIRECT EVIDENCE:",
        len(direct_support)
    )

    print(
        "CONTRADICTIONS:",
        len(contradictions)
    )

    print(
        "FACT CHECKS:",
        len(fact_checks)
    )

    print(
        "RELATED REPORTS:",
        len(related_results)
    )

    print(
        "IGNORED REPORTS:",
        len(ignored_results)
    )

    print(
        "TRUSTED SUPPORT:",
        trusted_support
    )

    print(
        "MATCH SCORE:",
        match_score
    )

    print("\nWHY:")
    print(why)

    print("\nEVIDENCE:")

    for item in evidence[:10]:

        print(
            "[",
            item["type"],
            "]",
            item["title"]
        )

        print(
            "SOURCE:",
            item["source"]
        )

        print(
            "DATE:",
            item["date"]
        )

    print("===================================")

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "status": status,

        "confidence": confidence,

        "message": message,

        "why": why,

        "evidence": evidence,

        "sources": current_sources,

        "related_sources": related_results[:5],

        "ignored_sources": ignored_results[:5],

        "trusted_count": (
            trusted_support
            + trusted_contradiction
            + trusted_factcheck
        ),

        "matched_sources": (
            len(direct_support)
            + len(contradictions)
            + len(fact_checks)
        ),

        "match_score": match_score
    }


# ============================================================
# DIRECT TEST MODE
# ============================================================

if __name__ == "__main__":

    print()
    print("==============================================")
    print(" TRUTHLENS AI - LIVE VERIFIER V12 TEST")
    print("==============================================")

    test_claim = input(
        "\nEnter news claim:\n> "
    ).strip()

    if test_claim:

        result = verify_news(
            test_claim
        )

        print("\n")
        print("==============================================")
        print("FINAL RESULT")
        print("==============================================")
        print(
            "STATUS:",
            result["status"]
        )
        print(
            "CONFIDENCE:",
            result["confidence"]
        )
        print(
            "DIRECT EVIDENCE:",
            len(result["evidence"])
        )
        print(
            "RELATED REPORTS:",
            len(result["related_sources"])
        )
        print(
            "IGNORED REPORTS:",
            len(result["ignored_sources"])
        )
        print(
            "WHY:",
            result["why"]
        )
        print("==============================================")