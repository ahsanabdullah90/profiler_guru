"""Assessment framework definitions."""

from typing import Any

FRAMEWORKS: dict[str, dict[str, Any]] = {
    "communication_style": {
        "id": "communication_style",
        "label": "Conversation Pattern Analysis",
        "description": (
            "Analyze communication patterns: directness, expressiveness, "
            "responsiveness, formality, and conflict style."
        ),
        "dimensions": [
            {"id": "directness", "label": "Directness",
             "description": "Uses straightforward vs indirect language"},
            {"id": "expressiveness", "label": "Expressiveness",
             "description": "Emotional expression and vocabulary range"},
            {"id": "responsiveness", "label": "Responsiveness",
             "description": "Response timing, engagement, and reciprocation"},
            {"id": "formality", "label": "Formality",
             "description": "Formal vs casual register and structure"},
            {"id": "conflict_style", "label": "Conflict Style",
             "description": "How disagreement, tension, or correction is handled"},
        ],
        "chart_type": "bars",
        "kb_query": (
            "communication patterns, linguistic style, conversational analysis, "
            "discourse markers, turn-taking"
        ),
    },
    "big_five": {
        "id": "big_five",
        "label": "Big Five / OCEAN",
        "description": (
            "Score on Openness, Conscientiousness, Extraversion, "
            "Agreeableness, and Neuroticism based on linguistic markers."
        ),
        "dimensions": [
            {"id": "openness", "label": "Openness",
             "description": "Intellectual curiosity, creativity, preference for variety"},
            {"id": "conscientiousness", "label": "Conscientiousness",
             "description": "Organization, dependability, discipline in communication"},
            {"id": "extraversion", "label": "Extraversion",
             "description": "Sociability, energy, engagement in conversation"},
            {"id": "agreeableness", "label": "Agreeableness",
             "description": "Cooperation, warmth, politeness, harmony-seeking"},
            {"id": "neuroticism", "label": "Neuroticism",
             "description": "Emotional sensitivity, negative affect, reactivity"},
        ],
        "chart_type": "radar",
        "kb_query": (
            "Big Five personality traits, OCEAN model, "
            "linguistic markers of personality traits"
        ),
    },
    "attachment": {
        "id": "attachment",
        "label": "Attachment Style",
        "description": (
            "Identify attachment patterns: Secure, Anxious, Avoidant, "
            "or Disorganized based on DM communication."
        ),
        "dimensions": [
            {"id": "secure", "label": "Secure",
             "description": "Consistent, warm, comfortable communication"},
            {"id": "anxious", "label": "Anxious",
             "description": "Reassurance-seeking, worry, over-communication"},
            {"id": "avoidant", "label": "Avoidant",
             "description": "Emotional distance, dismissive, reluctance"},
            {"id": "disorganized", "label": "Disorganized",
             "description": "Erratic, inconsistent, contradictory patterns"},
        ],
        "chart_type": "classification",
        "kb_query": (
            "attachment theory, attachment styles, Bowlby, Ainsworth, "
            "secure anxious avoidant disorganized"
        ),
    },
    "emotional_intelligence": {
        "id": "emotional_intelligence",
        "label": "Emotional Intelligence (Goleman)",
        "description": (
            "Assess Self-awareness, Self-regulation, Motivation, Empathy, "
            "and Social Skills from text communication."
        ),
        "dimensions": [
            {"id": "self_awareness", "label": "Self-awareness",
             "description": "Reflects on own feelings, labels emotions, takes responsibility"},
            {"id": "self_regulation", "label": "Self-regulation",
             "description": "Manages impulses, de-escalates, stays calm"},
            {"id": "motivation", "label": "Motivation",
             "description": "Goal-oriented language, optimism, persistence"},
            {"id": "empathy", "label": "Empathy",
             "description": "Validates others, perspective-taking, attunement"},
            {"id": "social_skills", "label": "Social Skills",
             "description": "Turn-taking, rapport building, conflict management"},
        ],
        "chart_type": "bars",
        "kb_query": (
            "emotional intelligence, Goleman, self-regulation, "
            "empathy, social skills communication"
        ),
    },
}

# ── Clinical screening instruments (kind="questionnaire") ─────────────────

CLINICAL_INSTRUMENTS: dict[str, dict[str, Any]] = {
    "phq9": {
        "id": "phq9",
        "label": "PHQ-9",
        "full_label": "PHQ-9 Depression Screening",
        "kind": "questionnaire",
        "description": "Patient Health Questionnaire-9 — depression severity over the past 2 weeks.",
        "scoring": "sum",
        "items": [
            {"id": "q1", "prompt": "Little interest or pleasure in doing things",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q2", "prompt": "Feeling down, depressed, or hopeless",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q3", "prompt": "Trouble falling or staying asleep, or sleeping too much",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q4", "prompt": "Feeling tired or having little energy",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q5", "prompt": "Poor appetite or overeating",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q6", "prompt": "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q7", "prompt": "Trouble concentrating on things, such as reading the newspaper or watching television",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q8", "prompt": "Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q9", "prompt": "Thoughts that you would be better off dead, or of hurting yourself",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "More than half the days"}, {"value": 3, "label": "Nearly every day"}]},
        ],
        "cut_points": [
            {"min": 0, "max": 4, "label": "Minimal"},
            {"min": 5, "max": 9, "label": "Mild"},
            {"min": 10, "max": 14, "label": "Moderate"},
            {"min": 15, "max": 19, "label": "Moderately Severe"},
            {"min": 20, "max": 27, "label": "Severe"},
        ],
        "chart_type": "band_total",
    },
    "gad7": {
        "id": "gad7",
        "label": "GAD-7",
        "full_label": "GAD-7 Anxiety Screening",
        "kind": "questionnaire",
        "description": "Generalized Anxiety Disorder-7 — anxiety severity over the past 2 weeks.",
        "scoring": "sum",
        "items": [
            {"id": "q1", "prompt": "Feeling nervous, anxious, or on edge",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "Over half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q2", "prompt": "Not being able to stop or control worrying",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "Over half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q3", "prompt": "Worrying too much about different things",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "Over half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q4", "prompt": "Trouble relaxing",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "Over half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q5", "prompt": "Being so restless that it is hard to sit still",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "Over half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q6", "prompt": "Becoming easily annoyed or irritable",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "Over half the days"}, {"value": 3, "label": "Nearly every day"}]},
            {"id": "q7", "prompt": "Feeling afraid, as if something awful might happen",
             "responses": [{"value": 0, "label": "Not at all"}, {"value": 1, "label": "Several days"},
                           {"value": 2, "label": "Over half the days"}, {"value": 3, "label": "Nearly every day"}]},
        ],
        "cut_points": [
            {"min": 0, "max": 4, "label": "Minimal"},
            {"min": 5, "max": 9, "label": "Mild"},
            {"min": 10, "max": 14, "label": "Moderate"},
            {"min": 15, "max": 21, "label": "Severe"},
        ],
        "chart_type": "band_total",
    },
    "bhs": {
        "id": "bhs",
        "label": "BHS",
        "full_label": "Beck Hopelessness Scale",
        "kind": "questionnaire",
        "description": "Beck Hopelessness Scale — hopelessness severity (20 yes/no items).",
        "scoring": "sum",
        "items": [
            {"id": "q1", "prompt": "I look forward to the future with hope and enthusiasm.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q2", "prompt": "I might as well give up because I cannot make things better for myself.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q3", "prompt": "When things are going badly, I am helped by knowing they cannot stay that way forever.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q4", "prompt": "I cannot imagine what my life would be like in 10 years.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q5", "prompt": "I have enough time to accomplish the things I want to do.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q6", "prompt": "In the future, I expect to succeed in what concerns me most.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q7", "prompt": "My future seems dark to me.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q8", "prompt": "I happen to be particularly lucky, and I expect to get more of the good things in life than the average person.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q9", "prompt": "I just cannot get the breaks, and there is no reason I will in the future.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q10", "prompt": "My past experiences have prepared me well for the future.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q11", "prompt": "All I can see ahead of me is unpleasantness rather than pleasantness.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q12", "prompt": "I do not expect to get what I really want.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q13", "prompt": "When I look ahead to the future, I expect I will be happier than I am now.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q14", "prompt": "Things just do not work out the way I want them to.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q15", "prompt": "I have great faith in the future.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q16", "prompt": "I never get what I want, so it is foolish to want anything.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q17", "prompt": "It is very unlikely that I will get any real satisfaction in the future.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q18", "prompt": "The future seems vague and uncertain to me.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
            {"id": "q19", "prompt": "I can look forward to more good times than bad times.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}]},
            {"id": "q20", "prompt": "There is no use in really trying to get something I want because I probably will not get it.", "responses": [{"value": 0, "label": "False"}, {"value": 1, "label": "True"}], "reverse": True},
        ],
        "cut_points": [
            {"min": 0, "max": 3, "label": "Normal"},
            {"min": 4, "max": 8, "label": "Mild"},
            {"min": 9, "max": 14, "label": "Moderate"},
            {"min": 15, "max": 20, "label": "Severe"},
        ],
        "chart_type": "band_total",
    },
}

# Merge clinical instruments into main FRAMEWORKS dict
FRAMEWORKS.update(CLINICAL_INSTRUMENTS)

DEFAULT_FRAMEWORK = "communication_style"


def get_framework(framework_id: str) -> dict[str, Any] | None:
    return FRAMEWORKS.get(framework_id)


def get_dimension_ids(framework_id: str) -> list[str]:
    fw = FRAMEWORKS.get(framework_id)
    if not fw:
        return []
    return [d["id"] for d in fw["dimensions"]]


def get_framework_hash(framework_id: str) -> str:
    """Return a short deterministic SHA-256 hex digest of the framework definition.
    Changes only if the framework's structure, labels, or dimensions change.
    Used to tie historical assessment scores to the exact scale version.
    """
    import hashlib
    import json
    fw = FRAMEWORKS.get(framework_id, {})
    canonical = json.dumps(fw, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]
