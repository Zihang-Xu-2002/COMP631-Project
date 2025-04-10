#!/usr/bin/python
# -*- coding: utf-8 -*-

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# LinkedIn Jobs URL
URL = "https://www.simplyhired.com/sitemap/viewjob/sitemap_index.xml"

# 请求头，模拟真实浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.linkedin.com/",
    "Connection": "keep-alive",
}

async def crawl_page(context) -> None:
    """
    打开 LinkedIn Jobs 页面，等待页面加载完成及额外等待 10 秒，
    然后获取 HTML 内容并保存到文件。
    """
    print(f"[INFO] 开始爬取: {URL}")
    page = await context.new_page()
    
    # 导航到目标页面，并等待网络空闲状态，确保 JS 动态加载完成
    await page.goto(URL, wait_until='networkidle')
    # 等待 10 秒，确保页面完全加载
    await asyncio.sleep(2-5)
    
    content = await page.content()
    filename = "linkedin_jobs.html"
    Path(filename).write_text(content, encoding="utf-8")
    print(f"[INFO] 页面已保存到文件：{filename}")
    
    await page.close()

async def main():
    async with async_playwright() as p:
        # 启动无头浏览器（可设置 headless=False 观察浏览器行为）
        browser = await p.firefox.launch(headless=True)
        # 创建新的浏览器上下文，并设置自定义请求头和 User-Agent
        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"],
            extra_http_headers={
                "Accept": HEADERS["Accept"],
                "Accept-Language": HEADERS["Accept-Language"],
                "Referer": HEADERS["Referer"],
                "Connection": HEADERS["Connection"],
            }
        )
        
        # 爬取 LinkedIn Jobs 页面
        await crawl_page(context)
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())