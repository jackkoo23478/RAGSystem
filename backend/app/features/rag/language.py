import re

from opencc import OpenCC

_CJK = re.compile(r"[㐀-䶿一-鿿]")
_to_traditional = OpenCC("s2t")  # characters only: wording (and Cantonese words) stay as they are

# Characters that OpenCC "converts" although they are right in traditional and in Cantonese text: 台灣 would become 臺灣, 蒙哥馬里 馬裏,
# the Cantonese 吓 晒 响 became 嚇 曬 響, and 郁 (to move) became 鬱 (depressed), which changes the meaning. They are the characters
# that s2t changed in text that is already traditional: DRCD (Traditional Chinese Wikipedia), the Cantonese Wikipedia (those that changed
# 40 times or more: fewer are simplified text that sits in the articles, like 国 学 广) and the documents of this project.
# A simplified text that uses one of them (这里) keeps it: a few characters stay unconverted, but correct text is never damaged.
_KEEP = frozenset(
    "台群吓里布占响峰托郁周秘晒涌岩范咸了干游征伙余制准岳唇咤床于厘才核采后吃杰面回栗辟弦搜斗家朴局并痴凶合庄云具只巨系灶念表雇栖熏私昆咨困注胆卷夸致升腊沄咽症疴欲满"
)


def is_chinese(text: str) -> bool:
    """True when the text has any Chinese character. A question that mixes English words into Chinese counts as Chinese."""
    return _CJK.search(text) is not None


def to_traditional(text: str) -> str:
    """Simplified characters become traditional ones; traditional, Cantonese and English text is left as it is.
    The model sometimes writes simplified characters, and a prompt can not stop that without side effects."""
    converted = _to_traditional.convert(text)
    if converted == text or len(converted) != len(text):
        return converted
    return "".join(original if original in _KEEP else new for original, new in zip(text, converted))
