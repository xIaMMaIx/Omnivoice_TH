# -*- coding: utf-8 -*-
"""
english_reader.py — ระบบอ่านคำศัพท์ภาษาอังกฤษเป็นคำอ่านภาษาไทยแบบ 100% Pure Python
ขั้นตอน:
1. Custom Dictionary (custom_dict.json)
2. Pronunciation Cache (en_read_cache.json)
3. Pure Python CMUdict / g2p_en -> Thai Phonetics
4. Letter-by-Letter Fallback
"""

import os
import json
import re
import atexit

CUSTOM_DICT_FILE = "custom_dict.json"
CACHE_FILE = "en_read_cache.json"

# คำศัพท์เริ่มต้นใน Custom Dictionary (คำเฉพาะทางไอที ตัวย่อ แบรนด์)
DEFAULT_CUSTOM_DICT = {
    "AI": "เอไอ",
    "PYTHON": "ไพธอน",
    "APP": "แอป",
    "APPS": "แอป",
    "GRADIO": "เกรดิโอ",
    "GPU": "จีพียู",
    "CPU": "ซีพียู",
    "API": "เอพีไอ",
    "APIS": "เอพีไอ",
    "OK": "โอเค",
    "WEB": "เว็บ",
    "WEBSITE": "เว็บไซต์",
    "ONLINE": "ออนไลน์",
    "OFFLINE": "ออฟไลน์",
    "CHATGPT": "แชตจีพีที",
    "OMNIVOICE": "ออมนิโวซ์",
    "WINDOWS": "วินโดวส์",
    "LINUX": "ลินุกซ์",
    "MAC": "แมค",
    "PC": "พีซี",
    "IT": "ไอที",
    "UI": "ยูไอ",
    "UX": "ยูเอ็กซ์",
    "TTS": "ทีทีเอส",
    "LLM": "แอลแอลเอ็ม",
    "HD": "เอชดี",
    "4K": "สี่เค",
    "3D": "สามดี",
    "THAI": "ไทย",
    "ENGLISH": "อังกฤษ",
    "TEST": "เทสต์",
    "DEMO": "เดโม",
    "HELLO": "เฮลโล",
    "FREE": "ฟรี",
    "MODEL": "โมเดล",
    "VOICE": "โวซ์",
    "AUDIO": "ออดิโอ",
    "LINK": "ลิงก์",
    "CLICK": "คลิก",
    "START": "สตาร์ท",
    "STOP": "สต็อป",
    "RESET": "รีเซ็ต",
    "SAVE": "เซฟ",
    "OPEN": "โอเพ่น",
    "CLOSE": "โคลส",
    "DATA": "ดาต้า",
    "FILE": "ไฟล์",
    "SYSTEM": "ซิสเต็ม",
    "USER": "ยูสเซอร์",
    "ADMIN": "แอดมิน",
    "SERVER": "เซิร์ฟเวอร์",
    "LOCAL": "โลคอล",
    "CODE": "โค้ด",
    "PAGE": "เพจ",
    "LIVE": "ไลฟ์",
    "STREAM": "สตรีม",
    "GAME": "เกม",
    "POST": "โพสต์",
    "LIKE": "ไลก์",
    "SHARE": "แชร์",
    "PROMPT": "พรอมต์",
}

# คำอ่านตัวอักษร A-Z (สำหรับการสะกดทีละตัวถ้าไม่พบคำอ่านอื่น)
LETTER_NAMES = {
    "A": "เอ",
    "B": "บี",
    "C": "ซี",
    "D": "ดี",
    "E": "อี",
    "F": "เอฟ",
    "G": "จี",
    "H": "เอช",
    "I": "ไอ",
    "J": "เจ",
    "K": "เค",
    "L": "แอล",
    "M": "เอ็ม",
    "N": "เอ็น",
    "O": "โอ",
    "P": "พี",
    "Q": "คิว",
    "R": "อาร์",
    "S": "เอส",
    "T": "ที",
    "U": "ยู",
    "V": "วี",
    "W": "ดับเบิลยู",
    "X": "เอ็กซ์",
    "Y": "วาย",
    "Z": "ซี",
}

# แผนที่พยัญชนะต้น ARPABET -> พยัญชนะไทย
ARPABET_CONSONANTS_INIT = {
    "B": "บ",
    "CH": "ช",
    "D": "ด",
    "DH": "ด",
    "F": "ฟ",
    "G": "ก",
    "HH": "ฮ",
    "JH": "จ",
    "K": "ค",
    "L": "ล",
    "M": "ม",
    "N": "น",
    "NG": "ง",
    "P": "พ",
    "R": "ร",
    "S": "ส",
    "SH": "ช",
    "T": "ท",
    "TH": "ท",
    "V": "ว",
    "W": "ว",
    "Y": "ย",
    "Z": "ซ",
    "ZH": "ช",
}

# แผนที่ตัวสะกด ARPABET -> ตัวสะกดไทย
ARPABET_CONSONANTS_FINAL = {
    "B": "บ",
    "D": "ด",
    "F": "ฟ",
    "G": "ก",
    "K": "ค",
    "L": "ล",
    "M": "ม",
    "N": "น",
    "NG": "ง",
    "P": "พ",
    "S": "ส",
    "T": "ท",
    "V": "ฟ",
    "Z": "ส",
}

# แผนที่สระ ARPABET -> รูปแบบเสียงสระไทย
ARPABET_VOWELS = {
    "AA": "อา",
    "AE": "แอะ",
    "AH": "อะ",
    "AO": "ออ",
    "AW": "เอา",
    "AY": "ไอ",
    "EH": "เอะ",
    "ER": "เออ",
    "EY": "เอ",
    "IH": "อิ",
    "IY": "อี",
    "OW": "โอ",
    "OY": "ออย",
    "UH": "อุ",
    "UW": "อู",
}

_g2p_instance = None
_cache_dirty = False
THAI_CHARACTER_PATTERN = re.compile(r"[ก-๙]")
TAG_OR_ENGLISH_PATTERN = re.compile(r"\[[A-Za-z][A-Za-z-]*\]|[a-zA-Z]+")


def get_g2p():
    """โหลดโมเดล g2p_en แบบ Lazy Load (ครั้งแรกครั้งเดียว)"""
    global _g2p_instance
    if _g2p_instance is None:
        try:
            from g2p_en import G2p

            _g2p_instance = G2p()
        except Exception as e:
            # Keep the normalizer usable even when optional G2P resources are
            # missing; the caller will use the letter-by-letter fallback.
            print(f"g2p_en unavailable; using fallback: {e}")
            _g2p_instance = False
    return _g2p_instance


def load_json_file(filepath, default_data):
    """โหลดไฟล์ JSON หากไม่มีให้สร้างใหม่พร้อมค่าเริ่มต้น และรวมค่าใหม่เสมอ"""
    data = default_data.copy()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                saved = json.load(f)
                data.update(saved)
        except Exception:
            pass
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def save_json_file(filepath, data):
    """บันทึกไฟล์ JSON"""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ ไม่สามารถบันทึก {filepath}: {e}")


# โหลด Custom Dict และ Cache ในหน่วยความจำ
_custom_dict = load_json_file(CUSTOM_DICT_FILE, DEFAULT_CUSTOM_DICT)
_pronunciation_cache = load_json_file(CACHE_FILE, {})


def _is_valid_cached_reading(word, reading):
    """Reject old cache entries that merely repeat the original English word."""
    return bool(
        isinstance(reading, str)
        and reading.strip()
        and reading.casefold() != word.casefold()
        and THAI_CHARACTER_PATTERN.search(reading)
    )


def _clean_pronunciation_cache():
    global _cache_dirty
    invalid_words = [
        word
        for word, reading in _pronunciation_cache.items()
        if not _is_valid_cached_reading(word, reading)
    ]
    for word in invalid_words:
        del _pronunciation_cache[word]
    _cache_dirty = bool(invalid_words)


def flush_pronunciation_cache():
    """Persist new successful readings once when the application exits."""
    global _cache_dirty
    if _cache_dirty:
        save_json_file(CACHE_FILE, _pronunciation_cache)
        _cache_dirty = False


_clean_pronunciation_cache()
atexit.register(flush_pronunciation_cache)


DIGIT_PATTERN = re.compile(r"\d+")


def arpabet_to_thai(phonemes):
    """แปลงรายการเสียง ARPABET จาก g2p_en ให้เป็นคำอ่านไทยอย่างง่าย"""
    # ตัวอย่าง phonemes: ['HH', 'AH0', 'L', 'OW1'] หรือ ['P', 'AY1', 'TH', 'AA0', 'N']
    clean_phonemes = [DIGIT_PATTERN.sub("", p) for p in phonemes if p.strip()]
    if not clean_phonemes:
        return ""

    syllables = []
    current_init = ""
    current_vowel = ""

    for i, ph in enumerate(clean_phonemes):
        if ph in ARPABET_VOWELS:
            # เจอสระ
            vowel_sound = ARPABET_VOWELS[ph]
            init_char = ARPABET_CONSONANTS_INIT.get(current_init, "อ")

            # ตรวจสอบตัวสะกดถัดไป (ถ้ามีพยัญชนะถัดไป และไม่ใช่พยัญชนะต้นของสระถัดไป)
            final_char = ""
            if i + 1 < len(clean_phonemes) and clean_phonemes[i + 1] not in ARPABET_VOWELS:
                # ถ้าพยัญชนะถัดไปอยู่ท้ายสุด หรือตัวถัดจากมันเป็นพยัญชนะอีกตัว -> นับเป็นตัวสะกด
                if i + 2 >= len(clean_phonemes) or clean_phonemes[i + 2] not in ARPABET_VOWELS:
                    final_char = ARPABET_CONSONANTS_FINAL.get(clean_phonemes[i + 1], "")

            syl = f"{init_char}{vowel_sound}{final_char}".replace("ออ", "อ")
            syllables.append(syl)
            current_init = ""
        elif ph in ARPABET_CONSONANTS_INIT:
            current_init = ph

    result = "".join(syllables)
    return result if result else None


def read_english_word(word):
    """อ่านคำศัพท์ภาษาอังกฤษ 1 คำ ตาม 4 ลำดับชั้น:
    1. Custom Dict
    2. Cache
    3. CMUdict / g2p_en
    4. Spell letter-by-letter (เฉพาะตัวย่อพิมพ์ใหญ่) หรือคงรูปเดิมสำหรับคำทั่วไป
    """
    clean_word = word.strip()
    if not clean_word:
        return ""

    upper_word = clean_word.upper()

    # Step 1: Custom Dictionary
    if upper_word in _custom_dict:
        return _custom_dict[upper_word]

    # Step 2: Pronunciation Cache
    cached_reading = _pronunciation_cache.get(upper_word)
    if _is_valid_cached_reading(clean_word, cached_reading):
        return cached_reading

    # Step 3: Pure Python CMUdict / g2p_en
    thai_read = None
    g2p = get_g2p()
    if g2p:
        try:
            phonemes = g2p(clean_word)
            # ตัดเครื่องหมายวรรคตอนที่ g2p คืนมา
            phonemes = [p for p in phonemes if p.strip() and p not in (" ", "'", ",")]
            thai_read = arpabet_to_thai(phonemes)
        except Exception:
            thai_read = None

    # Step 4: Fallback — เฉพาะตัวย่อภาษาอังกฤษที่เป็นตัวพิมพ์ใหญ่ทั้งหมด (เช่น AI, CPU, GPU)
    # ให้สะกดทีละตัวอักษร ส่วนคำทั่วไปให้คงรูปเดิมเพื่อให้โมเดล TTS ออกเสียงตามปกติ
    if not thai_read:
        if clean_word.isupper() and len(upper_word) <= 4 and all(c in LETTER_NAMES for c in upper_word):
            thai_read = "".join(LETTER_NAMES.get(c, c) for c in upper_word)
        else:
            thai_read = clean_word

    # Cache only useful Thai readings. Do not permanently cache a failed
    # conversion, so a later dictionary update or repaired G2P can retry it.
    if _is_valid_cached_reading(clean_word, thai_read):
        global _cache_dirty
        _pronunciation_cache[upper_word] = thai_read
        _cache_dirty = True

    return thai_read


def normalize_english_text(text):
    """ค้นหาและแปลงคำศัพท์ภาษาอังกฤษในข้อความไทยให้เป็นคำอ่านภาษาไทย"""
    if not text:
        return ""

    def replace_word(match):
        token = match.group(0)
        # OmniVoice non-verbal tags are syntax, not English words. Preserve
        # them exactly so [laughter] and similar tags remain functional.
        if token.startswith("["):
            return token
        return read_english_word(token)

    return TAG_OR_ENGLISH_PATTERN.sub(replace_word, text)
