import gradio as gr

def floating_scroll_button(anchor_id="input-anchor", label="🔽 Jump to Input"):
    """Insert a floating button that scrolls to the specified anchor_id"""
    gr.HTML(f"""
    <style>
    #scroll-button {{
        position: fixed;
        top: 30px;
        right: 30px;
        z-index: 100;
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 12px 16px;
        border-radius: 8px;
        font-size: 14px;
        cursor: pointer;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
    }}
    #scroll-button:hover {{
        background-color: #45a049;
    }}
    </style>

    <button id="scroll-button" onclick="document.getElementById('{anchor_id}').scrollIntoView({{ behavior: 'smooth' }})">
        {label}
    </button>
    """)
