"""Per-framework modular step definitions for the sequential synthesis (small-model) pipeline.

Each step has:
- id: unique within its framework
- label: human-readable for UI progress display
- needs_logs: whether it requires raw chat logs or only prior context
- system: system prompt for this step
- user: user prompt template using {chat_logs}, {context}, and standard template vars
- output_key: key to store the step output in the shared state
- max_chars: maximum chat log characters for steps that read logs (None = use default)
"""

from typing import Any

# ── Shared step fragments ──────────────────────────────────────────────
_LINGUISTIC_SYSTEM = (
    "You are a linguistic communication analyst. Extract concise, "
    "specific linguistic features from text messages."
)
_LINGUISTIC_USER = (
    "Extract the 5-7 most distinctive linguistic features from these messages. "
    "Focus on: vocabulary choices, sentence structure patterns, punctuation usage, "
    "repeated phrases or emojis, and unique expressions.\n\n"
    "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
    "Output a concise bullet list of features. For each, give a label, "
    "one example quote, and a brief explanation."
)

_TONE_SYSTEM = (
    "You are a communication analyst specializing in conversational tone "
    "and emotional expression patterns."
)
_TONE_USER = (
    "Analyze the conversational tone, emotional expression patterns, "
    "and responsiveness in these messages. Describe: "
    "the overall energy level, emotional range, how the contact handles "
    "positive vs negative topics, and their typical response style "
    "(elaborate vs brief, engaged vs detached).\n\n"
    "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
    "Prior linguistic analysis:\n{context}\n\n"
    "Output a concise paragraph."
)

# ── Framework step definitions ─────────────────────────────────────────

STEP_DEFS: dict[str, list[dict[str, Any]]] = {
    # ===================== Communication Style =========================
    "communication_style": [
        {
            "id": "linguistic_features",
            "label": "Linguistic Features",
            "needs_logs": True,
            "system": _LINGUISTIC_SYSTEM,
            "user": _LINGUISTIC_USER,
            "output_key": "linguistic_features",
        },
        {
            "id": "tone_responsiveness",
            "label": "Tone & Responsiveness",
            "needs_logs": True,
            "system": _TONE_SYSTEM,
            "user": _TONE_USER,
            "output_key": "tone_analysis",
        },
        {
            "id": "conflict_style",
            "label": "Conflict & Regulation",
            "needs_logs": True,
            "system": (
                "You are a communication conflict analyst. "
                "Analyze how disagreement and tension are handled in text conversations."
            ),
            "user": (
                "Analyze how this contact handles disagreement, tension, or criticism. "
                "Look for: "
                "whether they engage or withdraw from conflict, "
                "their tone when disagreeing, "
                "whether they apologize or escalate, "
                "and how they respond to your direct questions or corrections.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "conflict_analysis",
        },
        {
            "id": "scoring",
            "label": "Scoring Dimensions",
            "needs_logs": False,
            "system": (
                "You are a communication assessment specialist. "
                "Score communication style dimensions based on prior analysis."
            ),
            "user": (
                "Based on the analyses below, score this contact on each "
                "communication style dimension (1-10). Use the rubric anchors below to calibrate your scoring.\n\n"
                "Contact: {name}\n\n"
                "ANALYSES:\n{context}\n\n"
                "RUBRIC ANCHORS:\n{rubric_anchors}\n\n"
                "For each dimension provide: score, confidence (0.0-1.0), evidence count.\n\n"
                "CONFIDENCE RULES:\n"
                "- evidence_count: Number of distinct messages supporting your score (minimum 3)\n"
                "- confidence: Your certainty in this score (0.0-1.0)\n"
                "  - 0.9-1.0: Multiple clear examples across different conversations\n"
                "  - 0.7-0.8: Several supporting examples, consistent pattern\n"
                "  - 0.5-0.6: Limited examples or mixed signals\n"
                "  - Below 0.5: Insufficient evidence — flag as unreliable\n\n"
                "At the very beginning, embed a score block:\n"
                "<!-- SCORES: {{\"directness\": {{\"score\": 7, \"confidence\": 0.8, \"evidence_count\": 5}}, \"expressiveness\": {{\"score\": 5, \"confidence\": 0.6, \"evidence_count\": 3}}}} -->\n"
                "Then for each dimension, provide a one-sentence justification with a quote."
            ),
            "output_key": "scores",
        },
        {
            "id": "synthesis",
            "label": "Synthesizing Report",
            "needs_logs": False,
            "system": (
                "You are a communication assessment writer. "
                "Produce the final assessment report — do not comment on or review the analyses."
            ),
            "user": (
                "{kb_context}"
                "Using the analyses below, write the final communication style "
                "assessment report for {name}. Output ONLY the report — do not "
                "mention, praise, or critique the prior analyses.\n\n"
                "The report MUST include:\n"
                "- A score block at the very beginning: "
                "<!-- SCORES: {{...}} -->\n"
                "- 2-3 paragraphs covering overall communication profile, "
                "key strengths and challenges\n"
                "- Practical recommendations for communicating with this contact\n\n"
                "ANALYSES:\n{context}"
            ),
            "output_key": "final",
        },
    ],

    # ===================== Big Five / OCEAN ============================
    "big_five": [
        {
            "id": "linguistic_features",
            "label": "Linguistic Markers",
            "needs_logs": True,
            "system": _LINGUISTIC_SYSTEM,
            "user": _LINGUISTIC_USER,
            "output_key": "linguistic_features",
        },
        {
            "id": "social_engagement",
            "label": "Social Engagement",
            "needs_logs": True,
            "system": (
                "You are a behavioral analyst studying social engagement "
                "patterns in text communication."
            ),
            "user": (
                "Analyze this contact's social engagement patterns. "
                "Look for: "
                "how often they initiate vs react, "
                "their openness to new discussion topics, "
                "whether they ask questions and show curiosity, "
                "their turn-taking and conversational flow, "
                "and their energy level in conversations.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior linguistic analysis:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "social_analysis",
        },
        {
            "id": "emotion_patterns",
            "label": "Emotion & Cooperation",
            "needs_logs": True,
            "system": (
                "You are a behavioral analyst studying emotional patterns "
                "and cooperation in text communication."
            ),
            "user": (
                "Analyze the emotional patterns and cooperation style. "
                "Look for: "
                "frequency and intensity of negative emotion expressions, "
                "cooperative vs competitive language, "
                "politeness and warmth markers, "
                "reactivity to stress or frustration, "
                "and how they handle requests or expectations.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "emotion_analysis",
        },
        {
            "id": "scoring",
            "label": "Big Five Scoring",
            "needs_logs": False,
            "system": (
                "You are a personality assessment specialist in the Big Five (OCEAN) model. "
                "Score personality traits based on prior analysis."
            ),
            "user": (
                "Based on the analyses below, score this contact on each "
                "Big Five personality trait (1-10). Use the rubric anchors below to calibrate your scoring.\n\n"
                "Contact: {name}\n\n"
                "ANALYSES:\n{context}\n\n"
                "RUBRIC ANCHORS:\n{rubric_anchors}\n\n"
                "For each trait provide: score, confidence (0.0-1.0), evidence count.\n\n"
                "CONFIDENCE RULES:\n"
                "- evidence_count: Number of distinct messages supporting your score (minimum 3)\n"
                "- confidence: Your certainty in this score (0.0-1.0)\n"
                "  - 0.9-1.0: Multiple clear examples across different conversations\n"
                "  - 0.7-0.8: Several supporting examples, consistent pattern\n"
                "  - 0.5-0.6: Limited examples or mixed signals\n"
                "  - Below 0.5: Insufficient evidence — flag as unreliable\n\n"
                "At the very beginning, embed a score block:\n"
                "<!-- SCORES: {{\"openness\": {{\"score\": 6, \"confidence\": 0.7, \"evidence_count\": 4}}, \"conscientiousness\": {{\"score\": 7, \"confidence\": 0.8, \"evidence_count\": 5}}}} -->\n"
                "Then for each trait, provide a one-sentence justification with a quote."
            ),
            "output_key": "scores",
        },
        {
            "id": "synthesis",
            "label": "Synthesizing Report",
            "needs_logs": False,
            "system": (
                "You are a personality assessment writer. "
                "Produce the final Big Five report — do not comment on or review the analyses."
            ),
            "user": (
                "{kb_context}"
                "Using the analyses below, write the final Big Five personality "
                "profile for {name}. Output ONLY the report — do not mention, "
                "praise, or critique the prior analyses.\n\n"
                "The report MUST include:\n"
                "- A score block at the very beginning: "
                "<!-- SCORES: {{...}} -->\n"
                "- 2-3 paragraphs covering the most prominent traits, "
                "how they manifest in communication, and the trait combination story\n\n"
                "ANALYSES:\n{context}"
            ),
            "output_key": "final",
        },
    ],

    # ===================== Attachment Style ============================
    "attachment": [
        {
            "id": "linguistic_features",
            "label": "Communication Patterns",
            "needs_logs": True,
            "system": _LINGUISTIC_SYSTEM,
            "user": (
                "Extract the 5-7 most distinctive communication patterns from these messages. "
                "Focus on: the contact's typical message length, emotional language use, "
                "how they start and end conversations, "
                "their use of questions vs statements, and any repetitive patterns.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Output a concise bullet list."
            ),
            "output_key": "linguistic_features",
        },
        {
            "id": "responsiveness",
            "label": "Responsiveness Patterns",
            "needs_logs": True,
            "system": (
                "You are an attachment communication analyst. "
                "Analyze responsiveness and engagement patterns in messages."
            ),
            "user": (
                "Analyze the contact's responsiveness patterns. "
                "Look for: "
                "response timing (quick vs delayed), "
                "message length consistency, "
                "who typically initiates and ends conversations, "
                "how they respond when you share something personal, "
                "and whether they match your conversational energy.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analysis:\n{context}\n\n"
                "Output a concise paragraph."
            ),
            "output_key": "responsiveness_analysis",
        },
        {
            "id": "anxious_markers",
            "label": "Reassurance-Seeking",
            "needs_logs": True,
            "system": (
                "You are an attachment pattern analyst. "
                "Identify reassurance-seeking and anxiety markers in text messages."
            ),
            "user": (
                "Analyze these messages for reassurance-seeking and anxiety markers. "
                "Look for: frequent questions seeking confirmation, "
                "worry expressed about the relationship or your availability, "
                "over-communication when you take time to respond, "
                "seeking validation or approval, "
                "and expressions of uncertainty about where things stand.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific evidence."
            ),
            "output_key": "anxious_analysis",
        },
        {
            "id": "avoidant_markers",
            "label": "Distance Patterns",
            "needs_logs": True,
            "system": (
                "You are an attachment pattern analyst. "
                "Identify emotional distance and avoidance markers in text messages."
            ),
            "user": (
                "Analyze these messages for emotional distance and avoidance markers. "
                "Look for: deflecting emotional or personal topics, "
                "giving brief or dismissive responses to emotional sharing, "
                "changing subjects away from feelings or relationship talk, "
                "inconsistency in engagement (hot/cold), "
                "and reluctance to make plans or commitments.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific evidence."
            ),
            "output_key": "avoidant_analysis",
        },
        {
            "id": "scoring",
            "label": "Attachment Classification",
            "needs_logs": False,
            "system": (
                "You are an attachment theory specialist. "
                "Classify attachment style based on communication pattern analysis."
            ),
            "user": (
                "Based on the analyses below, classify the attachment style and "
                "rate each style dimension (1-10). Use the rubric anchors below to calibrate your scoring.\n\n"
                "Contact: {name}\n\n"
                "ANALYSES:\n{context}\n\n"
                "RUBRIC ANCHORS:\n{rubric_anchors}\n\n"
                "For each dimension provide: score, confidence (0.0-1.0), evidence count.\n\n"
                "CONFIDENCE RULES:\n"
                "- evidence_count: Number of distinct messages supporting your score (minimum 3)\n"
                "- confidence: Your certainty in this score (0.0-1.0)\n"
                "  - 0.9-1.0: Multiple clear examples across different conversations\n"
                "  - 0.7-0.8: Several supporting examples, consistent pattern\n"
                "  - 0.5-0.6: Limited examples or mixed signals\n"
                "  - Below 0.5: Insufficient evidence — flag as unreliable\n\n"
                "At the very beginning, embed:\n"
                "<!-- SCORES: {{\"secure\": {{\"score\": 7, \"confidence\": 0.8, \"evidence_count\": 5}}, \"anxious\": {{\"score\": 4, \"confidence\": 0.6, \"evidence_count\": 3}}}} -->\n"
                "<!-- CLASSIFICATION: Secure -->\n\n"
                "Then provide your reasoning and evidence."
            ),
            "output_key": "scores",
        },
        {
            "id": "synthesis",
            "label": "Synthesizing Report",
            "needs_logs": False,
            "system": (
                "You are an attachment assessment writer. "
                "Produce the final attachment style report — do not comment on or review the analyses."
            ),
            "user": (
                "{kb_context}"
                "Using the analyses below, write the final attachment style "
                "assessment report for {name}. Output ONLY the report — do not "
                "mention, praise, or critique the prior analyses.\n\n"
                "The report MUST include:\n"
                "- A score block at the very beginning: "
                "<!-- SCORES: {{...}} -->\n"
                "- A classification line: <!-- CLASSIFICATION: ... -->\n"
                "- 2-3 paragraphs of behavioral evidence from the chat logs\n"
                "- A dimension breakdown (Secure, Anxious, Avoidant, Disorganized) "
                "with scores and justification\n"
                "- Practical communication recommendations\n\n"
                "ANALYSES:\n{context}"
            ),
            "output_key": "final",
        },
    ],

    # ===================== Emotional Intelligence ======================
    "emotional_intelligence": [
        {
            "id": "linguistic_features",
            "label": "Communication Patterns",
            "needs_logs": True,
            "system": _LINGUISTIC_SYSTEM,
            "user": _LINGUISTIC_USER,
            "output_key": "linguistic_features",
        },
        {
            "id": "self_awareness",
            "label": "Self-Awareness",
            "needs_logs": True,
            "system": (
                "You are an emotional intelligence analyst. "
                "Identify self-awareness markers in text communication."
            ),
            "user": (
                "Analyze these messages for self-awareness markers. "
                "Look for: reflecting on own feelings or reactions, "
                "naming or labeling emotions, "
                "taking responsibility for mistakes or tone, "
                "acknowledging personal limitations, "
                "and recognizing how their behavior affects others.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analysis:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "self_awareness_analysis",
        },
        {
            "id": "self_regulation",
            "label": "Self-Regulation",
            "needs_logs": True,
            "system": (
                "You are an emotional intelligence analyst. "
                "Identify self-regulation markers in text communication."
            ),
            "user": (
                "Analyze these messages for self-regulation markers. "
                "Look for: staying calm when topics get tense, "
                "de-escalating rather than escalating conflict, "
                "pausing or stepping back instead of reacting impulsively, "
                "managing frustration constructively, "
                "and apologizing or correcting when they overreact.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "self_regulation_analysis",
        },
        {
            "id": "motivation",
            "label": "Motivation",
            "needs_logs": True,
            "system": (
                "You are an emotional intelligence analyst. "
                "Identify motivation and goal-orientation markers in text communication."
            ),
            "user": (
                "Analyze these messages for motivation and goal-orientation. "
                "Look for: goal-directed language and planning, "
                "optimism and positive framing of challenges, "
                "persistence in conversation topics, "
                "initiative in moving conversations forward, "
                "and expressions of personal standards or aspirations.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "motivation_analysis",
        },
        {
            "id": "empathy",
            "label": "Empathy",
            "needs_logs": True,
            "system": (
                "You are an emotional intelligence analyst. "
                "Identify empathy markers in text communication."
            ),
            "user": (
                "Analyze these messages for empathy markers. "
                "Look for: validating the other person's feelings or experiences, "
                "perspective-taking and seeing things from your point of view, "
                "acknowledging your concerns or emotions, "
                "asking follow-up questions that show genuine interest, "
                "and offering emotional support or comfort.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "empathy_analysis",
        },
        {
            "id": "social_skills",
            "label": "Social Skills",
            "needs_logs": True,
            "system": (
                "You are an emotional intelligence analyst. "
                "Identify social skills markers in text communication."
            ),
            "user": (
                "Analyze these messages for social skills and rapport building. "
                "Look for: smooth turn-taking and conversational flow, "
                "rapport-building language (humor, warmth, shared references), "
                "skillful handling of social awkwardness or disagreements, "
                "adapting communication style to the situation, "
                "and managing the overall relationship dynamic.\n\n"
                "Contact: {name}\n\nCHAT LOGS:\n{chat_logs}\n\n"
                "Prior analyses:\n{context}\n\n"
                "Output a concise paragraph with specific examples."
            ),
            "output_key": "social_skills_analysis",
        },
        {
            "id": "scoring",
            "label": "EI Scoring",
            "needs_logs": False,
            "system": (
                "You are an emotional intelligence assessment specialist in the Goleman framework. "
                "Score EI competencies based on prior analysis."
            ),
            "user": (
                "Based on the analyses below, score this contact on each "
                "Goleman emotional intelligence competency (1-10). Use the rubric anchors below to calibrate your scoring.\n\n"
                "Contact: {name}\n\n"
                "ANALYSES:\n{context}\n\n"
                "RUBRIC ANCHORS:\n{rubric_anchors}\n\n"
                "For each competency provide: score, confidence (0.0-1.0), evidence count.\n\n"
                "CONFIDENCE RULES:\n"
                "- evidence_count: Number of distinct messages supporting your score (minimum 3)\n"
                "- confidence: Your certainty in this score (0.0-1.0)\n"
                "  - 0.9-1.0: Multiple clear examples across different conversations\n"
                "  - 0.7-0.8: Several supporting examples, consistent pattern\n"
                "  - 0.5-0.6: Limited examples or mixed signals\n"
                "  - Below 0.5: Insufficient evidence — flag as unreliable\n\n"
                "At the very beginning, embed a score block:\n"
                "<!-- SCORES: {{\"self_awareness\": {{\"score\": 6, \"confidence\": 0.7, \"evidence_count\": 4}}, \"self_regulation\": {{\"score\": 7, \"confidence\": 0.8, \"evidence_count\": 5}}}} -->\n"
                "Then for each competency, provide a one-sentence justification with a quote."
            ),
            "output_key": "scores",
        },
        {
            "id": "synthesis",
            "label": "Synthesizing Report",
            "needs_logs": False,
            "system": (
                "You are an emotional intelligence report writer. "
                "Produce the final EI report — do not comment on or review the analyses."
            ),
            "user": (
                "{kb_context}"
                "Using the analyses below, write the final emotional intelligence "
                "assessment report for {name}. Output ONLY the report — do not "
                "mention, praise, or critique the prior analyses.\n\n"
                "The report MUST include:\n"
                "- A score block at the very beginning: "
                "<!-- SCORES: {{...}} -->\n"
                "- 2-3 paragraphs covering the strongest and weakest competencies, "
                "behavioral evidence for each, and development recommendations\n\n"
                "ANALYSES:\n{context}"
            ),
            "output_key": "final",
        },
    ],
}


def get_modular_steps(framework_id: str) -> list[dict[str, Any]] | None:
    return STEP_DEFS.get(framework_id)
