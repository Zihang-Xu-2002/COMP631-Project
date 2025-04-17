# gradio
import gradio as gr
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from retriever.main import get_searcher_and_corpus, rag_retrieve
from frontend.components import floating_scroll_button

get_searcher_and_corpus() 

def rag_chat(query, history):
    docs = rag_retrieve(query)
    
    # Simulated response (can be replaced with LLM-generated content)
    summary = f"I reviewed {len(docs)} relevant documents. It's a very interesting question."

    # Document summary list
    #doc_texts = [f"{d['title']}: {d['text'][:100]}..." for d in docs]
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

    # Build the chat history entry
    new_entry = (
    f"<p><strong>You asked:</strong> {query}</p>"
    f"<p><strong>RAG Response:</strong> {summary}</p>"
    f"<p><strong>Retrieved Documents:</strong></p>" + "\n".join(doc_texts)
)

    history = history or []
    history.append(new_entry)
    return "\n\n---\n\n".join(history), history


with gr.Blocks() as demo:
    gr.Markdown("### 📚 COMP 631 Chatbot")

    
    output = gr.HTML()

    floating_scroll_button()
   

    gr.HTML('<a id="input-anchor"></a>') 

    textbox = gr.Textbox(label="Please Enter Your Question")
    submit = gr.Button("Submit")
    clear = gr.Button("Clear")
    state = gr.State([])

    submit.click(rag_chat, [textbox, state], [output, state])
    textbox.submit(rag_chat, [textbox, state], [output, state])
    clear.click(lambda: ("", []), None, [output, state])


demo.launch()
