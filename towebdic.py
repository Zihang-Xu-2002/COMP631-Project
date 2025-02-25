#!/usr/bin/python
# -*- coding: utf-8 -*-

import asyncio
import csv
import os
import random
from pathlib import Path
from playwright.async_api import async_playwright

CSV_FILE = "urls.csv"      # CSV 文件路径，根据实际情况修改
OUTPUT_DIR = "web"         # 输出目录

# 请求头，模拟真实浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.linkedin.com/",
    "Connection": "keep-alive",
}

async def crawl_url(context, id, url):
    """
    爬取指定 URL 并保存 HTML 内容，同时输出服务器状态码。
    """
    page = await context.new_page()
    print(f"[INFO] 正在爬取 ID {id}：{url}")
    response = await page.goto(url, wait_until="networkidle")
    
    # 获取状态码
    status = response.status if response is not None else "No Response"
    print(f"[INFO] ID {id} 返回状态：{status}")
    
    # 获取页面内容
    content = await page.content()
    
    # 拼接保存文件路径，文件命名为 “{ID}web.html”
    file_path = os.path.join(OUTPUT_DIR, f"{id}web.html")
    Path(file_path).write_text(content, encoding="utf-8")
    
    await page.close()

async def main():
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 读取 CSV 文件
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                rows.append(row)
    
    async with async_playwright() as p:
        # 启动无头浏览器（可以设置 headless=False 观察浏览器行为）
        browser = await p.firefox.launch(headless=True)
        # 创建浏览器上下文，并设置请求头
        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"],
            extra_http_headers={
                "Accept": HEADERS["Accept"],
                "Accept-Language": HEADERS["Accept-Language"],
                "Referer": HEADERS["Referer"],
                "Connection": HEADERS["Connection"],
            }
        )
        
        # 顺序爬取 CSV 中的每个 URL
        for row in rows:
            id, url = row[0], row[1]
            await crawl_url(context, id, url)
            # 每次爬取后间隔随机2到5秒
            await asyncio.sleep(random.uniform(2, 5))
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())