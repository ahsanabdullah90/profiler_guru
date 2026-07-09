"""Per-framework knowledge-base query strings."""

from src.assessment.frameworks import FRAMEWORKS


def get_kb_query(framework_id: str) -> str:
    fw = FRAMEWORKS.get(framework_id)
    if fw:
        return fw["kb_query"]
    return "linguistic style, emotional sentiment, attachment type, personality traits"
