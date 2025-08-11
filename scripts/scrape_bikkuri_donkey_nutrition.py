import time
import re
import os
import io
import sys
import json
import pandas as pd
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import pdfplumber
import requests


BASE = "https://www.bikkuri-donkey.com/producing/"
BTN_TEXT = "栄養成分情報を見る"  # クリック対象

def make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,2000")
    return webdriver.Chrome(options=opts)

def click_nutrition_button(driver):
    # ページ到達
    driver.get(BASE)
    # ボタンの出方が複数パターンあり得るので順に探す
    candidates = [
        (By.LINK_TEXT, BTN_TEXT),
        (By.PARTIAL_LINK_TEXT, "栄養成分"),
        (By.XPATH, f"//*[contains(normalize-space(.), '{BTN_TEXT}')]"),
        (By.CSS_SELECTOR, "a, button")
    ]
    for by, sel in candidates:
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((by, sel)))
            els = driver.find_elements(by, sel)
            for el in els:
                try:
                    txt = el.text.strip()
                    if BTN_TEXT in txt or ("栄養成分" in txt and "見る" in txt):
                        driver.execute_script("arguments[0].click();", el)
                        return True
                except Exception:
                    continue
        except Exception:
            pass
    return False

def extract_tables_from_html(driver):
    # 新しくモーダル/別ページ/タブ遷移する可能性
    time.sleep(2)
    # タブが増えたら最後に切り替え
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(1)

    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    # 1) HTMLテーブルを素直に回収
    tables = soup.find_all("table")
    dfs = []
    for t in tables:
        # ヘッダ行推定
        df = pd.read_html(str(t), flavor="lxml")[0]
        # 空テーブル・1列だけ等をスキップ
        if df.shape[1] >= 2 and df.shape[0] >= 1:
            dfs.append(df)

    if dfs:
        # 列名をできる範囲で正規化（日本語そのままでOK。重複は番号付与）
        normalized = []
        for df in dfs:
            df.columns = [str(c).strip() for c in df.columns]
            normalized.append(df)
        # 横並びの複数表がある場合は縦に積む（列合わせは外部で調整）
        big = pd.concat(normalized, axis=0, ignore_index=True)
        return big

    # 2) PDFリンクしか無い場合はリンク収集して呼び側でPDF処理
    pdf_links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if ".pdf" in href.lower():
            pdf_links.append(urljoin(driver.current_url, href))

    return None if not pdf_links else pdf_links

def tables_from_pdfs(links):
    rows = []
    for url in links:
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                for page in pdf.pages:
                    try:
                        tbls = page.extract_tables()
                        for tbl in tbls or []:
                            # 行ごとにセルのNoneを空文字に
                            clean = [[(c or "").strip() if isinstance(c, str) else ("" if c is None else str(c)) for c in row] for row in tbl]
                            # 1行目をヘッダとみなす（崩れていたら後で整える）
                            if len(clean) >= 2:
                                header = [h if h else f"col{i}" for i, h in enumerate(clean[0])]
                                for data in clean[1:]:
                                    # 列数差を吸収
                                    if len(data) < len(header):
                                        data += [""] * (len(header) - len(data))
                                    elif len(data) > len(header):
                                        data = data[:len(header)]
                                    rows.append(dict(zip(header, data)))
                    except Exception:
                        continue
        except Exception:
            continue
    if not rows:
        return None
    df = pd.DataFrame(rows)

    # よくある列名のゆらぎを軽く正規化（あれば）
    rename_map = {
        "エネルギー": "エネルギー(kcal)",
        "熱量": "エネルギー(kcal)",
        "たんぱく質": "たんぱく質(g)",
        "脂質": "脂質(g)",
        "炭水化物": "炭水化物(g)",
        "食塩相当量": "食塩相当量(g)",
    }
    for k, v in list(rename_map.items()):
        if k in df.columns and v not in df.columns:
            df.rename(columns={k: v}, inplace=True)

    return df

def main():
    driver = make_driver()
    try:
        clicked = click_nutrition_button(driver)
        if not clicked:
            print("⚠️ ボタンが見つからずクリックできませんでした。サイトの構造が変わったかも。")
            print("現在URL:", driver.current_url)
            sys.exit(1)

        result = extract_tables_from_html(driver)

        if isinstance(result, pd.DataFrame):
            out = "bikkuri_donkey_nutrition.csv"
            result.to_csv(out, index=False)
            print(f"✅ HTMLテーブルから抽出しました -> {out}")
        elif isinstance(result, list):
            print(f"ℹ️ PDFリンクを検出: {len(result)}件。PDFを解析します…")
            df = tables_from_pdfs(result)
            if df is None or df.empty:
                print("⚠️ PDFからテーブルを抽出できませんでした。")
                sys.exit(2)
            out = "bikkuri_donkey_nutrition_from_pdfs.csv"
            df.to_csv(out, index=False)
            print(f"✅ PDFから抽出しました -> {out}")
        else:
            print("⚠️ テーブルもPDFも見つかりませんでした。画面キャプチャして教えてください。")
            sys.exit(3)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
