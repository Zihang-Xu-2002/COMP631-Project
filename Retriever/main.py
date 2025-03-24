from datasets import load_dataset
from sentence_transformers import SentenceTransformer
import types
from typing import List, Dict
import torch
import logging
from exact_search import DenseRetrievalExactSearch
import json
import os

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')


dataset = load_dataset("csv", data_files="./Retriever/data/corpus.csv", split="train")
if "id" in dataset.column_names:
    dataset = dataset.remove_columns("id")
ids = list(range(len(dataset))) 
dataset = dataset.add_column("id", ids)

# 打印整体数据量
print(f"✅ Dataset contains: {len(dataset)} documents totally")

none_in_title = any(example["title"] is None for example in dataset)
none_in_text = any(example["text"] is None for example in dataset)

if none_in_title or none_in_text:
    print("⚠️ There exists None in the dataset:")
    if none_in_title:
        print(" - Column 'title' has None values")
    if none_in_text:
        print(" - Column 'text' has None values")
else:
    print("✅ No None values in the dataset")

ratio = 1
sample_size = int(len(dataset) * ratio)

corpus = {
    example["id"]: {
        "title": example["title"],
        "text": example["text"]
    }
    for example in dataset.select(range(sample_size))
}
device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
model = SentenceTransformer("jxm/cde-small-v2", 
trust_remote_code=True) 
model = model.to(device)

# 定义 encode_queries 方法
def encode_queries(self, queries: List[str], batch_size: int = 32, show_progress_bar: bool = False, convert_to_tensor: bool = False, **kwargs):
    return self.encode(queries, batch_size=batch_size, show_progress_bar=show_progress_bar, convert_to_tensor=convert_to_tensor, **kwargs)

# 定义 encode_corpus 方法
def encode_corpus(self, corpus: List[Dict[str, str]], batch_size: int = 32, show_progress_bar: bool = False, convert_to_tensor: bool = False, **kwargs):
    corpus_texts = [entry.get('title', '') + ' ' + entry.get('text', '') for entry in corpus]
    return self.encode(corpus_texts, batch_size=batch_size, show_progress_bar=show_progress_bar, convert_to_tensor=convert_to_tensor, **kwargs)

model.encode_queries = types.MethodType(encode_queries, model)
model.encode_corpus = types.MethodType(encode_corpus, model)

if hasattr(model, "encode_queries") and hasattr(model, "encode_corpus"):
    print("✅ Model Loaded Successfully!")
else:
    print("❌ Model Loading Failed!")

searcher = DenseRetrievalExactSearch(model=model, batch_size=120, corpus_chunk_size=50000)
# queries = {
#     "1": "Software Engineer jobs"
# }
# rtn = searcher.search(corpus=corpus, queries=queries, top_k=5, score_function="dot")
# print(len(rtn))
# # save results to json
# import json

# with open("results.json", "w") as f:
#     json.dump(rtn, f, indent=4)
# print("✅ Results saved successfully!")
clear_terminal()
print("\n🧠 Welcome to the Dense Retriever Agent! Type query: <your query> to search, or type exit to quit. Type help for more commands.")

while True:
    user_input = input("🔎 Enter command: ").strip()
    if user_input.lower() == "exit":
        print("👋 Exiting the retriever agent. Goodbye!")
        break
    elif user_input.startswith("query:"):
        query_content = user_input[len("query:"):].strip()
        queries = {"1": query_content}

        # Run retrieval
        results = searcher.search(corpus=corpus, queries=queries, top_k=5, score_function="cos_sim")

        print(f"\n🎯 Top 5 Results:\n")
        for rank, (doc_id, score) in enumerate(results["1"].items(), start=1):
            doc_id = int(doc_id)  # ensure it's an int to index into corpus
            title = corpus[doc_id]["title"]
            text = corpus[doc_id]["text"]
            first_5_lines = "\n".join(text.strip().splitlines()[:5])
            print(f"[{rank}] Doc ID: {doc_id}, Score: {score:.4f}")
            print(f"📌 Title: {title}")
            print(f"📝 Text Preview:\n{first_5_lines}\n")

        # Save results
        with open("results.json", "w") as f:
            json.dump(results, f, indent=4)
        print("✅ Results saved to results.json\n")
    elif user_input.startswith("show:"):
        try:
            doc_id = int(user_input[len("show:"):].strip())
            if doc_id in corpus:
                title = corpus[doc_id]["title"]
                text = corpus[doc_id]["text"]
                print(f"\n📖 Full Document - ID: {doc_id}")
                print(f"Title: {title}")
                print(f"Text:\n{text}\n")
            else:
                print(f"❌ Document with ID {doc_id} not found in corpus.\n")
        except ValueError:
            print("❗ Invalid document ID. Usage: show:<id>\n")
    elif user_input.lower() == "help":
        print("""
                🧠 Available Commands:

                1️⃣  query:<your search query>
                    - Description: Search the corpus using a natural language query.
                    - Example: query: software engineer jobs

                2️⃣  show:<corpus_id>
                    - Description: Show the full document with the specified corpus ID.
                    - Example: show:123

                3️⃣  exit
                    - Description: Exit the retriever agent.
                """)


    else:
        print("❗Please enter your query as `query: <your question>`, or type `exit` to quit.\n")
