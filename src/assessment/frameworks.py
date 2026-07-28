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
             "description": "Uses straightforward vs indirect language",
             "rubric": {
                 "1-2": "Nearly always indirect; avoids stating needs or opinions clearly; relies on hints and implication",
                 "3-4": "Often indirect; occasionally states opinions but with hedging or softening",
                 "5-6": "Balanced directness; states views clearly when needed but uses tact in sensitive topics",
                 "7-8": "Consistently direct; communicates needs and opinions unambiguously while remaining respectful",
                 "9-10": "Highly direct and candid; uses clear, unambiguous language even in difficult conversations without aggression"
             }},
            {"id": "expressiveness", "label": "Expressiveness",
             "description": "Emotional expression and vocabulary range",
             "rubric": {
                 "1-2": "Minimal emotional expression; responses are terse or purely factual; limited vocabulary range",
                 "3-4": "Occasional emotional expression; vocabulary is functional but not varied",
                 "5-6": "Regular emotional expression with moderate vocabulary range; uses emojis or punctuation for tone",
                 "7-8": "Frequently expressive; varied vocabulary; comfortable conveying a range of emotions through text",
                 "9-10": "Highly expressive with rich vocabulary; articulates complex emotional states and nuances fluently"
             }},
            {"id": "responsiveness", "label": "Responsiveness",
             "description": "Response timing, engagement, and reciprocation",
             "rubric": {
                 "1-2": "Rarely responds in a timely manner; frequent unreciprocated messages; low engagement",
                 "3-4": "Inconsistent responsiveness; sometimes engaged, sometimes delayed or minimal",
                 "5-6": "Generally responsive; reciprocates most conversational turns; engagement matches context",
                 "7-8": "Consistently responsive and engaged; timely replies; actively reciprocates and builds on topics",
                 "9-10": "Highly attuned responsiveness; near-immediate engagement; consistently matches and elevates conversational energy"
             }},
            {"id": "formality", "label": "Formality",
             "description": "Formal vs casual register and structure",
             "rubric": {
                 "1-2": "Exclusively casual; slang, abbreviations, minimal punctuation or capitalization",
                 "3-4": "Mostly casual but adjusts tone slightly when context demands it",
                 "5-6": "Flexible register; comfortable with both casual and formal tones depending on context",
                 "7-8": "Predominantly formal or structured language; careful punctuation and complete sentences",
                 "9-10": "Consistently formal register with structured paragraphs; high linguistic precision and etiquette"
             }},
            {"id": "conflict_style", "label": "Conflict Style",
             "description": "How disagreement, tension, or correction is handled",
             "rubric": {
                 "1-2": "Avoidant or escalating; either withdraws from disagreement or responds with hostility/defensiveness",
                 "3-4": "Tends toward avoidance or discomfort with tension; may deflect rather than address directly",
                 "5-6": "Constructive approach; addresses disagreements calmly and seeks resolution without escalation",
                 "7-8": "Skilled conflict handler; raises concerns directly with empathy; de-escalates tension effectively",
                 "9-10": "Exceptional at navigating disagreement; invites open dialogue, validates opposing views, and strengthens relationships through conflict resolution"
             }},
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
             "description": "Intellectual curiosity, creativity, preference for variety",
             "rubric": {
                 "1-2": "Narrow conversational range; resists new topics or perspectives; prefers routine subjects",
                 "3-4": "Occasionally engages with new ideas but mostly stays within familiar conversational territory",
                 "5-6": "Shows curiosity; explores varied topics; open to new perspectives when introduced",
                 "7-8": "Actively seeks novel topics and diverse viewpoints; intellectually curious across multiple domains",
                 "9-10": "Highly exploratory mindset; consistently introduces novel ideas, abstract thinking, and creative perspectives"
             }},
            {"id": "conscientiousness", "label": "Conscientiousness",
             "description": "Organization, dependability, discipline in communication",
             "rubric": {
                 "1-2": "Messages lack structure; frequent typos, incomplete thoughts; inconsistent follow-through",
                 "3-4": "Some organization but inconsistent; occasionally follows up or completes conversational threads",
                 "5-6": "Generally organized communication; follows through on commitments; messages are coherent and structured",
                 "7-8": "Well-structured messages; reliable follow-through on conversational tasks; thoughtful responses",
                 "9-10": "Meticulous communication; highly organized, structured, and reliable; consistently follows up with precision"
             }},
            {"id": "extraversion", "label": "Extraversion",
             "description": "Sociability, energy, engagement in conversation",
             "rubric": {
                 "1-2": "Minimal initiation; predominantly reactive; brief responses that don't invite further discussion",
                 "3-4": "Occasionally initiates but usually responds; moderate energy in conversation",
                 "5-6": "Regularly initiates and engages; comfortable with back-and-forth; shows conversational energy",
                 "7-8": "Frequently initiates topics; high conversational energy; actively draws others into discussion",
                 "9-10": "Consistently high social energy; initiates frequently; animated conversational style that energizes interactions"
             }},
            {"id": "agreeableness", "label": "Agreeableness",
             "description": "Cooperation, warmth, politeness, harmony-seeking",
             "rubric": {
                 "1-2": "Frequently dismissive, argumentative, or indifferent to others' perspectives",
                 "3-4": "Occasionally cooperative but can be blunt or dismissive when disagreeing",
                 "5-6": "Generally warm and cooperative; polite and considerate in most interactions",
                 "7-8": "Consistently warm and accommodating; actively seeks harmony and validates others' views",
                 "9-10": "Highly compassionate and conciliatory; prioritizes harmony, shows exceptional warmth and cooperative spirit"
             }},
            {"id": "neuroticism", "label": "Neuroticism",
             "description": "Emotional sensitivity, negative affect, reactivity",
             "rubric": {
                 "1-2": "Consistently even-keeled; very low expression of negative emotion or reactivity",
                 "3-4": "Occasional mild negative expressions but generally emotionally stable",
                 "5-6": "Moderate emotional reactivity; expresses both positive and negative emotions appropriately",
                 "7-8": "Frequently expresses worry, frustration, or emotional sensitivity; reactive to interpersonal stressors",
                 "9-10": "High emotional reactivity; frequent expressions of anxiety, frustration, or distress; easily triggered by minor events"
             }},
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
             "description": "Consistent, warm, comfortable communication",
             "rubric": {
                 "1-2": "Rarely shows comfort or consistency; communication feels guarded or unpredictable",
                 "3-4": "Occasional warmth but inconsistent; some comfort in communication but with notable reservations",
                 "5-6": "Generally warm and consistent; communicates comfort with intimacy and maintains stable engagement",
                 "7-8": "Consistently warm, open, and comfortable; handles closeness without anxiety or withdrawal",
                 "9-10": "Highly secure communication; effortlessly warm, consistently available, comfortable with both closeness and autonomy"
             }},
            {"id": "anxious", "label": "Anxious",
             "description": "Reassurance-seeking, worry, over-communication",
             "rubric": {
                 "1-2": "No signs of reassurance-seeking or worry; self-assured communication style",
                 "3-4": "Occasional subtle reassurance-seeking or mild worry about connection",
                 "5-6": "Noticeable reassurance-seeking patterns; asks about relationship status or availability",
                 "7-8": "Frequent reassurance-seeking; worried about responses or availability; over-interprets delays",
                 "9-10": "Intense anxiety patterns; persistent seeking of confirmation; distress over perceived distance or delay"
             }},
            {"id": "avoidant", "label": "Avoidant",
             "description": "Emotional distance, dismissive, reluctance",
             "rubric": {
                 "1-2": "Open and engaged; no signs of emotional distance or dismissal of closeness",
                 "3-4": "Occasional brief responses to emotional topics; mild preference for surface-level conversation",
                 "5-6": "Regularly deflects emotional depth; prefers practical or factual topics over personal sharing",
                 "7-8": "Consistently avoids emotional or intimate topics; dismissive of relationship talk; noticeably distant",
                 "9-10": "Strongly avoids closeness; dismisses or minimizes emotional needs; actively maintains distance through brevity or deflection"
             }},
            {"id": "disorganized", "label": "Disorganized",
             "description": "Erratic, inconsistent, contradictory patterns",
             "rubric": {
                 "1-2": "Consistent, predictable communication; no erratic or contradictory patterns",
                 "3-4": "Occasional minor inconsistency but generally coherent communication style",
                 "5-6": "Noticeable shifts between warm and distant behavior; some contradictory responses",
                 "7-8": "Frequent contradictory patterns; alternates between seeking and rejecting connection",
                 "9-10": "Highly erratic communication; dramatic shifts from closeness to distance; confused or contradictory attachment behavior"
             }},
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
             "description": "Reflects on own feelings, labels emotions, takes responsibility",
             "rubric": {
                 "1-2": "Rarely reflects on own feelings or behavior; no emotional labeling; avoids responsibility",
                 "3-4": "Occasional reflection on emotions; limited emotional vocabulary; takes responsibility infrequently",
                 "5-6": "Regularly reflects on feelings; labels basic emotions; takes responsibility when warranted",
                 "7-8": "Frequently introspective; articulates nuanced emotional states; consistently owns mistakes",
                 "9-10": "Deep self-awareness; precisely labels complex emotions; proactively reflects on behavior patterns and their impact on others"
             }},
            {"id": "self_regulation", "label": "Self-regulation",
             "description": "Manages impulses, de-escalates, stays calm",
             "rubric": {
                 "1-2": "Frequent impulsive reactions; escalates tension; difficulty managing frustration in messages",
                 "3-4": "Occasional loss of composure; some impulse control but can be reactive under stress",
                 "5-6": "Generally manages impulses well; de-escalates when needed; maintains composure in most situations",
                 "7-8": "Consistently calm and measured; effectively de-escalates tense moments; thoughtful rather than reactive",
                 "9-10": "Exceptional self-regulation; remains composed under pressure; transforms potential conflict into constructive dialogue"
             }},
            {"id": "motivation", "label": "Motivation",
             "description": "Goal-oriented language, optimism, persistence",
             "rubric": {
                 "1-2": "Little goal-directed language; expresses pessimism or resignation; abandons topics quickly",
                 "3-4": "Occasional goal-oriented statements but limited persistence; mixed optimism",
                 "5-6": "Regularly expresses goals and aspirations; maintains conversation threads; generally optimistic tone",
                 "7-8": "Consistently goal-focused; persists through conversational lulls; expresses clear aspirations and hope",
                 "9-10": "Strongly driven; articulates clear goals with action plans; maintains optimism and persistence even when discussing challenges"
             }},
            {"id": "empathy", "label": "Empathy",
             "description": "Validates others, perspective-taking, attunement",
             "rubric": {
                 "1-2": "Rarely acknowledges others' feelings; responses are self-focused or dismissive of emotional content",
                 "3-4": "Occasionally recognizes feelings but rarely validates; limited perspective-taking",
                 "5-6": "Regularly validates others' emotions; shows perspective-taking; some emotional attunement",
                 "7-8": "Consistently validates and empathizes; uses analogies to show understanding; anticipates emotional needs",
                 "9-10": "Deep emotional attunement across conversations; validates without prompting; frequently takes others' perspective with specific, genuine responses"
             }},
            {"id": "social_skills", "label": "Social Skills",
             "description": "Turn-taking, rapport building, conflict management",
             "rubric": {
                 "1-2": "Awkward turn-taking; limited rapport building; struggles with conversational flow",
                 "3-4": "Functional but basic social skills; maintains conversation but limited rapport depth",
                 "5-6": "Good conversational flow; builds rapport through shared references and appropriate humor",
                 "7-8": "Skilled communicator; smooth turn-taking; builds strong rapport; manages relationship dynamics well",
                 "9-10": "Exceptional social facility; effortlessly builds deep rapport; navigates complex interpersonal dynamics with natural skill"
             }},
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
