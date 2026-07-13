import re

CLOUD_PATTERNS = [
    re.compile(r"^gpt-", re.I),
    re.compile(r"^o1-", re.I),
    re.compile(r"^o3-", re.I),
    re.compile(r"^claude-", re.I),
    re.compile(r"^gemini-(1\.5|2\.0)-(pro|flash)", re.I),
    re.compile(r"^gemini-(pro|flash)-\d", re.I),
]

LARGE_PATTERNS = [
    re.compile(r"gpt-4", re.I),
    re.compile(r"gpt-4o", re.I),
    re.compile(r"o1", re.I),
    re.compile(r"o3", re.I),
    re.compile(r"claude-3", re.I),
    re.compile(r"claude-sonnet", re.I),
    re.compile(r"claude-opus", re.I),
    re.compile(r"gemini-(1\.5|2\.0)-(pro|flash)", re.I),
    re.compile(r"llama3(\.1)?:70b", re.I),
    re.compile(r"llama3:405b", re.I),
    re.compile(r"mixtral:8x22b", re.I),
    re.compile(r"qwen2\.5:72b", re.I),
    re.compile(r"qwen3:\d+b", re.I),
    re.compile(r"gemma2:27b", re.I),
    re.compile(r"gemma3", re.I),
]

MEDIUM_PATTERNS = [
    re.compile(r"llama3(\.1)?:8b", re.I),
    re.compile(r"llama3(\.1)?:13b", re.I),
    re.compile(r"mistral-", re.I),
    re.compile(r"mixtral:8x7b", re.I),
    re.compile(r"qwen2\.5:(14b|32b)", re.I),
    re.compile(r"phi3:14b", re.I),
    re.compile(r"codestral", re.I),
    re.compile(r"dbrx", re.I),
]


def is_cloud_model(name: str) -> bool:
    if not name:
        return False
    return any(p.search(name) for p in CLOUD_PATTERNS)


def classify_model(name: str) -> str:
    if not name:
        return "small"
    if any(p.search(name) for p in LARGE_PATTERNS):
        return "large"
    if any(p.search(name) for p in MEDIUM_PATTERNS):
        return "medium"
    return "small"
