# -*- coding: utf-8 -*-
"""
config.py — เก็บค่าคงที่ และฟังก์ชันโหลด/บันทึกการตั้งค่าของโปรแกรม
"""

import os
import json

# ──────────────────────────────────────────────────────────────
# Path constants
# ──────────────────────────────────────────────────────────────
REF_DIR = "reference_audios"
os.makedirs(REF_DIR, exist_ok=True)

MAX_CHUNK_SIZE = 300  # ขีดจำกัดตัวอักษรต่อ 1 chunk ก่อนส่งให้โมเดล
SETTINGS_FILE = "settings.json"  # ไฟล์บันทึกการตั้งค่า
MODEL_DIR = "models/omnivoice-thai"  # โฟลเดอร์เก็บโมเดล local
ASR_MODEL_DIR = "models/whisper-large-v3-turbo"  # โฟลเดอร์เก็บโมเดล Whisper ASR local
HF_REPO_ID = "hotdogs/omnivoice-thai"  # HuggingFace repo หลัก
HF_AUDIO_TOK_REPO_ID = "eustlb/higgs-audio-v2-tokenizer"  # Audio Tokenizer repo
HF_ASR_REPO_ID = "openai/whisper-large-v3-turbo"  # Whisper ASR repo

# ──────────────────────────────────────────────────────────────
# Default settings
# ──────────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "speed": 1.0,
    "num_step": 32,
    "guidance_scale": 2.0,
    "class_temperature": 0.0,
    "last_ref_audio": None,
    "max_text_length": 10000,
    "silence_duration": 0.3,
}


def load_settings():
    """โหลดการตั้งค่าจากไฟล์ JSON — merge กับ DEFAULT เพื่อรองรับคีย์ใหม่"""
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings = {**DEFAULT_SETTINGS, **saved}
            # ลบคีย์เก่าที่ไม่ใช้แล้ว (เช่น engine จากเวอร์ชันก่อน)
            for key in list(settings):
                if key not in DEFAULT_SETTINGS:
                    del settings[key]
            return settings
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()


def save_settings(speed, num_step, guidance_scale, class_temperature, max_text_length, silence_duration):
    """บันทึกการตั้งค่าลงไฟล์ JSON"""
    settings = {
        "speed": round(float(speed), 2),
        "num_step": int(num_step),
        "guidance_scale": round(float(guidance_scale), 2),
        "class_temperature": round(float(class_temperature), 2),
        "last_ref_audio": load_settings().get("last_ref_audio"),
        "max_text_length": int(max_text_length),
        "silence_duration": round(float(silence_duration), 2),
    }
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return "✅ บันทึกการตั้งค่าเรียบร้อย!"
    except Exception as e:
        return f"❌ บันทึกไม่สำเร็จ: {e}"


def save_last_ref_audio(filename):
    """บันทึกเฉพาะชื่อไฟล์เสียงต้นฉบับล่าสุด (แยกจากปุ่มบันทึกปกติเพื่อให้บันทึกอัตโนมัติเมื่อเลือก)"""
    if not filename:
        return
    settings = load_settings()
    settings["last_ref_audio"] = filename
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def reset_settings():
    """รีเซ็ตการตั้งค่ากลับเป็นค่าเริ่มต้น"""
    d = DEFAULT_SETTINGS
    save_settings(d["speed"], d["num_step"], d["guidance_scale"], d["class_temperature"], d["max_text_length"], d["silence_duration"])
    return (
        d["speed"],
        d["num_step"],
        d["guidance_scale"],
        d["class_temperature"],
        d["max_text_length"],
        d["silence_duration"],
        "🔄 รีเซ็ตเป็นค่าเริ่มต้นเรียบร้อย!",
    )
