# Scoring Rubrics Reference

This document documents the anchored scoring rubrics used by Profile_Guru's assessment pipeline. Rubrics are injected into the LLM prompt as reference anchors to calibrate scores across dimensions.

> **Important:** These rubrics are adapted from established psychological frameworks and validated instruments (EQ-i 2.0, NEO-PI-R, ECR-R, interpersonal communication research) for text-based analysis. They are **not** validated instruments themselves — scores reflect observed language patterns, not clinical measurement.

---

## Communication Style

### Directness
| Score | Anchor |
|-------|--------|
| 1–2 | Nearly always indirect; avoids stating needs or opinions clearly; relies on hints and implication |
| 3–4 | Often indirect; occasionally states opinions but with hedging or softening |
| 5–6 | Balanced directness; states views clearly when needed but uses tact in sensitive topics |
| 7–8 | Consistently direct; communicates needs and opinions unambiguously while remaining respectful |
| 9–10 | Highly direct and candid; uses clear, unambiguous language even in difficult conversations without aggression |

### Expressiveness
| Score | Anchor |
|-------|--------|
| 1–2 | Minimal emotional expression; responses are terse or purely factual; limited vocabulary range |
| 3–4 | Occasional emotional expression; vocabulary is functional but not varied |
| 5–6 | Regular emotional expression with moderate vocabulary range; uses emojis or punctuation for tone |
| 7–8 | Frequently expressive; varied vocabulary; comfortable conveying a range of emotions through text |
| 9–10 | Highly expressive with rich vocabulary; articulates complex emotional states and nuances fluently |

### Responsiveness
| Score | Anchor |
|-------|--------|
| 1–2 | Rarely responds in a timely manner; frequent unreciprocated messages; low engagement |
| 3–4 | Inconsistent responsiveness; sometimes engaged, sometimes delayed or minimal |
| 5–6 | Generally responsive; reciprocates most conversational turns; engagement matches context |
| 7–8 | Consistently responsive and engaged; timely replies; actively reciprocates and builds on topics |
| 9–10 | Highly attuned responsiveness; near-immediate engagement; consistently matches and elevates conversational energy |

### Formality
| Score | Anchor |
|-------|--------|
| 1–2 | Exclusively casual; slang, abbreviations, minimal punctuation or capitalization |
| 3–4 | Mostly casual but adjusts tone slightly when context demands it |
| 5–6 | Flexible register; comfortable with both casual and formal tones depending on context |
| 7–8 | Predominantly formal or structured language; careful punctuation and complete sentences |
| 9–10 | Consistently formal register with structured paragraphs; high linguistic precision and etiquette |

### Conflict Style
| Score | Anchor |
|-------|--------|
| 1–2 | Avoidant or escalating; either withdraws from disagreement or responds with hostility/defensiveness |
| 3–4 | Tends toward avoidance or discomfort with tension; may deflect rather than address directly |
| 5–6 | Constructive approach; addresses disagreements calmly and seeks resolution without escalation |
| 7–8 | Skilled conflict handler; raises concerns directly with empathy; de-escalates tension effectively |
| 9–10 | Exceptional at navigating disagreement; invites open dialogue, validates opposing views, and strengthens relationships through conflict resolution |

---

## Big Five / OCEAN

### Openness
| Score | Anchor |
|-------|--------|
| 1–2 | Narrow conversational range; resists new topics or perspectives; prefers routine subjects |
| 3–4 | Occasionally engages with new ideas but mostly stays within familiar conversational territory |
| 5–6 | Shows curiosity; explores varied topics; open to new perspectives when introduced |
| 7–8 | Actively seeks novel topics and diverse viewpoints; intellectually curious across multiple domains |
| 9–10 | Highly exploratory mindset; consistently introduces novel ideas, abstract thinking, and creative perspectives |

### Conscientiousness
| Score | Anchor |
|-------|--------|
| 1–2 | Messages lack structure; frequent typos, incomplete thoughts; inconsistent follow-through |
| 3–4 | Some organization but inconsistent; occasionally follows up or completes conversational threads |
| 5–6 | Generally organized communication; follows through on commitments; messages are coherent and structured |
| 7–8 | Well-structured messages; reliable follow-through on conversational tasks; thoughtful responses |
| 9–10 | Meticulous communication; highly organized, structured, and reliable; consistently follows up with precision |

### Extraversion
| Score | Anchor |
|-------|--------|
| 1–2 | Minimal initiation; predominantly reactive; brief responses that don't invite further discussion |
| 3–4 | Occasionally initiates but usually responds; moderate energy in conversation |
| 5–6 | Regularly initiates and engages; comfortable with back-and-forth; shows conversational energy |
| 7–8 | Frequently initiates topics; high conversational energy; actively draws others into discussion |
| 9–10 | Consistently high social energy; initiates frequently; animated conversational style that energizes interactions |

### Agreeableness
| Score | Anchor |
|-------|--------|
| 1–2 | Frequently dismissive, argumentative, or indifferent to others' perspectives |
| 3–4 | Occasionally cooperative but can be blunt or dismissive when disagreeing |
| 5–6 | Generally warm and cooperative; polite and considerate in most interactions |
| 7–8 | Consistently warm and accommodating; actively seeks harmony and validates others' views |
| 9–10 | Highly compassionate and conciliatory; prioritizes harmony, shows exceptional warmth and cooperative spirit |

### Neuroticism
| Score | Anchor |
|-------|--------|
| 1–2 | Consistently even-keeled; very low expression of negative emotion or reactivity |
| 3–4 | Occasional mild negative expressions but generally emotionally stable |
| 5–6 | Moderate emotional reactivity; expresses both positive and negative emotions appropriately |
| 7–8 | Frequently expresses worry, frustration, or emotional sensitivity; reactive to interpersonal stressors |
| 9–10 | High emotional reactivity; frequent expressions of anxiety, frustration, or distress; easily triggered by minor events |

---

## Attachment Style

### Secure
| Score | Anchor |
|-------|--------|
| 1–2 | Rarely shows comfort or consistency; communication feels guarded or unpredictable |
| 3–4 | Occasional warmth but inconsistent; some comfort in communication but with notable reservations |
| 5–6 | Generally warm and consistent; communicates comfort with intimacy and maintains stable engagement |
| 7–8 | Consistently warm, open, and comfortable; handles closeness without anxiety or withdrawal |
| 9–10 | Highly secure communication; effortlessly warm, consistently available, comfortable with both closeness and autonomy |

### Anxious
| Score | Anchor |
|-------|--------|
| 1–2 | No signs of reassurance-seeking or worry; self-assured communication style |
| 3–4 | Occasional subtle reassurance-seeking or mild worry about connection |
| 5–6 | Noticeable reassurance-seeking patterns; asks about relationship status or availability |
| 7–8 | Frequent reassurance-seeking; worried about responses or availability; over-interprets delays |
| 9–10 | Intense anxiety patterns; persistent seeking of confirmation; distress over perceived distance or delay |

### Avoidant
| Score | Anchor |
|-------|--------|
| 1–2 | Open and engaged; no signs of emotional distance or dismissal of closeness |
| 3–4 | Occasional brief responses to emotional topics; mild preference for surface-level conversation |
| 5–6 | Regularly deflects emotional depth; prefers practical or factual topics over personal sharing |
| 7–8 | Consistently avoids emotional or intimate topics; dismissive of relationship talk; noticeably distant |
| 9–10 | Strongly avoids closeness; dismisses or minimizes emotional needs; actively maintains distance through brevity or deflection |

### Disorganized
| Score | Anchor |
|-------|--------|
| 1–2 | Consistent, predictable communication; no erratic or contradictory patterns |
| 3–4 | Occasional minor inconsistency but generally coherent communication style |
| 5–6 | Noticeable shifts between warm and distant behavior; some contradictory responses |
| 7–8 | Frequent contradictory patterns; alternates between seeking and rejecting connection |
| 9–10 | Highly erratic communication; dramatic shifts from closeness to distance; confused or contradictory attachment behavior |

---

## Emotional Intelligence (Goleman)

### Self-awareness
| Score | Anchor |
|-------|--------|
| 1–2 | Rarely reflects on own feelings or behavior; no emotional labeling; avoids responsibility |
| 3–4 | Occasional reflection on emotions; limited emotional vocabulary; takes responsibility infrequently |
| 5–6 | Regularly reflects on feelings; labels basic emotions; takes responsibility when warranted |
| 7–8 | Frequently introspective; articulates nuanced emotional states; consistently owns mistakes |
| 9–10 | Deep self-awareness; precisely labels complex emotions; proactively reflects on behavior patterns and their impact on others |

### Self-regulation
| Score | Anchor |
|-------|--------|
| 1–2 | Frequent impulsive reactions; escalates tension; difficulty managing frustration in messages |
| 3–4 | Occasional loss of composure; some impulse control but can be reactive under stress |
| 5–6 | Generally manages impulses well; de-escalates when needed; maintains composure in most situations |
| 7–8 | Consistently calm and measured; effectively de-escalates tense moments; thoughtful rather than reactive |
| 9–10 | Exceptional self-regulation; remains composed under pressure; transforms potential conflict into constructive dialogue |

### Motivation
| Score | Anchor |
|-------|--------|
| 1–2 | Little goal-directed language; expresses pessimism or resignation; abandons topics quickly |
| 3–4 | Occasional goal-oriented statements but limited persistence; mixed optimism |
| 5–6 | Regularly expresses goals and aspirations; maintains conversation threads; generally optimistic tone |
| 7–8 | Consistently goal-focused; persists through conversational lulls; expresses clear aspirations and hope |
| 9–10 | Strongly driven; articulates clear goals with action plans; maintains optimism and persistence even when discussing challenges |

### Empathy
| Score | Anchor |
|-------|--------|
| 1–2 | Rarely acknowledges others' feelings; responses are self-focused or dismissive of emotional content |
| 3–4 | Occasionally recognizes feelings but rarely validates; limited perspective-taking |
| 5–6 | Regularly validates others' emotions; shows perspective-taking; some emotional attunement |
| 7–8 | Consistently validates and empathizes; uses analogies to show understanding; anticipates emotional needs |
| 9–10 | Deep emotional attunement across conversations; validates without prompting; frequently takes others' perspective with specific, genuine responses |

### Social Skills
| Score | Anchor |
|-------|--------|
| 1–2 | Awkward turn-taking; limited rapport building; struggles with conversational flow |
| 3–4 | Functional but basic social skills; maintains conversation but limited rapport depth |
| 5–6 | Good conversational flow; builds rapport through shared references and appropriate humor |
| 7–8 | Skilled communicator; smooth turn-taking; builds strong rapport; manages relationship dynamics well |
| 9–10 | Exceptional social facility; effortlessly builds deep rapport; navigates complex interpersonal dynamics with natural skill |
