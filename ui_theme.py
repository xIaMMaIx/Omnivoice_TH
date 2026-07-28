# -*- coding: utf-8 -*-
"""
ui_theme.py — Dark Grey Monochrome Theme, Custom CSS และ JavaScript โหมดมืด
"""

import gradio as gr

custom_theme = gr.themes.Soft(
    primary_hue=gr.themes.colors.slate,
    secondary_hue=gr.themes.colors.zinc,
    neutral_hue=gr.themes.colors.gray,
    spacing_size=gr.themes.sizes.spacing_md,
    radius_size=gr.themes.sizes.radius_md,
    text_size=gr.themes.sizes.text_md,
    font=[
        "Noto Sans Thai",
        "Segoe UI",
        "Tahoma",
        "Thonburi",
        "Inter",
        "sans-serif",
    ],
    font_mono=["IBM Plex Mono", "Consolas", "Courier New", "monospace"],
).set(
    # พื้นหลังหลัก
    body_background_fill="#111317",
    body_background_fill_dark="#111317",
    body_text_color="#e2e8f0",
    body_text_color_dark="#e2e8f0",
    # Block / Panel
    block_background_fill="#17191e",
    block_background_fill_dark="#17191e",
    block_border_color="#262932",
    block_border_color_dark="#262932",
    block_label_text_color="#94a3b8",
    block_label_text_color_dark="#94a3b8",
    block_title_text_color="#f1f5f9",
    block_title_text_color_dark="#f1f5f9",
    # Input
    input_background_fill="#1c1f26",
    input_background_fill_dark="#1c1f26",
    input_border_color="#333842",
    input_border_color_dark="#333842",
    input_placeholder_color="#64748b",
    input_placeholder_color_dark="#64748b",
    # Button
    button_primary_background_fill="linear-gradient(135deg, #334155 0%, #475569 50%, #64748b 100%)",
    button_primary_background_fill_dark="linear-gradient(135deg, #334155 0%, #475569 50%, #64748b 100%)",
    button_primary_background_fill_hover="linear-gradient(135deg, #475569 0%, #64748b 50%, #94a3b8 100%)",
    button_primary_background_fill_hover_dark="linear-gradient(135deg, #475569 0%, #64748b 50%, #94a3b8 100%)",
    button_primary_text_color="#f8fafc",
    button_primary_text_color_dark="#f8fafc",
    button_secondary_background_fill="#21252e",
    button_secondary_background_fill_dark="#21252e",
    button_secondary_text_color="#e2e8f0",
    button_secondary_text_color_dark="#e2e8f0",
    button_cancel_background_fill="#7f1d1d",
    button_cancel_background_fill_dark="#7f1d1d",
    button_cancel_text_color="#fca5a5",
    button_cancel_text_color_dark="#fca5a5",
    # Shadow
    shadow_drop="0 4px 24px rgba(0, 0, 0, 0.25)",
    shadow_drop_lg="0 8px 32px rgba(0, 0, 0, 0.35)",
    shadow_spread="2px",
    # Tab
    block_label_background_fill="#21252e",
    block_label_background_fill_dark="#21252e",
)

# JavaScript สำหรับบังคับ Dark Mode
dark_mode_js = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

# Custom CSS
custom_css = """
/* ===== ซ่อน Footer ===== */
footer { display: none !important; }

/* ===== Header Gradient ===== */
#app-header {
    text-align: center;
    padding: 16px 16px 8px 16px;
    margin-bottom: 4px;
}
#app-header h1 {
    background: linear-gradient(135deg, #94a3b8, #cbd5e1, #e2e8f0, #f8fafc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 1.85em !important;
    font-weight: 800 !important;
    margin-bottom: 4px !important;
    letter-spacing: -0.02em;
}
#app-header p {
    color: #94a3b8 !important;
    font-size: 0.95em !important;
    margin-top: 0 !important;
}

/* ===== Tab Styling ===== */
.tabs > .tab-nav > button {
    font-size: 1.05em !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
    border-radius: 10px 10px 0 0 !important;
    transition: all 0.2s ease !important;
}
.tabs > .tab-nav > button.selected {
    background: linear-gradient(135deg, #1e222b, #17191e) !important;
    color: #e2e8f0 !important;
    border-bottom: 3px solid #64748b !important;
}

/* ===== Clone Button (Vibrant Orange Gradient) ===== */
#btn-clone {
    background: linear-gradient(135deg, #ea580c 0%, #f97316 50%, #fb923c 100%) !important;
    color: #ffffff !important;
    border: none !important;
    font-size: 1.15em !important;
    font-weight: 700 !important;
    padding: 11px 18px !important;
    border-radius: 12px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 20px rgba(249, 115, 22, 0.35) !important;
    letter-spacing: 0.02em;
}
#btn-clone:hover {
    background: linear-gradient(135deg, #f97316 0%, #fb923c 50%, #fdba74 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(249, 115, 22, 0.55) !important;
}
#btn-clone:active {
    transform: translateY(0) !important;
}

/* ===== Character Counter ===== */
#char-count textarea {
    text-align: right !important;
    color: #94a3b8 !important;
    font-size: 0.85em !important;
    border: none !important;
    background: transparent !important;
    min-height: 0 !important;
    padding: 4px 8px !important;
}

/* ===== Normalized Preview ===== */
#norm-preview textarea {
    color: #cbd5e1 !important;
    font-style: italic !important;
    background: #1c1f26 !important;
    border-color: #333842 !important;
    border-radius: 10px !important;
}

/* ===== Status Message ===== */
#status-msg textarea {
    font-weight: 500 !important;
    border-radius: 10px !important;
}

/* ===== Card-like Sections ===== */
.panel-card {
    border: 1px solid #262932 !important;
    border-radius: 14px !important;
    padding: 8px !important;
    background: #17191e !important;
}

/* ===== Audio Components ===== */
.audio-panel {
    border-radius: 12px !important;
    overflow: hidden;
}

/* ===== Non-Verbal Tag Buttons ===== */
.tag-btn {
    min-width: auto !important;
    padding: 6px 12px !important;
    font-size: 0.85em !important;
    border-radius: 20px !important;
    background: #21252e !important;
    border: 1px solid #333842 !important;
    color: #cbd5e1 !important;
    transition: all 0.2s ease !important;
}
.tag-btn:hover {
    background: #2b303c !important;
    border-color: #64748b !important;
    transform: scale(1.05) !important;
}

/* ===== Settings Section ===== */
.settings-accordion {
    border: 1px solid #262932 !important;
    border-radius: 12px !important;
    background: #14161a !important;
}

/* ===== Examples ===== */
.examples-accordion {
    margin-top: 2px !important;
}
.examples-table {
    border-radius: 10px !important;
    overflow: hidden;
}
.examples-table button {
    transition: all 0.15s ease !important;
}
.examples-table button:hover {
    background: #21252e !important;
    color: #f1f5f9 !important;
}

/* ===== Help Tab ===== */
#help-content {
    line-height: 1.8 !important;
}
#help-content h3 {
    color: #cbd5e1 !important;
    border-bottom: 1px solid #262932;
    padding-bottom: 6px;
    margin-top: 20px !important;
}
#help-content code {
    background: #21252e !important;
    color: #e2e8f0 !important;
    padding: 2px 6px;
    border-radius: 4px;
}

/* ===== Responsive ===== */
/* Columns wrap automatically: 3 on wide desktops, 2 on mid-sized screens, 1 on mobile. */
#clone-workspace {
    gap: 14px !important;
}

@media (max-width: 768px) {
    #app-header h1 {
        font-size: 1.5em !important;
    }
    #btn-clone {
        font-size: 1em !important;
    }
}
"""
