from scrape_cocos import scrape_cocos# ← ココス用（別ファイルで定義してある場合のみ必要）
from scrape_bikkuri_donkey_nutrition import scrape_bikkuri_donkey_nutrition
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_mcdonalds():
    URL = "https://www.mcdonalds.co.jp/quality/allergy_Nutrition/nutrient/"
    CHAIN_NAME = "マクドナルド"

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--lang=ja-JP')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.get(URL)
    time.sleep(8)
    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "lxml")

    menu_list = []
    for table in soup.find_all("table", class_="allergy-info__table"):
        for row in table.select("tbody > tr"):
            tds = row.find_all("td")
            if len(tds) < 5:
                continue
            menu_name = tds[0].get_text(strip=True)
            category = row.get("data-kind", "未分類")
            menu_list.append({
                "チェーン名": CHAIN_NAME,
                "カテゴリ": category,
                "メニュー名": menu_name,
                "カロリー": tds[1].get_text(strip=True),
                "たんぱく質": tds[2].get_text(strip=True),
                "脂質": tds[3].get_text(strip=True),
                "炭水化物": tds[4].get_text(strip=True)
            })
    return menu_list

# --- ここからがmain実行部分 ---
if __name__ == "__main__":
    all_menus = []
    all_menus += scrape_mcdonalds()   # マクドナルドのデータ
    all_menus += scrape_cocos()       # ココスのデータ（importできていれば）
    all_menus += scrape_bikkuri_donkey_nutrition()

    df = pd.DataFrame(all_menus)
    df = df.rename(columns={
        "チェーン名": "店舗名",
        "たんぱく質": "たんぱく質 (g)",
        "脂質": "脂質 (g)",
        "炭水化物": "炭水化物 (g)"
    })
    df = df[["店舗名", "カテゴリ", "メニュー名", "カロリー", "たんぱく質 (g)", "脂質 (g)", "炭水化物 (g)"]]
    df = df.drop_duplicates()
    df.to_csv("menu_data_all_chains.csv", index=False)
    print("menu_data_all_chains.csv をマクドナルド＋ココス＋びっくりドンキーの最新PFC情報で更新しました！（重複も自動で除去）")
