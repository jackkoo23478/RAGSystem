from app.features.rag.language import is_chinese, to_traditional


def test_english_is_not_chinese():
    assert not is_chinese("How many leave days?")
    assert not is_chinese("")
    assert not is_chinese("12345 - refund?")


def test_any_chinese_character_makes_it_chinese():
    assert is_chinese("年假有幾多日?")
    assert is_chinese("refund 要幾耐?")  # English words inside a Chinese question
    assert is_chinese("变换车道")  # simplified counts too


def test_simplified_characters_become_traditional():
    assert to_traditional("变换车道时应该显示方向灯") == "變換車道時應該顯示方向燈"


def test_traditional_cantonese_and_english_text_are_left_alone():
    for text in ["我哋只係問下,佢冇答我", "行咗幾公里", "皇后大道", "Refund within 30 days. [1]", "答案係 14 日 [1]。"]:
        assert to_traditional(text) == text


def test_characters_that_are_right_in_traditional_and_cantonese_text_are_not_damaged():
    # OpenCC alone turns these into 臺灣, 馬裏, 嚇, 曬, 響 and 鬱 (郁 = to move: the meaning changes)
    for text in ["台灣", "蒙哥馬里", "佢吓吓都晒晒聲,隻手响個度郁嚟郁去", "群組", "占領", "布料", "周圍"]:
        assert to_traditional(text) == text


def test_a_simplified_text_is_still_converted_around_the_characters_that_are_kept():
    assert to_traditional("邦联在蒙哥马里建立首都") == "邦聯在蒙哥馬里建立首都"  # 联 and 马 converted, 里 kept
    assert to_traditional("国家学会点样") == "國家學會點樣"
