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

# --- ここだけ差分適用でOK ---

def make_driver(headless: bool = True):
    opts = Options()
    if headless:
        # 新旧 headless 両対応
        for flag in ["--headless=new", "--headless"]:
            opts.add_argument(flag)
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1280,2000")
    # UA を固定して分岐を避ける
    opts.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome Safari")
    return webdriver.Chrome(options=opts)

def click_nutrition_button(driver) -> bool:
    driver.get(BASE)
    candidates = [
        (By.LINK_TEXT, BTN_TEXT),
        (By.PARTIAL_LINK_TEXT, "栄養成分"),
        (By.XPATH, f"//*[contains(normalize-space(.), '{BTN_TEXT}')]"),
        (By.CSS_SELECTOR, "a, button"),
    ]
    cur_handles = set(driver.window_handles)
    for by, sel in candidates:
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((by, sel)))
            for el in driver.find_elements(by, sel):
                txt = (el.text or "").strip()
                if BTN_TEXT in txt or ("栄養成分" in txt and "見る" in txt):
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    WebDriverWait(driver, 3).until(EC.element_to_be_clickable(el))
                    el.click()
                    # クリック後の「何かが起きる」まで待つ
                    def any_ready(d):
                        # 新タブ
                        if len(d.window_handles) > len(cur_handles): 
                            return True
                        # テーブル or PDF リンク
                        html = d.page_source
                        return ("<table" in html.lower()) or (".pdf" in html.lower())
                    WebDriverWait(driver, 10).until(any_ready)
                    return True
        except Exception:
            continue
    return False

def extract_tables_from_html(driver):
    # タブ遷移対応
    if len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])
    time.sleep(1)

    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")

    # まず HTML テーブル
    dfs = []
    for t in soup.find_all("table"):
        try:
            df = pd.read_html(str(t), flavor="lxml")[0]
            if df.shape[0] >= 1 and df.shape[1] >= 2:
                df.columns = [str(c).strip() for c in df.columns]
                dfs.append(df)
        except Exception:
            continue
    if dfs:
        return pd.concat(dfs, axis=0, ignore_index=True)

    # 次に PDF リンク
    pdf_links = []
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if ".pdf" in href.lower():
            pdf_links.append(urljoin(driver.current_url, href))
    return None if not pdf_links else pdf_links

def _normalize_macros(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = df_raw.copy()

    # 1列目を商品名に想定
    name_col = df.columns[0]
    df.rename(columns={name_col: "name"}, inplace=True)

    # 列名ゆらぎ
    ren = {
        "エネルギー": "kcal",
        "熱量": "kcal",
        "エネルギー(kcal)": "kcal",
        "たんぱく質": "protein_g",
        "たんぱく質(g)": "protein_g",
        "脂質": "fat_g",
        "脂質(g)": "fat_g",
        "炭水化物": "carb_g",
        "炭水化物(g)": "carb_g",
    }
    for s, t in ren.items():
        if s in df.columns and t not in df.columns:
            df.rename(columns={s: t}, inplace=True)

    # 数値化（「g」「kcal」混入や全角対応）
    def to_num(s):
        if pd.isna(s): 
            return pd.NA
        x = str(s)
        x = re.sub(r"[^\d\.\-]", "", x)
        try:
            return float(x) if x else pd.NA
        except Exception:
            return pd.NA

    for c in ["kcal", "protein_g", "fat_g", "carb_g"]:
        if c in df.columns:
            df[c] = df[c].map(to_num)

    out = df[["name"] + [c for c in ["kcal","protein_g","fat_g","carb_g"] if c in df.columns]].copy()
    out.insert(0, "category", "栄養成分")
    out.insert(0, "chain", "びっくりドンキー")
    return out

def tables_from_pdfs(links) -> pd.DataFrame | None:
    rows = []
    for url in links:
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                for page in pdf.pages:
                    for tbl in (page.extract_tables() or []):
                        clean = [[(c or "").strip() if isinstance(c, str) else ("" if c is None else str(c)) for c in row] for row in tbl]
                        if len(clean) >= 2:
                            header = [h if h else f"col{i}" for i, h in enumerate(clean[0])]
                            for data in clean[1:]:
                                if len(data) < len(header):
                                    data += [""] * (len(header) - len(data))
                                elif len(data) > len(header):
                                    data = data[:len(header)]
                                rows.append(dict(zip(header, data)))
        except Exception:
            continue
    if not rows:
        return None
    df = pd.DataFrame(rows)
    # 軽くリネーム
    rename_map = {
        "エネルギー": "エネルギー(kcal)",
        "熱量": "エネルギー(kcal)",
        "たんぱく質": "たんぱく質(g)",
        "脂質": "脂質(g)",
        "炭水化物": "炭水化物(g)",
    }
    for k, v in list(rename_map.items()):
        if k in df.columns and v not in df.columns:
            df.rename(columns={k: v}, inplace=True)
    return df

# ここからが update_menu_all_chains.py から呼ばれる関数本体
def scrape_bikkuri_donkey_nutrition(headless: bool = True) -> pd.DataFrame:
    driver = make_driver(headless=headless)
    try:
        if not click_nutrition_button(driver):
            raise RuntimeError("栄養成分ボタンが見つからない/遷移しない")

        result = extract_tables_from_html(driver)
        if isinstance(result, pd.DataFrame):
            return _normalize_macros(result)
        elif isinstance(result, list):
            pdf_df = tables_from_pdfs(result)
            if pdf_df is None or pdf_df.empty:
                raise RuntimeError("PDFから抽出できず")
            return _normalize_macros(pdf_df)
        else:
            raise RuntimeError("テーブルもPDFも見つからず")
    finally:
        driver.quit()

if __name__ == "__main__":
    df = scrape_bikkuri_donkey_nutrition(headless=True)
    out = "bikkuri_donkey_nutrition.csv"
    df.to_csv(out, index=False)
    print(f"✅ 抽出 -> {out} / {len(df)} 行")
