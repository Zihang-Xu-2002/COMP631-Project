from datasets import load_dataset
from sentence_transformers import SentenceTransformer
import types
from typing import List, Dict
import torch
from retriever.exact_search import DenseRetrievalExactSearch
import json
import os

# 模型与检索器全局缓存
searcher = None
corpus = None

def get_searcher_and_corpus(
    corpus_path="../retriever/data/corpus.csv",
    model_name="jxm/cde-small-v2",
    ratio=1.0
):
    global searcher, corpus

    dataset = load_dataset("csv", data_files=corpus_path, split="train")
    if "id" in dataset.column_names:
        dataset = dataset.remove_columns("id")
    ids = list(range(len(dataset))) 
    dataset = dataset.add_column("id", ids)

    print(f"✅ Dataset contains: {len(dataset)} documents totally")

    # 清洗空值
    if any(x["title"] is None for x in dataset):
        print("⚠️ Some titles are None")
    if any(x["text"] is None for x in dataset):
        print("⚠️ Some texts are None")

    sample_size = int(len(dataset) * ratio)
    corpus = {
        example["id"]: {
            "title": example["title"],
            "text": example["text"]
        }
        for example in dataset.select(range(sample_size))
    }

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = SentenceTransformer(model_name, trust_remote_code=True)
    model = model.to(device)

    # patch encode_xxx 方法
    def encode_queries(self, queries: List[str], **kwargs):
        return self.encode(queries, **kwargs)

    def encode_corpus(self, corpus_list: List[Dict[str, str]], **kwargs):
        texts = [entry.get("title", "") + " " + entry.get("text", "") for entry in corpus_list]
        return self.encode(texts, **kwargs)

    model.encode_queries = types.MethodType(encode_queries, model)
    model.encode_corpus = types.MethodType(encode_corpus, model)

    if hasattr(model, "encode_queries") and hasattr(model, "encode_corpus"):
        print("✅ Model Loaded Successfully!")

    searcher = DenseRetrievalExactSearch(model=model, batch_size=120, corpus_chunk_size=50000)
    return searcher, corpus


def rag_retrieve(query: str, top_k=10, score_function="cos_sim"):
    """用于 frontend 调用：基于 query 返回 top_k 检索文档"""
    if searcher is None or corpus is None:
        raise RuntimeError("Retriever not initialized. Call get_searcher_and_corpus() first.")

    results = searcher.search(corpus=corpus, queries={"1": query}, top_k=top_k, score_function=score_function)
    doc_list = []
    for doc_id in results["1"]:
        entry = corpus[int(doc_id)]
        doc_list.append({
            "title": entry["title"],
            "text": entry["text"]
        })
    return doc_list


def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


# CLI 交互接口（保留）
if __name__ == "__main__":
    get_searcher_and_corpus()
    clear_terminal()
    print("\n🧠 Welcome to the Dense Retriever Agent! Type query: <your query> to search, or type exit to quit. Type help for more commands.")

    while True:
        user_input = input("🔎 Enter command: ").strip()
        if user_input.lower() == "exit":
            print("👋 Exiting the retriever agent. Goodbye!")
            break
        elif user_input.startswith("query:"):
            query = user_input[len("query:"):].strip()
            results = rag_retrieve(query, top_k=5)
            print(f"\n🎯 Top 5 Results:\n")
            for i, doc in enumerate(results, 1):
                preview = "\n".join(doc["text"].strip().splitlines()[:5])
                print(f"[{i}] {doc['title']}\n{preview}\n")
        elif user_input.startswith("show:"):
            try:
                doc_id = int(user_input[len("show:"):].strip())
                if doc_id in corpus:
                    print(f"\n📖 {corpus[doc_id]['title']}\n{corpus[doc_id]['text']}\n")
                else:
                    print(f"❌ No document with ID {doc_id}")
            except:
                print("❗ Invalid show command")
        elif user_input.lower() == "help":
            print("""
                🧠 Commands:
                - query:<text>
                - show:<doc_id>
                - exit
                """)
        else:
            print("❗Unknown command. Try `query: your question` or `help`.")
