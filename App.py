# -*- coding: utf-8 -*-
"""
App.py — ไฟล์หลักสำหรับเปิดใช้งานแอปพลิเคชัน OmniVoice Thai (Modular UI & Launch)
"""

import os
import socket
import gradio as gr

# ปิด Analytics และการเชื่อมต่อออนไลน์ที่ไม่จำเป็นของ Gradio
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

# นำเข้าฟังก์ชันและค่าจากไฟล์โมดูลย่อย
from config import load_settings, save_settings, reset_settings, save_last_ref_audio, MAX_TEXT_LENGTH
from normalizer import (
    NON_VERBAL_TAGS,
    EXAMPLE_TEXTS,
    update_text_metadata,
    insert_tag,
)
from audio_manager import (
    get_audio_list,
    save_audio,
    save_ref_text_only,
    delete_audio,
    update_preview,
    refresh_audio_list,
    get_trim_controls,
    get_trim_controls_for_saved_audio,
    trim_audio_file,
    trim_saved_audio,
)
from model_manager import (
    start_background_loading,
    clone_voice,
    update_model_ui,
    transcribe_audio_file,
    get_model_load_status,
)
from ui_theme import custom_theme, custom_css, dark_mode_js

# โหลดการตั้งค่าปัจจุบัน
current_settings = load_settings()

# เริ่มโหลดโมเดลเบื้องหลังทันที
start_background_loading()


# ╔══════════════════════════════════════════════════════════════╗
# ║  Gradio UI — หน้าเว็บแอป                                     ║
# ╚══════════════════════════════════════════════════════════════╝

with gr.Blocks(title="OmniVoice Thai — เครื่องมือโคลนเสียงภาษาไทย") as demo:
    # ===== Header =====
    gr.Markdown(
        "# 🎙️ OmniVoice Thai\n"
        "เครื่องมือโคลนเสียงภาษาไทย — ใส่ข้อความ เลือกเสียงต้นฉบับ แล้วสร้างเสียงพูดได้ทันที",
        elem_id="app-header",
    )

    global_status = gr.Markdown("⏳ **สถานะ:** กำลังเตรียมความพร้อมระบบ...", elem_id="global-status")
    model_timer = gr.Timer(value=2, active=True)

    # ===== Tabs =====
    with gr.Tabs():
        # ──────────────────────────────────────────────────────
        # Tab 1: โคลนเสียง (3 คอลัมน์บน desktop และตัดเป็น 2/1 ตามพื้นที่)
        # ──────────────────────────────────────────────────────
        with gr.Tab("🎤 โคลนเสียง"):
            with gr.Row(equal_height=False, elem_id="clone-workspace"):
                # คอลัมน์ 1: ข้อความ
                with gr.Column(scale=1, min_width=320):
                    gr.Markdown("### 📝 ข้อความ")

                    input_text = gr.Textbox(
                        label="ข้อความที่ต้องการให้พูด",
                        lines=4,
                        max_lines=10,
                        max_length=MAX_TEXT_LENGTH,
                        placeholder="พิมพ์ข้อความภาษาไทยที่นี่...\nเช่น สวัสดีครับ วันนี้อากาศดีมาก",
                        elem_classes="panel-card",
                    )

                    with gr.Row():
                        char_count = gr.Textbox(
                            label="",
                            value="0 ตัวอักษร",
                            interactive=False,
                            elem_id="char-count",
                            show_label=False,
                        )

                    norm_preview = gr.Textbox(
                        label="🔄 ตัวอย่างคำอ่านหลัง Normalize",
                        interactive=False,
                        lines=2,
                        elem_id="norm-preview",
                        placeholder="ข้อความจะถูกแปลงอัตโนมัติเมื่อพิมพ์...",
                    )

                    # --- Non-Verbal Tags (กดเร็ว) ---
                    with gr.Accordion(
                        "🎭 แทรกเสียงเอฟเฟกต์",
                        open=False,
                        elem_classes="settings-accordion",
                    ):
                        with gr.Row():
                            tag_buttons = []
                            for label, tag in NON_VERBAL_TAGS[:4]:
                                btn = gr.Button(
                                    label, size="sm", elem_classes="tag-btn"
                                )
                                tag_buttons.append((btn, tag))
                        with gr.Row():
                            for label, tag in NON_VERBAL_TAGS[4:]:
                                btn = gr.Button(
                                    label, size="sm", elem_classes="tag-btn"
                                )
                                tag_buttons.append((btn, tag))

                    with gr.Accordion(
                        "💡 ลองข้อความตัวอย่าง",
                        open=False,
                        elem_classes="examples-accordion",
                    ):
                        gr.Examples(
                            examples=[[ex] for ex in EXAMPLE_TEXTS],
                            inputs=[input_text],
                            label="",
                            examples_per_page=8,
                            elem_id="examples-table",
                        )

                # คอลัมน์ 2: เสียงต้นฉบับ
                with gr.Column(scale=1, min_width=320):
                    gr.Markdown("### 🎧 เสียงต้นฉบับ")

                    audio_choices = get_audio_list()
                    last_ref = current_settings.get("last_ref_audio")
                    if last_ref not in audio_choices:
                        last_ref = None

                    ref_dropdown = gr.Dropdown(
                        label="เลือกเสียงจากคลัง",
                        choices=audio_choices,
                        value=last_ref,
                        interactive=True,
                        elem_classes="panel-card",
                    )

                    ref_preview = gr.Audio(
                        label="ฟังตัวอย่างเสียงต้นฉบับ",
                        interactive=False,
                        elem_classes="audio-panel",
                    )

                    ref_text_input = gr.Textbox(
                        label="📜 Ref Text ของคลิปนี้ (ไม่บังคับ)",
                        placeholder="ข้อความที่พูดในคลิปเสียงต้นฉบับ (ใส่หรือไม่ใส่ก็ได้)",
                        lines=3,
                        max_lines=6,
                        info="ใส่หรือไม่ใส่ก็ได้ (หากไม่ใส่ระบบจะใช้ Whisper ถอดเสียงอัตโนมัติ) ไม่จำกัดความยาวคลิปเสียง",
                    )

                # คอลัมน์ 3: สร้างเสียง + ผลลัพธ์
                with gr.Column(scale=1, min_width=320):
                    btn_clone = gr.Button(
                        "🚀 เริ่มสร้างเสียง",
                        variant="primary",
                        size="lg",
                        elem_id="btn-clone",
                    )

                    output_audio = gr.Audio(
                        label="🔊 เสียงที่สร้างได้",
                        interactive=False,
                        elem_classes="audio-panel",
                    )

                    status_msg = gr.Textbox(
                        label="สถานะ",
                        interactive=False,
                        lines=2,
                        elem_id="status-msg",
                    )

        # ──────────────────────────────────────────────────────
        # Tab 2: ตั้งค่า (แยกออกมาให้ Tab 1 กระชับ)
        # ──────────────────────────────────────────────────────
        with gr.Tab("⚙️ ตั้งค่า"):
            gr.Markdown(
                "### ปรับแต่งการสร้างเสียง\nค่าเหล่านี้จะถูกบันทึกอัตโนมัติเมื่อกด **💾 บันทึก** และโหลดกลับมาเมื่อเปิดแอปครั้งถัดไป"
            )

            with gr.Row():
                with gr.Column(scale=1, min_width=350):
                    gr.Markdown("#### 🎤 การสร้างเสียง")

                    speed_slider = gr.Slider(
                        label="🔄 ความเร็วในการพูด",
                        minimum=0.5,
                        maximum=2.0,
                        value=current_settings["speed"],
                        step=0.1,
                        info="1.0 = ปกติ, ต่ำกว่า = ช้าลง, สูงกว่า = เร็วขึ้น",
                    )

                with gr.Column(scale=1, min_width=350):
                    gr.Markdown("#### 🔬 ขั้นสูง")

                    num_step_slider = gr.Slider(
                        label="จำนวนรอบ Decode (Steps)",
                        minimum=16,
                        maximum=64,
                        value=current_settings["num_step"],
                        step=4,
                        info="ยิ่งมาก = คุณภาพดีขึ้น แต่ใช้เวลานานขึ้น (ค่าเริ่มต้น 32)",
                    )

                    guidance_slider = gr.Slider(
                        label="Guidance Scale",
                        minimum=0.5,
                        maximum=5.0,
                        value=current_settings["guidance_scale"],
                        step=0.1,
                        info="ความเข้มในการยึดตามข้อความ (ค่าเริ่มต้น 2.0)",
                    )

                    temperature_slider = gr.Slider(
                        label="Temperature",
                        minimum=0.0,
                        maximum=2.0,
                        value=current_settings["class_temperature"],
                        step=0.1,
                        info="0 = ผลลัพธ์เหมือนเดิมทุกครั้ง, สูงขึ้น = มีความแปรผัน",
                    )

            with gr.Row():
                btn_save_settings = gr.Button(
                    "💾 บันทึกการตั้งค่า", variant="primary"
                )
                btn_reset_settings = gr.Button(
                    "🔄 รีเซ็ตเป็นค่าเริ่มต้น", variant="secondary"
                )

            gr.Markdown("---")
            gr.Markdown(
                "#### 🤖 จัดการโมเดล AI (OmniVoice-Thai)\nโมเดลถูกบันทึกไว้ที่เครื่องเพื่อความเร็วในการโหลด หากต้องการเช็กหรืออัปเดตเวอร์ชันล่าสุดจาก HuggingFace สามารถกดปุ่มด้านล่างได้"
            )
            with gr.Row():
                btn_update_model = gr.Button(
                    "⬇️ อัปเดตโมเดลเป็นเวอร์ชันล่าสุดจาก HuggingFace",
                    variant="secondary",
                )

            settings_status = gr.Textbox(
                label="สถานะ",
                interactive=False,
                elem_id="settings-status",
            )

        # ──────────────────────────────────────────────────────
        # Tab 3: จัดการคลังเสียง
        # ──────────────────────────────────────────────────────
        with gr.Tab("📁 จัดการคลังเสียง"):
            gr.Markdown(
                "### จัดการไฟล์เสียงต้นฉบับในคลัง\nอัปโหลดเสียงใหม่ หรือลบเสียงที่ไม่ต้องการ"
            )

            with gr.Row():
                # เพิ่มเสียง
                with gr.Column(scale=1, min_width=350):
                    gr.Markdown("#### ➕ เพิ่มเสียงใหม่")

                    upload_audio = gr.Audio(
                        label="อัปโหลดหรืออัดเสียง",
                        type="filepath",
                        elem_classes="audio-panel",
                    )
                    audio_name = gr.Textbox(
                        label="ตั้งชื่อไฟล์ (ภาษาอังกฤษ)",
                        placeholder="เช่น my_voice_clear",
                        info="หากไม่ตั้งชื่อ ระบบจะตั้งให้อัตโนมัติ",
                    )
                    ref_text_manage = gr.Textbox(
                        label="📝 ข้อความที่พูดในคลิป (Ref Text, ไม่บังคับ)",
                        placeholder="พิมพ์คำพูดในคลิป หรือกด 'ถอดเสียง' (ใส่หรือไม่ใส่ก็ได้)",
                        lines=2,
                        info="ไม่จำกัดความยาวคลิปเสียง จะมี Ref Text คู่กันหรือไม่ก็ได้",
                    )
                    with gr.Row():
                        btn_transcribe = gr.Button(
                            "🔍 ถอดเสียง (Whisper local)",
                            variant="secondary",
                        )
                        btn_save = gr.Button(
                            "💾 บันทึกลงคลัง",
                            variant="primary",
                        )

                # จัดการเสียงในคลัง
                with gr.Column(scale=1, min_width=350):
                    gr.Markdown("#### 🗑️ จัดการเสียงและข้อความคู่กัน")

                    manage_dropdown = gr.Dropdown(
                        label="เลือกไฟล์ในคลัง",
                        choices=get_audio_list(),
                        interactive=True,
                    )
                    manage_preview = gr.Audio(
                        label="ฟังเสียง",
                        interactive=False,
                        elem_classes="audio-panel",
                    )
                    manage_ref_text = gr.Textbox(
                        label="📝 ข้อความ Ref Text ที่จับคู่กับไฟล์นี้ (.txt)",
                        placeholder="ข้อความที่บันทึกคู่กับไฟล์เสียง สามารถแก้ไขแล้วกดบันทึกได้",
                        lines=2,
                    )
                    btn_save_ref_text = gr.Button(
                        "💾 บันทึกการแก้ไข Ref Text",
                        variant="secondary",
                    )
                    with gr.Row():
                        btn_delete = gr.Button(
                            "🗑️ ลบไฟล์ที่เลือก",
                            variant="stop",
                        )
                        btn_refresh = gr.Button(
                            "🔄 รีเฟรชรายการเสียง",
                            variant="secondary",
                        )

            with gr.Accordion(
                "✂️ ตัดช่วงเสียงสำหรับใช้เป็น Reference",
                open=False,
                elem_classes="settings-accordion",
            ):
                gr.Markdown(
                    "เลือกตัดช่วงเสียงที่ต้องการได้ตามอิสระ (ไม่จำกัดความยาว) แล้วคลิปที่ตัดจะถูกใส่ในช่องอัปโหลด "
                    "เพื่อให้ตั้งชื่อก่อนบันทึก (จะมี Ref Text หรือไม่ก็ได้)"
                )
                with gr.Row():
                    trim_start = gr.Slider(
                        label="เริ่มต้น (วินาที)",
                        minimum=0,
                        maximum=100,
                        value=0,
                        step=0.1,
                    )
                    trim_end = gr.Slider(
                        label="สิ้นสุด (วินาที)",
                        minimum=0,
                        maximum=100,
                        value=100,
                        step=0.1,
                    )
                with gr.Row():
                    btn_trim_upload = gr.Button(
                        "✂️ ตัดไฟล์ที่อัปโหลด", variant="secondary"
                    )
                    btn_trim_saved = gr.Button(
                        "✂️ ตัดไฟล์ที่เลือกในคลัง", variant="secondary"
                    )
                trim_status = gr.Textbox(
                    label="สถานะการตัดเสียง",
                    interactive=False,
                    show_label=False,
                    value="อัปโหลดไฟล์หรือเลือกไฟล์ในคลังก่อนตัด",
                )

            manage_status = gr.Textbox(
                label="สถานะ",
                interactive=False,
                elem_id="manage-status",
            )

        # ──────────────────────────────────────────────────────
        # Tab 4: วิธีใช้งาน
        # ──────────────────────────────────────────────────────
        with gr.Tab("📖 วิธีใช้งาน"):
            gr.Markdown(
                """
### 🎯 ขั้นตอนการใช้งาน

**1. เตรียมเสียงต้นฉบับ**
- ไปที่แท็บ **📁 จัดการคลังเสียง**
- อัปโหลดไฟล์เสียง หรือกดบันทึกเสียงจากไมโครโฟน
- แนะนำเสียงที่ **ชัดเจน ไม่มีเสียงรบกวน** (ไม่จำกัดความยาวคลิปเสียง สามารถใช้สั้นหรือยาวได้ตามสะดวก)
- รองรับไฟล์ `.wav` `.mp3` `.flac` `.ogg`

**2. พิมพ์ข้อความ**
- ไปที่แท็บ **🎤 โคลนเสียง**
- พิมพ์ข้อความภาษาไทยที่ต้องการให้พูด
- ดูช่อง **ตัวอย่างคำอ่าน** เพื่อตรวจสอบว่าระบบอ่านถูกต้อง

**3. สร้างเสียง**
- เลือกเสียงต้นฉบับจาก Dropdown
- กดปุ่ม **🚀 เริ่มสร้างเสียง**
- รอสักครู่ ผลลัพธ์จะแสดงด้านขวา

---

### 🇹🇭 ฟีเจอร์ภาษาไทย

ระบบจะแปลงข้อความอัตโนมัติก่อนสร้างเสียง:

| สิ่งที่พิมพ์ | ระบบอ่านเป็น |
|:---|:---|
| `ดีๆ` `เร็วๆ` | ดีดี, เร็วเร็ว (ขยายไม้ยมก) |
| `100` `1,500` | หนึ่งร้อย, หนึ่งพันห้าร้อย |
| `500 บาท` `฿1,000` | ห้าร้อยบาทถ้วน |
| `081-234-5678` | ศูนย์แปดหนึ่ง... (อ่านทีละตัว) |
| `25/12/2568` | วันที่ยี่สิบห้า เดือนธันวาคม... |
| `15%` | สิบห้าเปอร์เซ็นต์ |
| `user@mail.com` | ยูสเซอร์ แอท เมล ดอท คอม |
| `ที่ 1` | ที่หนึ่ง |

---

### ⚙️ ตั้งค่าที่สำคัญ

| ตั้งค่า | คำแนะนำ |
|:---|:---|
| **ความเร็ว** | `1.0` = ปกติ, ลอง `0.8`–`0.9` ถ้าพูดเร็วเกินไป |
| **คำบรรยายเสียงต้นฉบับ (Ref Text)** | ใส่หรือไม่ใส่ก็ได้ (หากไม่ใส่ระบบจะใช้ Whisper ช่วยฟังอัตโนมัติ) |
| **Steps** | ค่าเริ่มต้น `32`, ลอง `48`–`64` เพื่อคุณภาพที่ดีขึ้น |
| **Guidance Scale** | ค่าเริ่มต้น `2.0`, ลอง `1.5`–`3.0` |
| **Temperature** | `0.0` = ผลเหมือนเดิมทุกครั้ง, ลอง `0.3`–`0.5` เพื่อความหลากหลาย |

---

### 🎭 Non-Verbal Tags (เสียงเอฟเฟกต์)

แทรกลงในข้อความได้เลย เช่น `สวัสดีครับ [laughter] ตลกมาก`

| Tag | เสียง |
|:---|:---|
| `[laughter]` | หัวเราะ |
| `[sigh]` | ถอนหายใจ |
| `[surprise-ah]` `[surprise-oh]` `[surprise-wa]` | ตกใจ |
| `[question-ei]` `[question-ah]` | ถาม |
| `[confirmation-en]` | รับ (อืม) |
| `[dissatisfaction-hnn]` | ไม่พอใจ (หึ่ม) |

---

### 💡 เคล็ดลับเพื่อผลลัพธ์ที่ดี

- ✅ ใช้เสียงต้นฉบับที่ **ชัดเจน ไม่มีเสียงรบกวน** (ไม่จำกัดความยาวคลิปเสียง)
- ✅ **Ref Text (คำบรรยายเสียงต้นฉบับ)** สามารถใส่เพื่อให้ได้จังหวะที่แม่นยำที่สุด หรือจะไม่ใส่ก็ได้เพื่อให้สะดวกและรวดเร็ว
- ✅ ข้อความไม่ควรยาวเกินไป (**ไม่เกิน 500 ตัวอักษร**)
- ✅ ใช้ **ภาษาไทย** เป็นหลัก (ภาษาอังกฤษจะมีระบบ CMUdict ช่วยอ่านคำศัพท์อัตโนมัติ)
- ✅ ตรวจสอบ **ตัวอย่างคำอ่าน** ก่อนกดสร้าง
- ✅ ลอง **เพิ่ม Steps** เป็น 48 หรือ 64 ถ้าเสียงยังไม่ดีพอ
- ⚠️ ผลลัพธ์อาจไม่สมบูรณ์กับข้อความที่ **สั้นมาก** หรือ **ยาวมาก**
""",
                elem_id="help-content",
            )

    # ╔══════════════════════════════════════════════════════════╗
    # ║  Event Handlers                                         ║
    # ╚══════════════════════════════════════════════════════════╝

    # --- Global Timer ---
    model_timer.tick(
        fn=get_model_load_status,
        outputs=[global_status, model_timer],
    )

    # --- Tab 1: โคลนเสียง ---

    # อัปเดต character count + normalized preview ใน callback เดียว
    input_text.change(
        fn=update_text_metadata,
        inputs=input_text,
        outputs=[char_count, norm_preview],
    )

    # อัปเดต preview เสียง และดึง Ref Text (.txt) เมื่อเลือก Dropdown
    ref_dropdown.change(
        fn=update_preview,
        inputs=ref_dropdown,
        outputs=[ref_preview, ref_text_input],
    )
    # บันทึกการเลือกล่าสุดลง settings.json แบบอัตโนมัติ
    ref_dropdown.change(
        fn=save_last_ref_audio,
        inputs=ref_dropdown,
        outputs=None,
    )

    # กดโคลนเสียง
    btn_clone.click(
        fn=clone_voice,
        inputs=[
            input_text,
            ref_dropdown,
            ref_text_input,
            speed_slider,
            num_step_slider,
            guidance_slider,
            temperature_slider,
        ],
        outputs=[output_audio, status_msg],
    )

    # --- Non-Verbal Tag Buttons ---
    for btn, tag in tag_buttons:
        btn.click(
            fn=lambda text, t=tag: insert_tag(text, t),
            inputs=input_text,
            outputs=input_text,
        )

    # --- Tab 2: ตั้งค่า ---
    btn_save_settings.click(
        fn=save_settings,
        inputs=[
            speed_slider,
            num_step_slider,
            guidance_slider,
            temperature_slider,
        ],
        outputs=settings_status,
    )
    btn_reset_settings.click(
        fn=reset_settings,
        outputs=[
            speed_slider,
            num_step_slider,
            guidance_slider,
            temperature_slider,
            settings_status,
        ],
    )
    btn_update_model.click(
        fn=update_model_ui,
        outputs=settings_status,
    )

    # --- Tab 3: จัดการคลังเสียง ---

    # Preview เสียง และดึง Ref Text ใน manage dropdown
    manage_dropdown.change(
        fn=update_preview,
        inputs=manage_dropdown,
        outputs=[manage_preview, manage_ref_text],
    )
    manage_dropdown.change(
        fn=get_trim_controls_for_saved_audio,
        inputs=manage_dropdown,
        outputs=[trim_start, trim_end, trim_status],
    )

    # เตรียมตัวเลือกช่วงตัดเมื่ออัปโหลดไฟล์ใหม่
    upload_audio.change(
        fn=get_trim_controls,
        inputs=upload_audio,
        outputs=[trim_start, trim_end, trim_status],
    )

    # คลิปที่ตัดจะกลับไปอยู่ในช่องอัปโหลดเพื่อให้ผู้ใช้ใส่ชื่อและ Ref Text ก่อนบันทึก
    btn_trim_upload.click(
        fn=trim_audio_file,
        inputs=[upload_audio, trim_start, trim_end],
        outputs=[upload_audio, trim_status],
    )
    btn_trim_saved.click(
        fn=trim_saved_audio,
        inputs=[manage_dropdown, trim_start, trim_end],
        outputs=[upload_audio, trim_status],
    )

    # ถอดเสียงอัตโนมัติด้วย Whisper
    btn_transcribe.click(
        fn=transcribe_audio_file,
        inputs=upload_audio,
        outputs=ref_text_manage,
    )

    # บันทึกเสียงใหม่พร้อมข้อความคู่กัน
    def save_and_sync(temp_path, custom_name, ref_text):
        result_dropdown, status = save_audio(temp_path, custom_name, ref_text)
        audios = get_audio_list()
        return result_dropdown, gr.update(choices=audios), status

    btn_save.click(
        fn=save_and_sync,
        inputs=[upload_audio, audio_name, ref_text_manage],
        outputs=[ref_dropdown, manage_dropdown, manage_status],
    )

    # บันทึกการแก้ไขเฉพาะ Ref Text สำหรับเสียงที่มีในคลัง
    btn_save_ref_text.click(
        fn=save_ref_text_only,
        inputs=[manage_dropdown, manage_ref_text],
        outputs=manage_status,
    )

    # ลบเสียงพร้อมข้อความคู่กัน
    def delete_and_sync(filename):
        result_dropdown, preview, ref_txt, status = delete_audio(filename)
        audios = get_audio_list()
        return (
            result_dropdown,
            gr.update(choices=audios, value=None),
            preview,
            ref_txt,
            status,
        )

    btn_delete.click(
        fn=delete_and_sync,
        inputs=manage_dropdown,
        outputs=[ref_dropdown, manage_dropdown, manage_preview, manage_ref_text, manage_status],
    )

    # รีเฟรชรายการ (อัปเดตทั้ง 2 dropdown)
    def refresh_and_sync():
        dropdown_update, status = refresh_audio_list()
        return dropdown_update, dropdown_update, status

    btn_refresh.click(
        fn=refresh_and_sync,
        outputs=[ref_dropdown, manage_dropdown, manage_status],
    )


# ╔══════════════════════════════════════════════════════════════╗
# ║  Launch                                                     ║
# ╚══════════════════════════════════════════════════════════════╝

if __name__ == "__main__":

    def find_free_port(start_port=7860, max_attempts=10):
        """หา port ที่ว่างอยู่ เริ่มจาก start_port"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("0.0.0.0", port))
                    return port
            except OSError:
                print(f"⚠️ Port {port} ไม่ว่าง ลองถัดไป...")
        print("⚠️ หา port ว่างไม่ได้ ให้ Gradio เลือกอัตโนมัติ")
        return None

    port = find_free_port()
    if port and port != 7860:
        print(f"🔀 ใช้ port {port} แทน (7860 ไม่ว่าง)")

    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        inbrowser=True,
        theme=custom_theme,
        css=custom_css,
        js=dark_mode_js,
    )
