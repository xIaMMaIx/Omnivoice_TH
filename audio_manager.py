# -*- coding: utf-8 -*-
"""
audio_manager.py — ระบบจัดการคลังเสียงอ้างอิง (Reference Audios) + จับคู่ข้อความ Ref Text (.txt)
"""

import os
import shutil
import tempfile
import uuid
import soundfile as sf
import gradio as gr
from config import REF_DIR

ALLOWED_AUDIO_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg")


def is_safe_filename(filename):
    """Ensure a user-supplied filename cannot escape the reference directory."""
    return bool(
        filename
        and os.path.basename(filename) == filename
        and not filename.startswith(".")
        and os.path.splitext(filename)[1].lower() in ALLOWED_AUDIO_EXTENSIONS
    )


_duration_cache = {}


def get_audio_duration(audio_path):
    """Return audio duration in seconds with mtime caching for instant lookups."""
    if not audio_path or not os.path.exists(audio_path):
        raise RuntimeError("ไม่พบไฟล์เสียง")

    try:
        mtime = os.path.getmtime(audio_path)
        cache_key = (os.path.abspath(audio_path), mtime)
        if cache_key in _duration_cache:
            return _duration_cache[cache_key]

        info = sf.info(audio_path)
        if info.samplerate <= 0:
            raise RuntimeError("ไม่พบค่า sample rate")
        duration = info.frames / info.samplerate
        _duration_cache[cache_key] = duration
        return duration
    except Exception as e:
        raise RuntimeError(f"ไม่สามารถอ่านระยะเวลาไฟล์เสียงได้: {e}") from e


def validate_reference_audio(audio_path, ref_text, require_ref_text=False):
    """Validate audio file existence and duration without imposing strict length limits."""
    try:
        duration = get_audio_duration(audio_path)
    except RuntimeError as e:
        return None, str(e)

    if duration <= 0:
        return duration, "⚠️ ไฟล์เสียงไม่มีความยาวหรือมีความยาวไม่ถูกต้อง"

    cleaned_ref_text = (ref_text or "").strip()
    if require_ref_text and not cleaned_ref_text:
        return duration, "ไม่พบ Ref Text — กรุณาใส่ข้อความที่พูดในคลิปก่อนสร้างเสียง"

    return duration, None


def get_trim_controls(audio_path):
    """Build slider updates for selecting a reference-audio segment freely."""
    if not audio_path or not os.path.exists(audio_path):
        return gr.update(), gr.update(), "เลือกหรืออัปโหลดไฟล์เสียงก่อนตัด"

    try:
        duration = get_audio_duration(audio_path)
    except RuntimeError as e:
        return gr.update(), gr.update(), f"⚠️ {e}"

    status = f"ความยาวต้นฉบับ {duration:.1f} วินาที — เลือกช่วงที่ต้องการตัดได้ตามอิสระ"
    return (
        gr.update(minimum=0, maximum=duration, value=0, step=0.1),
        gr.update(minimum=0, maximum=duration, value=duration, step=0.1),
        status,
    )


def get_trim_controls_for_saved_audio(filename):
    """Build trim controls for the currently selected library audio."""
    if not is_safe_filename(filename):
        return gr.update(), gr.update(), "เลือกไฟล์ในคลังก่อนตัด"
    return get_trim_controls(os.path.join(REF_DIR, filename))


def trim_audio_file(audio_path, start_seconds, end_seconds):
    """Export the selected segment as a temporary WAV ready to save as a reference."""
    if not audio_path or not os.path.exists(audio_path):
        return None, "⚠️ เลือกหรืออัปโหลดไฟล์เสียงก่อนตัด"

    try:
        duration = get_audio_duration(audio_path)
        start = max(0.0, float(start_seconds or 0))
        end = min(duration, float(end_seconds or 0))
    except (RuntimeError, TypeError, ValueError) as e:
        return None, f"⚠️ ไม่สามารถเตรียมช่วงตัดเสียงได้: {e}"

    segment_duration = end - start
    if segment_duration <= 0:
        return None, "⚠️ ช่วงที่เลือกไม่มีเสียง หรือจุดเริ่มต้นเกินกว่าจุดสิ้นสุด"

    try:
        samples, sample_rate = sf.read(audio_path, always_2d=True)
        start_frame = int(start * sample_rate)
        end_frame = int(end * sample_rate)
        segment = samples[start_frame:end_frame]
        if len(segment) == 0:
            return None, "⚠️ ช่วงที่เลือกไม่มีเสียง"

        output_path = os.path.join(
            tempfile.gettempdir(), f"omnivoice_trim_{uuid.uuid4().hex}.wav"
        )
        sf.write(output_path, segment, sample_rate, subtype="PCM_16")
        return output_path, f"✅ ตัดคลิปแล้ว: {start:.1f}–{end:.1f} วินาที ({segment_duration:.1f} วินาที)"
    except Exception as e:
        return None, f"❌ ตัดเสียงไม่สำเร็จ: {e}"


def trim_saved_audio(filename, start_seconds, end_seconds):
    """Trim an audio already stored in the reference library."""
    if not is_safe_filename(filename):
        return None, "⚠️ เลือกไฟล์ในคลังก่อนตัด"
    return trim_audio_file(
        os.path.join(REF_DIR, filename), start_seconds, end_seconds
    )


def get_audio_list():
    """ดึงรายชื่อไฟล์เสียงทั้งหมดจากคลัง"""
    if not os.path.exists(REF_DIR):
        os.makedirs(REF_DIR, exist_ok=True)
    files = [
        f
        for f in os.listdir(REF_DIR)
        if f.lower().endswith(ALLOWED_AUDIO_EXTENSIONS)
    ]
    files.sort()
    return files


def get_txt_path(filename):
    """หาชื่อไฟล์ .txt คู่กันของไฟล์เสียงนั้น"""
    if not is_safe_filename(filename):
        return None
    base, _ = os.path.splitext(filename)
    return os.path.join(REF_DIR, base + ".txt")


def get_audio_ref_text(filename):
    """ดึงข้อความ Ref Text (.txt) ที่คู่กันกับไฟล์เสียงที่เลือก"""
    txt_path = get_txt_path(filename)
    if txt_path and os.path.exists(txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            print(f"⚠️ อ่านไฟล์ {txt_path} ไม่สำเร็จ: {e}")
    return ""


def save_audio(temp_path, custom_name, ref_text=""):
    """บันทึกไฟล์เสียงลงคลัง พร้อมไฟล์ข้อความคู่กัน (.txt)"""
    if not temp_path:
        return gr.update(), "⚠️ กรุณาอัปโหลดหรืออัดเสียงก่อน"

    if not custom_name or not custom_name.strip():
        custom_name = "voice_" + os.path.basename(temp_path)

    custom_name = custom_name.strip()
    if not custom_name.lower().endswith(ALLOWED_AUDIO_EXTENSIONS):
        custom_name += ".wav"
    if not is_safe_filename(custom_name):
        return gr.update(), "⚠️ ชื่อไฟล์ไม่ถูกต้อง กรุณาใช้ชื่อไฟล์ธรรมดาโดยไม่มี path"

    _, validation_error = validate_reference_audio(temp_path, ref_text)
    if validation_error:
        return gr.update(), f"⚠️ {validation_error}"

    dest = os.path.join(REF_DIR, custom_name)
    shutil.copy(temp_path, dest)

    # บันทึก Ref Text คู่กัน (.txt)
    txt_path = get_txt_path(custom_name)
    if ref_text and ref_text.strip():
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(ref_text.strip())
    elif os.path.exists(txt_path):
        # ถ้าข้อความว่างเปล่า ให้ลบไฟล์ .txt เดิมออก
        os.remove(txt_path)

    audios = get_audio_list()
    msg = f"✅ บันทึก '{custom_name}' ลงคลังเรียบร้อย!"
    if ref_text and ref_text.strip():
        msg += " (พร้อมจับคู่ Ref Text)"
    return (
        gr.update(choices=audios, value=custom_name),
        msg,
    )


def save_ref_text_only(filename, ref_text):
    """อัปเดตหรือบันทึก Ref Text (.txt) สำหรับไฟล์เสียงที่มีอยู่แล้วในคลัง"""
    if not filename:
        return "⚠️ กรุณาเลือกไฟล์เสียงที่ต้องการบันทึกข้อความก่อน"
    if not is_safe_filename(filename):
        return "⚠️ ชื่อไฟล์ไม่ถูกต้อง"
    txt_path = get_txt_path(filename)
    if not txt_path:
        return "⚠️ ไม่พบชื่อไฟล์"

    audio_path = os.path.join(REF_DIR, filename)
    _, validation_error = validate_reference_audio(audio_path, ref_text)
    if validation_error:
        return f"⚠️ {validation_error}"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(ref_text.strip())
    return f"💾 บันทึกข้อความคู่กับ '{filename}' เรียบร้อยแล้ว!"


def delete_audio(filename):
    """ลบไฟล์เสียงและไฟล์ข้อความคู่กันออกจากคลัง"""
    if not filename:
        return gr.update(), None, "", "⚠️ กรุณาเลือกไฟล์จาก Dropdown ก่อนกดลบ"
    if not is_safe_filename(filename):
        return gr.update(), None, "", "⚠️ ชื่อไฟล์ไม่ถูกต้อง"

    path = os.path.join(REF_DIR, filename)
    txt_path = get_txt_path(filename)

    if os.path.exists(path):
        os.remove(path)
    if txt_path and os.path.exists(txt_path):
        os.remove(txt_path)

    audios = get_audio_list()
    return (
        gr.update(choices=audios, value=None),
        None,
        "",
        f"🗑️ ลบไฟล์ '{filename}' และข้อความคู่กันเรียบร้อยแล้ว",
    )


def update_preview(filename):
    """อัปเดตตัวอย่างเสียงและดึงข้อความ Ref Text คู่กันเมื่อเลือกจาก Dropdown"""
    if not filename:
        return None, ""
    if not is_safe_filename(filename):
        return None, ""
    path = os.path.join(REF_DIR, filename)
    ref_text = get_audio_ref_text(filename)
    if os.path.exists(path):
        return path, ref_text
    return None, ""


def refresh_audio_list():
    """รีเฟรชรายการไฟล์เสียง"""
    audios = get_audio_list()
    count = len(audios)
    return gr.update(choices=audios), f"🔄 รีเฟรชเรียบร้อย — พบเสียงในคลัง {count} ไฟล์"
