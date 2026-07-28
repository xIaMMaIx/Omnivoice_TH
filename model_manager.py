# -*- coding: utf-8 -*-
"""
model_manager.py — ระบบจัดการโมเดล OmniVoice-Thai
โหลดโมเดลเบื้องหลัง, สร้างเสียง, ถอดข้อความด้วย Whisper
"""

import os
import time
import threading
import torch
import gradio as gr
import numpy as np
from pythainlp.tokenize import sent_tokenize, word_tokenize
from huggingface_hub import snapshot_download

from config import (
    MODEL_DIR,
    ASR_MODEL_DIR,
    HF_REPO_ID,
    HF_AUDIO_TOK_REPO_ID,
    HF_ASR_REPO_ID,
    REF_DIR,
    MAX_CHUNK_SIZE,
)
from audio_manager import validate_reference_audio
from normalizer import normalize_thai_tts

# ──────────────────────────────────────────────────────────────
# Global state
# ──────────────────────────────────────────────────────────────
model = None
model_loading = False
model_error = None
generation_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────
# Model download & helpers
# ──────────────────────────────────────────────────────────────
def _get_asr_model_path():
    """หาที่เก็บโมเดล Whisper ASR จากโฟลเดอร์ local เท่านั้น"""
    local_path = os.path.abspath(ASR_MODEL_DIR)
    if os.path.isdir(local_path) and os.listdir(local_path):
        return local_path
    return None


def _download_models(force_update=False):
    """ดาวน์โหลดโมเดล OmniVoice, Audio Tokenizer และ Whisper ASR จาก HuggingFace"""
    model_path = os.path.abspath(MODEL_DIR)
    audio_tok_path = os.path.join(model_path, "audio_tokenizer")
    asr_path = os.path.abspath(ASR_MODEL_DIR)

    has_main = os.path.exists(model_path) and os.listdir(model_path)
    has_tok = os.path.isdir(audio_tok_path) and os.listdir(audio_tok_path)
    has_asr = os.path.isdir(asr_path) and os.listdir(asr_path)

    if has_main and has_tok and has_asr and not force_update:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        print(f"📁 พบโมเดลในเครื่อง (Offline Mode): {model_path}")
        return model_path

    os.environ["HF_HUB_OFFLINE"] = "0"
    os.environ["TRANSFORMERS_OFFLINE"] = "0"

    action = "อัปเดต" if force_update else "ดาวน์โหลด"
    print(f"⬇️ กำลัง{action}โมเดลหลัก ({HF_REPO_ID})...")
    snapshot_download(repo_id=HF_REPO_ID, local_dir=model_path)

    print(f"⬇️ กำลัง{action} Audio Tokenizer ({HF_AUDIO_TOK_REPO_ID})...")
    snapshot_download(repo_id=HF_AUDIO_TOK_REPO_ID, local_dir=audio_tok_path)

    print(f"⬇️ กำลัง{action} Whisper ASR ({HF_ASR_REPO_ID})...")
    snapshot_download(repo_id=HF_ASR_REPO_ID, local_dir=asr_path)

    print(f"✅ {action}โมเดลทั้ง 3 ส่วนเรียบร้อย!")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    return model_path


# ──────────────────────────────────────────────────────────────
# Model loading
# ──────────────────────────────────────────────────────────────
def _load_model(force_update=False):
    """โหลดโมเดล OmniVoice-Thai ลง GPU/CPU"""
    global model, model_loading, model_error

    if model_loading:
        return "⏳ ระบบกำลังโหลดโมเดลอยู่ กรุณารอสักครู่..."

    model_loading = True
    model_error = None
    start_time = time.time()

    try:
        from omnivoice import OmniVoice

        print("🎙️ กำลังโหลดโมเดล OmniVoice-Thai...")
        model_path = _download_models(force_update=force_update)
        is_offline = os.environ.get("HF_HUB_OFFLINE") == "1"

        if torch.cuda.is_available():
            loaded = OmniVoice.from_pretrained(
                model_path,
                torch_dtype=torch.float32,
                device_map="cuda:0",
                local_files_only=is_offline,
            )
            device_name = torch.cuda.get_device_name(0)
        else:
            loaded = OmniVoice.from_pretrained(
                model_path, local_files_only=is_offline
            )
            device_name = "CPU"

        if hasattr(loaded, "eval"):
            loaded.eval()
        model = loaded

        elapsed = time.time() - start_time
        msg = f"✅ โหลด OmniVoice สำเร็จ! ({elapsed:.1f}s, {device_name})"
        print(msg)
        return msg

    except Exception as e:
        model_error = str(e)
        print(f"❌ เกิดข้อผิดพลาด: {e}")
        return f"❌ โหลดโมเดลล้มเหลว: {e}"
    finally:
        model_loading = False


def start_background_loading():
    """เริ่มโหลดโมเดลเบื้องหลังเพื่อให้ UI เปิดได้ทันที"""
    threading.Thread(target=_load_model, daemon=True).start()

def get_model_load_status():
    """เช็คสถานะการโหลดโมเดลสำหรับ UI Poll"""
    global model, model_loading, model_error
    if model_error:
        return f"❌ ระบบพบข้อผิดพลาดในการโหลดโมเดล: {model_error}", gr.Timer(active=False)
    if model_loading:
        return "⏳ **สถานะ:** กำลังดาวน์โหลดหรือโหลดโมเดล AI เบื้องหลัง... (อาจใช้เวลา 1-3 นาทีในครั้งแรก)", gr.Timer(active=True)
    if model is not None:
        return "✅ **สถานะ:** โมเดลพร้อมใช้งานแล้ว!", gr.Timer(active=False)
    return "", gr.Timer(active=False)


# ──────────────────────────────────────────────────────────────
# UI callbacks
# ──────────────────────────────────────────────────────────────
def update_model_ui(progress=gr.Progress()):
    """อัปเดตโมเดลจาก HuggingFace ผ่านปุ่มในหน้า UI"""
    progress(0.1, desc="กำลังดาวน์โหลดโมเดลเวอร์ชันล่าสุด...")
    res = _load_model(force_update=True)
    progress(1.0, desc="เสร็จสิ้น")
    return res


def split_text_for_tts(text, max_chunk_size=300):
    """
    หั่นข้อความยาวๆ อย่างชาญฉลาดโดยใช้ PyThaiNLP:
    1. แยกตามการขึ้นบรรทัดใหม่
    2. ใช้ sent_tokenize หาระยะประโยค
    3. หากประโยคยาวเกิน max_chunk_size จะใช้ word_tokenize หั่นและสะสมคำ
    """
    paragraphs = text.split('\n')
    chunks = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        if len(para) <= max_chunk_size:
            chunks.append(para)
            continue
            
        sentences = sent_tokenize(para)
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
                
            if len(sent) <= max_chunk_size:
                chunks.append(sent)
            else:
                words = word_tokenize(sent)
                current_chunk = ""
                for word in words:
                    if len(current_chunk) + len(word) <= max_chunk_size:
                        current_chunk += word
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        
                        if len(word) > max_chunk_size:
                            # หั่นด้วยตัวอักษรกรณีที่คำๆ เดียวมันยาวเกินจริงๆ
                            for i in range(0, len(word), max_chunk_size):
                                chunks.append(word[i:i+max_chunk_size])
                            current_chunk = ""
                        else:
                            current_chunk = word
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                    
    return chunks

# ──────────────────────────────────────────────────────────────
# Voice cloning (core generation)
# ──────────────────────────────────────────────────────────────
def clone_voice(
    text,
    ref_filename,
    ref_text_input,
    speed,
    num_step,
    guidance_scale,
    class_temperature,
    max_text_length,
    silence_duration,
    progress=gr.Progress(),
):
    """ฟังก์ชันหลักสำหรับโคลนเสียงด้วย OmniVoice"""
    global model, model_loading, model_error

    # ── Guard clauses ──
    if model_loading:
        return None, "⏳ โมเดลกำลังโหลดอยู่ กรุณารอสักครู่แล้วลองใหม่..."
    if model is None:
        err = f"\n({model_error})" if model_error else ""
        return None, f"❌ โมเดลยังไม่ถูกโหลด{err}"
    if not text or not text.strip():
        return None, "⚠️ กรุณาใส่ข้อความที่ต้องการให้พูด"
    
    # ดึงค่า max_text_length ออกมาใช้งาน (กรณีที่อาจจะยังไม่โหลด)
    limit = int(max_text_length) if max_text_length else 10000
    if len(text) > limit:
        return None, f"⚠️ ข้อความยาวเกินไป ({len(text)}/{limit} ตัวอักษร)"
        
    if not ref_filename:
        return None, "⚠️ กรุณาเลือกเสียงต้นฉบับจากคลัง"

    ref_path = os.path.join(REF_DIR, ref_filename)
    if not os.path.exists(ref_path):
        return None, "❌ ไม่พบไฟล์เสียงต้นฉบับในคลัง กรุณาเลือกใหม่"

    ref_text = (ref_text_input or "").strip()
    duration, validation_error = validate_reference_audio(ref_path, ref_text)
    if validation_error:
        return None, f"⚠️ {validation_error}"

    gen_start = time.time()

    try:
        from omnivoice import OmniVoiceGenerationConfig

        # ── Normalize ──
        progress(0.1, desc="กำลัง normalize ข้อความและหั่นประโยค...")
        spoken_text = normalize_thai_tts(text)
        chunks = split_text_for_tts(spoken_text, max_chunk_size=MAX_CHUNK_SIZE)

        # ── Ref text: ว่าง → ให้ OmniVoice ใช้ Whisper ภายในตัว ──
        effective_ref_text = ref_text if ref_text else None

        # Pre-load Whisper ของ OmniVoice จาก local ถ้ายังไม่ได้โหลด
        if effective_ref_text is None and model._asr_pipe is None:
            asr_path = _get_asr_model_path()
            if asr_path is None:
                raise RuntimeError(
                    "ไม่พบโมเดล Whisper ในเครื่อง — กรุณาใส่ Ref Text หรือรันดาวน์โหลดโมเดลก่อน"
                )
            progress(0.2, desc="กำลังโหลดโมเดล Whisper...")
            model.load_asr_model(model_name=asr_path)

        # ── Generate ──
        gen_config = OmniVoiceGenerationConfig(
            num_step=int(num_step),
            guidance_scale=float(guidance_scale),
            class_temperature=float(class_temperature),
        )
        
        all_audio = []
        sample_rate = 24000
        silence_dur = float(silence_duration) if silence_duration is not None else 0.3
        silence_samples = int(silence_dur * sample_rate)
        silence_array = np.zeros(silence_samples, dtype=np.float32)

        for i, chunk in enumerate(chunks):
            progress((i + 1) / max(len(chunks), 1), desc=f"กำลังสร้างเสียงส่วนที่ {i+1}/{len(chunks)}...")
            
            generate_kwargs = dict(
                text=chunk,
                ref_audio=ref_path,
                ref_text=effective_ref_text,
                language="Thai",
                generation_config=gen_config,
            )
            if speed and float(speed) != 1.0:
                generate_kwargs["speed"] = float(speed)

            with generation_lock, torch.inference_mode():
                audio_out = model.generate(**generate_kwargs)
                
            chunk_audio = audio_out[0]
            if isinstance(chunk_audio, torch.Tensor):
                chunk_audio = chunk_audio.cpu().numpy()
                
            all_audio.append(chunk_audio)
            
            # เติมช่องว่าง (silence) ระหว่างประโยค ยกเว้น chunk สุดท้าย
            if i < len(chunks) - 1 and silence_dur > 0:
                all_audio.append(silence_array)

        if len(all_audio) == 0:
            return None, "⚠️ ไม่มีข้อความให้สร้างเสียง"

        concatenated_audio = np.concatenate(all_audio, axis=0)
        final_audio = (sample_rate, concatenated_audio)

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        elapsed = time.time() - gen_start

        # ── สรุปสถานะ ──
        settings_parts = []
        if speed and float(speed) != 1.0:
            settings_parts.append(f"ความเร็ว {float(speed):.1f}x")
        if int(num_step) != 32:
            settings_parts.append(f"Steps {int(num_step)}")
        if float(guidance_scale) != 2.0:
            settings_parts.append(f"Guidance {float(guidance_scale):.1f}")
        settings_str = f" | ⚙️ {', '.join(settings_parts)}" if settings_parts else ""

        progress(1.0, desc="เสร็จแล้ว!")
        status = f"✅ สร้างเสียงเรียบร้อย ({elapsed:.1f}s){settings_str}"
        if spoken_text != text.strip():
            status += f"\n📖 อ่านว่า: {spoken_text}"
        return final_audio, status

    except Exception as e:
        return None, f"❌ เกิดข้อผิดพลาด: {str(e)}"


# ──────────────────────────────────────────────────────────────
# Whisper ASR transcription (for audio management tab)
# ──────────────────────────────────────────────────────────────
def transcribe_audio_file(audio_path):
    """ถอดข้อความเสียงด้วยโมเดล Whisper"""
    global model, model_loading

    if model_loading:
        return "⏳ โมเดลกำลังโหลดอยู่ กรุณารอสักครู่แล้วกดถอดเสียงใหม่..."
    if not audio_path or not os.path.exists(audio_path):
        return "⚠️ กรุณาเลือกหรืออัปโหลดไฟล์เสียงที่ต้องการถอดข้อความก่อน"

    _, validation_error = validate_reference_audio(
        audio_path, ref_text=None, require_ref_text=False
    )
    if validation_error:
        return f"⚠️ {validation_error}"

    try:
        # ใช้ OmniVoice Internal ASR ถ้าโมเดลโหลดแล้ว
        if model is not None:
            asr_path = _get_asr_model_path()
            if asr_path and model._asr_pipe is None:
                model.load_asr_model(model_name=asr_path)
            if model._asr_pipe is not None:
                return model.transcribe(audio_path).strip()

        # Fallback: standalone Whisper pipeline
        from transformers import pipeline as hf_pipeline

        asr_path = _get_asr_model_path()
        if asr_path is None:
            return "⚠️ ไม่พบโมเดล Whisper ในเครื่อง — กรุณาดาวน์โหลดโมเดลก่อน"
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        asr_pipe = hf_pipeline(
            "automatic-speech-recognition",
            model=asr_path,
            device=device,
            chunk_length_s=30,
        )
        result = asr_pipe(audio_path, generate_kwargs={"language": "thai"})
        return result["text"].strip()
    except Exception as e:
        return f"❌ ไม่สามารถถอดข้อความได้: {e}"
