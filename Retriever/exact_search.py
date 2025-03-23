from __future__ import annotations

import heapq
import logging

import torch

from util import cos_sim, dot_score

logger = logging.getLogger(__name__)

from abc import ABC, abstractmethod

import os
import pickle
import json
import hashlib


class BaseSearch(ABC):
    @abstractmethod
    def search(
        self,
        corpus: dict[str, dict[str, str]],
        queries: dict[str, str],
        top_k: int,
        **kwargs,
    ) -> dict[str, dict[str, float]]:
        pass

def get_corpus_id(corpus: dict[str, dict[str, str]]) -> str:
    # 对 corpus 的内容做稳定 hash（注意大 corpora 会慢）
    serialized = json.dumps({k: corpus[k] for k in sorted(corpus)}, sort_keys=True)
    return hashlib.md5(serialized.encode('utf-8')).hexdigest()

# DenseRetrievalExactSearch is parent class for any dense model that can be used for retrieval
# Abstract class is BaseSearch
class DenseRetrievalExactSearch(BaseSearch):
    def __init__(self, model, batch_size: int = 128, corpus_chunk_size: int = 50000, cache_dir: str = "./cache", **kwargs):
        # model is class that provides encode_corpus() and encode_queries()
        self.model = model
        self.batch_size = batch_size
        self.score_functions = {"cos_sim": cos_sim, "dot": dot_score}
        self.score_function_desc = {
            "cos_sim": "Cosine Similarity",
            "dot": "Dot Product",
        }
        self.corpus_chunk_size = corpus_chunk_size
        self.show_progress_bar = kwargs.get("show_progress_bar", True)
        self.convert_to_tensor = kwargs.get("convert_to_tensor", True)
        self.results = {}
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def search(
        self,
        corpus: dict[str, dict[str, str]],
        queries: dict[str, str],
        top_k: int,
        score_function: str,
        return_sorted: bool = False,
        **kwargs,
    ) -> dict[str, dict[str, float]]:
        # Create embeddings for all queries using model.encode_queries()
        # Runs semantic search against the corpus embeddings
        # Returns a ranked list with the corpus ids
        if score_function not in self.score_functions:
            raise ValueError(
                f"score function: {score_function} must be either (cos_sim) for cosine similarity or (dot) for dot product"
            )

        logger.info("Encoding Queries...")
        query_ids = list(queries.keys())
        self.results = {qid: {} for qid in query_ids}
        queries_list = [queries[qid] for qid in queries]
        query_embeddings = self.model.encode_queries(
            queries_list,
            batch_size=self.batch_size,
            show_progress_bar=self.show_progress_bar,
            convert_to_tensor=self.convert_to_tensor,
        )

        logger.info("Sorting Corpus by document length (Longest first)...")

        corpus_ids = sorted(
            corpus,
            key=lambda k: len(corpus[k].get("title", "") + corpus[k].get("text", "")),
            reverse=True,
        )
        corpus_list = [corpus[cid] for cid in corpus_ids]

        # === 加载或计算 Corpus Embeddings ===
        corpus_id_hash = get_corpus_id(corpus)
        corpus_embeddings = self._load_cached_corpus_embeddings(corpus_id_hash)

        if corpus_embeddings is not None:
            logger.info("✅ Loaded cached corpus embeddings.")
        else:
            logger.info("Encoding Corpus in batches... Warning: This might take a while!")
            all_embeddings = []
            for batch_num, corpus_start_idx in enumerate(range(0, len(corpus_list), self.corpus_chunk_size)):
                logger.info(f"Encoding Batch {batch_num + 1}...")
                corpus_end_idx = min(corpus_start_idx + self.corpus_chunk_size, len(corpus_list))
                sub_embeddings = self.model.encode_corpus(
                    corpus_list[corpus_start_idx:corpus_end_idx],
                    batch_size=self.batch_size,
                    show_progress_bar=self.show_progress_bar,
                    convert_to_tensor=self.convert_to_tensor,
                )
                all_embeddings.append(sub_embeddings)

            corpus_embeddings = torch.cat(all_embeddings, dim=0)
            self._save_corpus_embeddings(corpus_id_hash, corpus_embeddings)

        logger.info(f"Scoring Function: {self.score_function_desc[score_function]} ({score_function})")

        cos_scores = self.score_functions[score_function](query_embeddings, corpus_embeddings)
        cos_scores[torch.isnan(cos_scores)] = -1

        # 取 top-k（按列走，每个 query）
        cos_scores_top_k_values, cos_scores_top_k_idx = torch.topk(
            cos_scores,
            min(top_k + 1, corpus_embeddings.size(0)),
            dim=1,
            largest=True,
            sorted=return_sorted,
        )
        cos_scores_top_k_values = cos_scores_top_k_values.cpu().tolist()
        cos_scores_top_k_idx = cos_scores_top_k_idx.cpu().tolist()

        # 汇总结果
        for query_itr in range(len(query_embeddings)):
            query_id = query_ids[query_itr]
            for sub_idx, score in zip(cos_scores_top_k_idx[query_itr], cos_scores_top_k_values[query_itr]):
                corpus_id = corpus_ids[sub_idx]
                if corpus_id != query_id:
                    self.results[query_id][corpus_id] = score

        return self.results
    
    def _corpus_cache_path(self, corpus_id: str) -> str:
        return os.path.join(self.cache_dir, f"corpus_emb_{corpus_id}.pt")

    def _load_cached_corpus_embeddings(self, corpus_id: str):
        path = self._corpus_cache_path(corpus_id)
        if os.path.exists(path):
            return torch.load(path)
        return None

    def _save_corpus_embeddings(self, corpus_id: str, embeddings: torch.Tensor):
        path = self._corpus_cache_path(corpus_id)
        torch.save(embeddings, path)
