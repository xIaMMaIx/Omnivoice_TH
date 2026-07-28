# -*- coding: utf-8 -*-
"""
normalizer.py — ระบบเตรียมและทำความสะอาดข้อความภาษาไทยก่อนส่งให้โมเดล TTS
"""

import re
from pythainlp.tokenize import word_tokenize
from pythainlp.util import normalize as thai_normalize
from pythainlp.util import num_to_thaiword, bahttext
from config import load_settings
from english_reader import normalize_english_text

THAI_MONTHS = [
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]

# แผนที่เครื่องหมาย → คำอ่านภาษาไทย
SYMBOL_MAP = {
    "%": "เปอร์เซ็นต์",
    "+": "บวก",
    "=": "เท่ากับ",
    "&": "แอนด์",
    "#": "ชาร์ป",
    "@": "แอท",
    "°": "องศา",
    "°C": "องศาเซลเซียส",
    "°F": "องศาฟาเรนไฮต์",
    "㎡": "ตารางเมตร",
    "㎞": "กิโลเมตร",
}

# Compile once because these expressions run for both the live preview and
# the final generation request.
PHONE_PATTERN = re.compile(r"0\d{1,2}[-.]?\d{3,4}[-.]?\d{3,4}")
CURRENCY_PATTERN = re.compile(r"([\d,]+\.?\d*)\s*บาท")
BAHT_SYMBOL_PATTERN = re.compile(r"฿\s*([\d,]+\.?\d*)")
DATE_PATTERN = re.compile(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})")
EMAIL_PATTERN = re.compile(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
PERCENT_PATTERN = re.compile(r"(\d)\s*%")
ORDINAL_PATTERN = re.compile(r"ที่\s*(\d+)")

# ตัวอย่างข้อความสำหรับทดลองใช้
EXAMPLE_TEXTS = [
    "สวัสดีครับ วันนี้อากาศดีมากเลย",
    "ราคาสินค้าชิ้นนี้ 1,500 บาท ลดเหลือ 999 บาท",
    "โทรหาผมได้ที่เบอร์ 081-234-5678 นะครับ",
    "วันที่ 25/12/2568 เป็นวันคริสต์มาส",
    "ยอดขายเพิ่มขึ้น 15% เมื่อเทียบกับปีที่แล้ว",
    "ส่งอีเมลมาที่ info@example.com ได้เลยครับ",
    "เด็กๆ ชอบกินขนมหวานๆ มากๆ",
    "[laughter] ตลกมากเลย ขำจนท้องแข็ง",
]

# Non-Verbal Tags ที่รองรับ
NON_VERBAL_TAGS = [
    ("😂 หัวเราะ", "[laughter]"),
    ("😮‍💨 ถอนหายใจ", "[sigh]"),
    ("😲 ตกใจ อ้า!", "[surprise-ah]"),
    ("😯 ตกใจ โอ้!", "[surprise-oh]"),
    ("🤩 ว้าว!", "[surprise-wa]"),
    ("🤔 ถาม เอ๊?", "[question-ei]"),
    ("👍 อืม (รับ)", "[confirmation-en]"),
    ("😤 หึ่ม", "[dissatisfaction-hnn]"),
]


def is_number(s):
    """ตรวจสอบว่าเป็นตัวเลขหรือไม่"""
    try:
        float(s.replace(",", ""))
        return True
    except ValueError:
        return False


def normalize_yamok(tokens):
    """แปลงไม้ยมก (ๆ) เป็นคำซ้ำ"""
    result = []
    for token in tokens:
        if "ๆ" in token:
            word_to_repeat = ""
            temp = list(result)
            while temp and not temp[-1].strip():
                temp.pop()
            if temp:
                word_to_repeat = temp[-1]

            if token.strip() == "ๆ":
                result.append(word_to_repeat)
            else:
                clean_word = token.replace("ๆ", "")
                result.append(clean_word)
                result.append(clean_word)
        else:
            result.append(token)
    return result


def normalize_numbers(token):
    """แปลงตัวเลขเป็นคำอ่านภาษาไทย"""
    if not is_number(token):
        return token

    num_str = token.replace(",", "")

    # เบอร์โทร (ขึ้นต้นด้วย 0 และยาว 9-10 หลัก)
    if num_str.startswith("0") and len(num_str) >= 9 and "." not in num_str:
        thai_digits = [num_to_thaiword(int(d)) for d in num_str]
        return "".join(thai_digits)

    # ทศนิยม
    if "." in num_str:
        return num_to_thaiword(float(num_str))

    # จำนวนเต็ม
    return num_to_thaiword(int(num_str))


def normalize_phone_numbers(text):
    """แปลงเบอร์โทรศัพท์เป็นคำอ่านทีละตัว เช่น 081-234-5678"""

    def phone_to_thai(match):
        digits = re.sub(r"[^0-9]", "", match.group(0))
        thai_digits = [num_to_thaiword(int(d)) for d in digits]
        return "".join(thai_digits)

    return PHONE_PATTERN.sub(phone_to_thai, text)


def normalize_currency(text):
    """แปลงจำนวนเงินบาทเป็นคำอ่าน เช่น 500 บาท → ห้าร้อยบาท"""

    def baht_to_spoken(amount):
        result = bahttext(amount)
        result = result.replace("ถ้วน", "").strip()
        return result

    def baht_to_thai(match):
        amount_str = match.group(1).replace(",", "")
        try:
            return baht_to_spoken(float(amount_str))
        except ValueError:
            return match.group(0)

    text = CURRENCY_PATTERN.sub(baht_to_thai, text)

    def baht_symbol_to_thai(match):
        amount_str = match.group(1).replace(",", "")
        try:
            return baht_to_spoken(float(amount_str))
        except ValueError:
            return match.group(0)

    return BAHT_SYMBOL_PATTERN.sub(baht_symbol_to_thai, text)


def normalize_dates(text):
    """แปลงวันที่เป็นคำอ่านภาษาไทย เช่น 25/12/2568 → วันที่ยี่สิบห้า เดือนธันวาคม พ.ศ.สองพันห้าร้อยหกสิบแปด"""

    def date_to_thai(match):
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3))

        if month < 1 or month > 12:
            return match.group(0)

        day_text = num_to_thaiword(day)
        month_text = THAI_MONTHS[month]

        if year < 2400:
            year += 543

        year_text = num_to_thaiword(year)
        return f"วันที่{day_text} เดือน{month_text} พุทธศักราช{year_text}"

    return DATE_PATTERN.sub(date_to_thai, text)


def normalize_email(text):
    """แปลงอีเมลเป็นคำอ่าน เช่น user@mail.com → ยูสเซอร์ แอท เมล ดอท คอม"""

    def email_to_thai(match):
        local = match.group(1)
        domain = match.group(2)
        domain_parts = domain.split(".")
        domain_read = " ดอท ".join(domain_parts)
        return f"{local} แอท {domain_read}"

    return EMAIL_PATTERN.sub(email_to_thai, text)


def normalize_symbols(text):
    """แปลงเครื่องหมายพิเศษเป็นคำอ่านภาษาไทย"""
    text = PERCENT_PATTERN.sub(lambda m: m.group(1) + "เปอร์เซ็นต์", text)
    text = text.replace("°C", "องศาเซลเซียส")
    text = text.replace("°F", "องศาฟาเรนไฮต์")

    for symbol, word in SYMBOL_MAP.items():
        if symbol in ("%", "°C", "°F"):
            continue
        text = text.replace(symbol, word)

    return text


def normalize_ordinals(text):
    """แปลงตัวเลขลำดับ เช่น ที่ 1 → ที่หนึ่ง"""

    def ordinal_to_thai(match):
        num = int(match.group(1))
        return f"ที่{num_to_thaiword(num)}"

    return ORDINAL_PATTERN.sub(ordinal_to_thai, text)


def normalize_thai_tts(text):
    """
    ฟังก์ชันหลัก: แปลงข้อความภาษาไทยให้พร้อมสำหรับ TTS
    """
    if not text:
        return ""

    text = thai_normalize(text)
    text = normalize_dates(text)
    text = normalize_currency(text)
    text = normalize_phone_numbers(text)
    text = normalize_email(text)
    text = normalize_symbols(text)
    text = normalize_ordinals(text)
    text = normalize_english_text(text)

    tokens = word_tokenize(text, engine="newmm")
    tokens = normalize_yamok(tokens)

    result = []
    for token in tokens:
        if is_number(token):
            result.append(normalize_numbers(token))
        else:
            result.append(token)

    return "".join(result)


def count_characters(text):
    """นับจำนวนตัวอักษรและแสดงสถานะ"""
    if not text:
        return "0 ตัวอักษร"
    count = len(text)
    limit = load_settings().get("max_text_length", 10000)
    if count > limit:
        return f"⚠️ {count}/{limit} ตัวอักษร (เกินขีดจำกัด!)"
    return f"📝 {count}/{limit} ตัวอักษร"


def preview_normalized(text):
    """แสดงตัวอย่างข้อความหลังจาก normalize"""
    if not text or not text.strip():
        return ""
    try:
        normalized = normalize_thai_tts(text)
        return normalized
    except Exception as e:
        return f"(ไม่สามารถแสดงตัวอย่างได้: {e})"


def update_text_metadata(text):
    """Update the counter and normalized preview in one UI callback."""
    return count_characters(text), preview_normalized(text)


def insert_tag(current_text, tag):
    """แทรก Non-Verbal Tag ลงในข้อความ"""
    if not current_text:
        return tag
    if current_text.endswith(" "):
        return current_text + tag
    return current_text + " " + tag
