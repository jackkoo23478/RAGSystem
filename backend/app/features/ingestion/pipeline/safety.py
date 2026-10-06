import re

# Phrases that are almost only ever written to manipulate an AI model.
# One of these is enough to flag a document.
STRONG = {
    "ignore-previous-instructions": r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all)\b.{0,30}\b(instructions?|rules?|prompts?|directions?)\b",
    "zh-ignore-instructions": r"(忽略|無視|无视|忘記|忘记).{0,6}(以上|之前|上面|先前|所有).{0,6}(指示|指令|規則|规则|提示)",
}

# Phrases that also appear in normal documents. Two or more are needed to flag a document.
WEAK = {
    "reply-only-with": r"\b(reply|respond|answer)\s+only\s+with\b",
    "system-notice": r"\bsystem\s+(notice|prompt|override)\b",
    "new-rule": r"\bnew\s+(rule|instructions?)\s*[:\-]",
    "do-not-mention": r"\bdo\s+not\s+(mention|reveal|tell)\b.{0,30}\b(this|these)\b",
    "zh-you-are-now": r"(你而家|你现在|你現在)(係|是)",
}

_STRONG = {name: re.compile(pattern, re.I | re.S) for name, pattern in STRONG.items()}
_WEAK = {name: re.compile(pattern, re.I | re.S) for name, pattern in WEAK.items()}


def scan_for_injection(text: str) -> list[str]:
    """Names of the injection signals found, or [] when the text looks fine.

    This is a speed bump, not a wall: a paraphrase or spaced-out letters get past it,
    and a document that merely quotes an attack is flagged. Flagged documents are
    held for an admin to review.
    """
    flat = " ".join(text.split())  # line breaks and runs of spaces must not hide a phrase
    strong = [name for name, rx in _STRONG.items() if rx.search(flat)]
    weak = [name for name, rx in _WEAK.items() if rx.search(flat)]
    if strong or len(weak) >= 2:
        return strong + weak
    return []
