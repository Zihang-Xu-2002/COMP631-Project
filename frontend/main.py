import gradio as gr
import sys
import os
import requests
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from retriever.main import get_searcher_and_corpus, rag_retrieve
from frontend.components import floating_scroll_button


get_searcher_and_corpus()

API_KEY = "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"

# 调用 LLaMA，只提问
def call_llama_only_query(query):
    prompt = f"""You are a helpful assistant. Please answer the user's question clearly and concisely.

User Question:
{query}
"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourdomain.com",
        "X-Title": "LLaMA-Demo",
    }

    payload = {
        "model": "shisa-ai/shisa-v2-llama3.3-70b:free",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload)
    )

    try:
        res_json = response.json()
        return res_json["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LLaMA Error] {str(e)}"

def call_llama_with_docs(query, docs):
    context = "\n\n".join([f"Title: {d['title']}\nContent: {d['text']}" for d in docs])
    prompt = f"""You are a helpful assistant. Based on the following retrieved documents, answer the user's question.

User Question:
{query}

Retrieved Documents:
{context[:3000]}

Please provide a helpful and concise answer based on the content above.
"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourdomain.com",
        "X-Title": "LLaMA-Demo",
    }

    payload = {
        "model": "shisa-ai/shisa-v2-llama3.3-70b:free",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload)
    )

    try:
        res_json = response.json()
        return res_json["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LLaMA Error] {str(e)}"

def handle_user_only(query, history):
    history = history or []
    user_answer = call_llama_only_query(query)
    history.append(f"<p><strong>You asked:</strong> {query}</p>")
    return "\n\n---\n\n".join(history), history, user_answer, ""

def handle_rag_and_docs(query, history):
    docs = rag_retrieve(query)

    doc_texts = []
    for d in docs:
        preview = d["text"][:100]
        full = d["text"]
        entry = f"""
            <details>
            <summary><strong>{d['title']}</strong>: {preview}...</summary>
            <p>{full}</p>
            </details>
        """
        doc_texts.append(entry)

    history = history or []
    history.append(
        f"<p><strong>Retrieved Documents:</strong></p>" + "\n".join(doc_texts)
    )
    rag_answer = call_llama_with_docs(query, docs)
    return "\n\n---\n\n".join(history), history, rag_answer

with gr.Blocks() as demo:
    gr.Markdown("## 📚 COMP 631 Chatbot with LLaMA AI")

    output_history = gr.HTML(label="History + Retrieved Documents")
    output_answer_only = gr.Textbox(label="🧠 LLaMA Answer (Only Question)", lines=6)
    output_answer_rag = gr.Textbox(label="📖 LLaMA Answer (With RAG)", lines=6)

    floating_scroll_button()

    gr.HTML('<a id="input-anchor"></a>')
    textbox = gr.Textbox(label="Please Enter Your Question", lines=2,
                         placeholder="e.g., What is the impact of AI on education?")
    submit = gr.Button("Submit")
    clear = gr.Button("Clear")

    state = gr.State([])

    # 只提问的回答
    submit.click(handle_user_only, [textbox, state],
                 [output_history, state, output_answer_only, output_answer_rag])

    # RAG的回答
    submit.click(handle_rag_and_docs, [textbox, state],
                 [output_history, state, output_answer_rag])

    textbox.submit(handle_user_only, [textbox, state],
                   [output_history, state, output_answer_only, output_answer_rag])
    textbox.submit(handle_rag_and_docs, [textbox, state],
                   [output_history, state, output_answer_rag])

    clear.click(lambda: ("", [], "", ""), None,
                [output_history, state, output_answer_only, output_answer_rag])

demo.launch()