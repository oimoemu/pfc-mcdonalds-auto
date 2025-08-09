import requests
from bs4 import BeautifulSoup
import time

def parse_cocos_pfc(soup):
    pfc = {}
    nutrient_ul = soup.find("ul", class_="nutrient_list")
    if not nutrient_ul:
        return None
    for li in nutrient_ul.find_all("li"):
        name = li.find("span").get_text(strip=True)
        value = li.get_text(strip=True).replace(name, "").strip()
        pfc[name] = value
    return {
        "カロリー": pfc.get("エネルギー", ""),
        "たんぱく質": pfc.get("たんぱく質", ""),
        "脂質": pfc.get("脂質", ""),
        "炭水化物": pfc.get("炭水化物", "")
    }

import re

# 全角→半角の簡易変換（数字と小数点だけ）
_Z2H = str.maketrans("０１２３４５６７８９．，", "0123456789..")

def num_only(s: str) -> str:
    """文字列から最初に出現する数値（整数/小数）だけを取り出して返す。なければ空文字。"""
    if not s:
        return ""
    t = str(s).translate(_Z2H)  # 全角→半角 & 全角ドット→半角
    m = re.search(r"\d+(?:\.\d+)?", t)
    return m.group(0) if m else ""

def scrape_cocos():
    CHAIN_NAME = "ココス"
    BASE_URL = "https://www.cocos-jpn.co.jp"
    LIST_URL = "https://www.cocos-jpn.co.jp/tabel/"
    menu_list = []

    res = requests.get(LIST_URL)
    soup = BeautifulSoup(res.content, "lxml")
    links = soup.find_all("a", href=True)
    menu_links = []
    for a in links:
        href = a['href']
        if href.startswith('/menu/') and href.endswith('.html'):
            menu_links.append(BASE_URL + href)

    for url in menu_links:
        try:
            page = requests.get(url)
            s = BeautifulSoup(page.content, "lxml")
            pfc = parse_cocos_pfc(s)
            if not pfc:
                continue

            menu_name = s.select_one("h2.menu_ttl")
            menu_name = menu_name.get_text(strip=True) if menu_name else ""

            # カテゴリはページ上部の <h1>
            category = s.select_one("h1")
            category = category.get_text(strip=True) if category else ""

            # ▼数値だけに統一
            kcal = num_only(pfc.get("カロリー", ""))           # 例 "350"
            protein = num_only(pfc.get("たんぱく質", ""))      # 例 "19.8"
            fat = num_only(pfc.get("脂質", ""))               # 例 "22.5"
            carb = num_only(pfc.get("炭水化物", ""))          # 例 "14.7"

            menu_list.append({
                "チェーン名": CHAIN_NAME,
                "カテゴリ": category,
                "メニュー名": menu_name,
                "カロリー": kcal,
                "たんぱく質": protein,
                "脂質": fat,
                "炭水化物": carb,
            })
            time.sleep(0.5)

        except Exception as e:
            print(f"エラー: {url} {e}")

    print(f"ココスメニュー抽出件数: {len(menu_list)}")
    return menu_list
