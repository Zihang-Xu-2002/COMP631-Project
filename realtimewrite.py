#!/usr/bin/python
# -*- coding: utf-8 -*-

import asyncio
import csv
import os
import random
from pathlib import Path
from playwright.async_api import async_playwright
import glob

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
    爬取指定 URL 并提取指定信息，同时输出服务器状态码。
    提取的字段：
      - JobTitle：data-testid="viewJobTitle" 的文本内容
      - detailText：所有 data-testid="detailText" 元素的文本，用 "|" 连接
      - viewJobQualificationItem：所有 data-testid="viewJobQualificationItem" 元素的文本，用 "|" 连接
      - viewJobBenefitItem：所有 data-testid="viewJobBenefitItem" 元素的文本，用 "|" 连接
      - viewJobBodyJobFullDescriptionContent：data-testid="viewJobBodyJobFullDescriptionContent" 部分文本，移除 "::marker"
    """
    page = await context.new_page()
    print(f"[INFO] 正在爬取 ID {id}：{url}")
    try:
        response = await page.goto(url, wait_until="networkidle")
    except Exception as e:
        print(f"[ERROR] ID {id} 请求异常：{e}")
        await page.close()
        return (id, "", "", "", "", "", url)

    if response:
        status = response.status
        print(f"[INFO] ID {id} 返回状态：{status}")
        if status == 403:
            print(f"[ERROR] ID {id} 返回403，程序中断")
            await page.close()
            # 这里抛出异常以便在上层中断整个脚本
            raise Exception("403 Forbidden")
    else:
        print(f"[ERROR] ID {id} 无响应")
        await page.close()
        return (id, "", "", "", "", "", url)

    try:
        # 提取 JobTitle
        job_title = ""
        job_title_el = await page.query_selector('[data-testid="viewJobTitle"]')
        if job_title_el:
            job_title = (await job_title_el.inner_text()).strip()
            job_title = 'Job title: ' + job_title

        # 提取 detailText，多元素用 "|" 连接
        detail_text_elements = await page.query_selector_all('[data-testid="detailText"]')
        detail_text_list = [ (await el.inner_text()).strip() for el in detail_text_elements ]
        detail_text_joined = 'Details: ' + "|".join(detail_text_list)

        # 提取 viewJobQualificationItem，多元素用 "|" 连接
        qualification_elements = await page.query_selector_all('[data-testid="viewJobQualificationItem"]')
        qualification_list = [ (await el.inner_text()).strip() for el in qualification_elements ]
        qualification_joined = 'Qualification: ' + "|".join(qualification_list)

        # 提取 viewJobBenefitItem，多元素用 "|" 连接
        benefit_elements = await page.query_selector_all('[data-testid="viewJobBenefitItem"]')
        benefit_list = [ (await el.inner_text()).strip() for el in benefit_elements ]
        benefit_joined = 'Benefit: ' + "|".join(benefit_list)

        # 提取 viewJobBodyJobFullDescriptionContent，移除 "::marker"
        body_text = ""
        body_el = await page.query_selector('[data-testid="viewJobBodyJobFullDescriptionContent"]')
        if body_el:
            body_text = (await body_el.inner_text()).strip().replace("::marker", "")

    except Exception as e:
        print(f"[ERROR] ID {id} 数据提取异常：{e}")
        await page.close()
        return (id, "", "", "", "", "", url)

    await page.close()
    return (id, job_title, detail_text_joined, qualification_joined, benefit_joined, body_text, url)


async def process_csv_file(csv_file, context):
    """
    读取单个 CSV 文件并调用 crawl_url 逐行爬取，
    实时写入结果到对应的 CSV 文件中。
    """
    # 读取 CSV 文件中的 URL 列表
    rows = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                rows.append(row)

    # 创建输出目录，并准备输出 CSV 文件（实时写入）
    os.makedirs("infor", exist_ok=True)
    output_csv = os.path.join("infor", f"{Path(csv_file).stem} infor.csv")
    with open(output_csv, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(["URL ID", "JobTitle", "detailText", "viewJobQualificationItem", "viewJobBenefitItem",
                         "viewJobBodyJobFullDescriptionContent", "original URL"])

        for row in rows:
            id, url = row[0], row[1]
            try:
                data = await crawl_url(context, id, url)
                writer.writerow(data)
                f_out.flush()  # 实时刷新写入，防止数据丢失
            except Exception as e:
                # 如果是403，直接抛出异常，终止整个脚本
                if "403" in str(e):
                    print(f"[ERROR] 遇到403错误，程序中断：{e}")
                    raise e
                else:
                    print(f"[ERROR] ID {id} 处理异常：{e}")
                    writer.writerow((id, "", "", "", "", "", url))
                    f_out.flush()

            # 每次爬取后间隔随机2到5秒
            await asyncio.sleep(random.uniform(2, 4))

    print(f"[INFO] 文件 {csv_file} 处理完毕，结果已保存到: {output_csv}")


def get_file_range(csv_file):
    """
    辅助函数：从文件名提取数字范围，用于按数值进行排序。
    文件名格式类似: group1__500.csv
    """
    stem = Path(csv_file).stem
    stem = stem.replace("group", "")
    parts = stem.split("__")
    if len(parts) == 2:
        start = int(parts[0])
        end = int(parts[1])
        return (start, end)
    else:
        return (999999, 999999)


async def main():
    # 找到当前目录下所有符合 group*__*.csv 的文件
    csv_files = glob.glob("group*__*.csv")
    csv_files.sort(key=lambda x: get_file_range(x))

    if not csv_files:
        print("No CSV files found matching the pattern 'group*__*.csv'.")
        return

    async with async_playwright() as p:
        # 启动无头浏览器
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

        # 依次处理每个 CSV 文件
        for csv_file in csv_files:
            print(f"[INFO] 开始处理文件: {csv_file}")
            try:
                await process_csv_file(csv_file, context)
            except Exception as e:
                if "403" in str(e):
                    print(f"[ERROR] 遇到403错误，程序中断：{e}")
                    await context.close()
                    await browser.close()
                    return
                else:
                    print(f"[ERROR] 文件 {csv_file} 处理异常：{e}")
                    continue

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())