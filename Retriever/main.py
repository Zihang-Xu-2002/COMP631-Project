from datasets import load_dataset
from sentence_transformers import SentenceTransformer
import types
from typing import List, Dict
import torch
import logging
from exact_search import DenseRetrievalExactSearch

dataset = load_dataset("csv", data_files="./Retriever/data/corpus.csv", split="train")
if "id" in dataset.column_names:
    dataset = dataset.remove_columns("id")
ids = list(range(len(dataset))) 
dataset = dataset.add_column("id", ids)

# 打印整体数据量
print(f"✅ 数据集总量: {len(dataset)} 条记录")

none_in_title = any(example["title"] is None for example in dataset)
none_in_text = any(example["text"] is None for example in dataset)

if none_in_title or none_in_text:
    print("⚠️ 数据集中存在 None 值:")
    if none_in_title:
        print(" - 'title' 列中存在 None 值")
    if none_in_text:
        print(" - 'text' 列中存在 None 值")
else:
    print("✅ 数据集中不存在 None 值")

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
queries = {
    "1": "Software"
}
rtn = searcher.search(corpus=corpus, queries=queries, top_k=5, score_function="dot")
print(len(rtn))
# save results to json
import json

with open("results.json", "w") as f:
    json.dump(rtn, f, indent=4)
print("✅ Results saved successfully!")