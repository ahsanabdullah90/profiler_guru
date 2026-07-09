"""Assessment framework definitions."""

from typing import Any

FRAMEWORKS: dict[str, dict[str, Any]] = {
    "communication_style": {
        "id": "communication_style",
        "label": "Communication Style",
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

FRAMEWORK_IDS = list(FRAMEWORKS.keys())
DEFAULT_FRAMEWORK = "communication_style"


def get_framework(framework_id: str) -> dict[str, Any] | None:
    return FRAMEWORKS.get(framework_id)


def get_dimension_ids(framework_id: str) -> list[str]:
    fw = FRAMEWORKS.get(framework_id)
    if not fw:
        return []
    return [d["id"] for d in fw["dimensions"]]
