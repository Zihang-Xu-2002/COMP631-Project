import pandas as pd
import numpy as np
import os
import json
import glob



"""
Attribute names for the job data
URL ID,JobTitle,detailText,viewJobQualificationItem,viewJobBenefitItem,viewJobBodyJobFullDescriptionContent,original URL

Attribute names for wiki data 
title, paragraph

Corpus : 
Common attribute names : title(for job, JobTitie is title), text(for job, it concats attributes except URL ID. For wiki, it concats paragraph)

"""
data_base_path = './web_scraper/data/'
data_target_path = './Retriever/data/'
job_folder = os.path.join(data_base_path, 'job')

merged_job_path = os.path.join(data_target_path, 'job_merged.csv')

# 检查是否已存在 job_merged.csv
if not os.path.exists(merged_job_path):
    # 查找所有 group*.csv 文件
    job_files = glob.glob(os.path.join(job_folder, 'group*.csv'))

    # 合并所有文件
    job_dfs = [pd.read_csv(f) for f in job_files]
    job_merged = pd.concat(job_dfs, ignore_index=True)
    job_merged = job_merged[job_merged["JobTitle"].notnull()]
    job_merged = job_merged.fillna("")

    none_in_columns = job_merged.isnull().any()
    if none_in_columns.any():
        print("⚠️ 合并后的数据中存在 None 值:")
        for col, has_none in none_in_columns.items():
            if has_none:
                none_ratio = job_merged[col].isnull().mean() * 100  # 计算缺失值占比
                print(f" - 列 '{col}' 中存在 None 值，占比: {none_ratio:.2f}%")
    else:
        print("✅ 合并后的数据中不存在 None 值")

    # 保存为 job_merged.csv
    job_merged.to_csv(merged_job_path, index=False)
    print(f"✅ 合并 {len(job_files)} 个 job 文件为 job_merged.csv，包含 {len(job_merged)} 条记录。")
else:
    print(f"✅ 文件 {merged_job_path} 已存在，跳过合并。")


wiki_folder = os.path.join(data_base_path, 'wiki')
merged_wiki_path = os.path.join(data_target_path, 'wiki_merged.csv')

# 检查是否已存在 wiki_merged.csv
if not os.path.exists(merged_wiki_path):
    wiki_files = glob.glob(os.path.join(wiki_folder, '*.json'))

    wiki_data = []

    for path in wiki_files:
        with open(path, 'r', encoding='utf-8') as f:
            content = json.load(f)

            # 假设结构是 {"data": {"title": ..., "paragraphs": [...]}}
            if "data" in content:
                title = content["data"].get("title", "")
                paragraphs = content["data"].get("paragraphs", [])
                text = "\n\n".join(paragraphs) if isinstance(paragraphs, list) else str(paragraphs)
                wiki_data.append({
                    "title": title,
                    "text": text
                })

    # 转换为 DataFrame 并保存
    wiki_df = pd.DataFrame(wiki_data)
    none_in_columns = wiki_df.isnull().any()
    if none_in_columns.any():
        print("⚠️ 合并后的数据中存在 None 值:")
        for col, has_none in none_in_columns.items():
            if has_none:
                print(f" - 列 '{col}' 中存在 None 值")
    else:
        print("✅ 合并后的数据中不存在 None 值")

    wiki_df.to_csv(merged_wiki_path, index=False)
    print(f"✅ 合并 {len(wiki_files)} 个 wiki 文件为 wiki_merged.csv，包含 {len(wiki_df)} 条记录。")
else:
    print(f"✅ 文件 {merged_wiki_path} 已存在，跳过合并。")

# === 加载 job 和 wiki 合并文件 ===
job_df = pd.read_csv(merged_job_path)
wiki_df = pd.read_csv(merged_wiki_path)

# === 处理 job 数据：添加 title / text / label 字段 ===
job_df["title"] = job_df["JobTitle"]
job_df["text"] = job_df[[
    "detailText",
    "viewJobQualificationItem",
    "viewJobBenefitItem",
    "viewJobBodyJobFullDescriptionContent",
    "original URL"
]].fillna("").agg("\n\n".join, axis=1)

job_df = job_df[["title", "text"]]


# === 处理 wiki 数据：保持 title，用 text 字段替代 paragraph ===


# # 补齐 wiki 缺少的 job 字段
# for col in job_df.columns:
#     if col not in wiki_df.columns:
#         wiki_df[col] = ""

# # 补齐 job 缺少的 wiki 字段（理论上只有 label、title、text 已够）
# for col in wiki_df.columns:
#     if col not in job_df.columns:
#         job_df[col] = ""

# 合并两类数据
job_df = job_df[["title", "text"]].reset_index(drop=True)
wiki_df = wiki_df[["title", "text"]].reset_index(drop=True)


corpus_df = pd.concat([job_df, wiki_df], ignore_index=True)
corpus_df = corpus_df.reset_index().rename(columns={"index": "id"})

corpus_df = corpus_df.dropna(subset=["title", "text"]).reset_index(drop=True)


none_in_columns = corpus_df.isnull().any()
if none_in_columns.any():
    print("⚠️ 合并后的数据中存在 None 值:")
    for col, has_none in none_in_columns.items():
        if has_none:
            none_ratio = corpus_df[col].isnull().mean() * 100  # 计算缺失值占比
            print(f" - 列 '{col}' 中存在 None 值，占比: {none_ratio:.8f}%")

# 保存最终结果
corpus_path = os.path.join(data_target_path, 'corpus.csv')
corpus_df.to_csv(corpus_path, index=False)

print(f"✅ 已生成最终 corpus.csv，共 {len(corpus_df)} 条数据，保存至：{corpus_path}")
