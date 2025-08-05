import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_cocos():
    CHAIN_NAME = "ココス"
    BASE_URL = "https://www.cocos-jpn.co.jp"
    LIST_URL = "https://www.cocos-jpn.co.jp/tabel/"
    menu_list = []

    # 1. メニュー一覧ページから全商品URLを取得
    res = requests.get(LIST_URL)
    soup = BeautifulSoup(res.content, "lxml")
    # 商品ごとの<a>タグを全て取得（構造に応じてクラス名や属性を調整してください）
    menu_links = soup.select('a.c-tabelList__item')  # ← 例。正しいセレクタは要調査

    for link in menu_links:
        menu_url = BASE_URL + link.get("href")
        menu_name = link.get_text(strip=True)  # 例。必要なら構造によって取得方法修正
        print(menu_name, menu_url)
        # 2. 各商品ページでPFCを取得
        r = requests.get(menu_url)
        s = BeautifulSoup(r.content, "lxml")
        # ↓ページ内のカロリー等の値を正しいセレクタで抜き出す
        kcal = s.select_one('.c-nutrition__energy').get_text(strip=True)
        p = s.select_one('.c-nutrition__protein').get_text(strip=True)
        f = s.select_one('.c-nutrition__fat').get_text(strip=True)
        c = s.select_one('.c-nutrition__carbohydrate').get_text(strip=True)

        menu_list.append({
            "チェーン名": CHAIN_NAME,
            "カテゴリ": "",  # カテゴリ情報を別途取得できれば追加
            "メニュー名": menu_name,
            "カロリー": kcal,
            "たんぱく質": p,
            "脂質": f,
            "炭水化物": c
        })
        time.sleep(0.5)  # サーバー負荷対策（マナーとして0.5秒スリープ）

    return menu_list
