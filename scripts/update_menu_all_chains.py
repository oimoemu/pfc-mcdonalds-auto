from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
import time
import tempfile  # ← 追加！

URL = "https://www.mcdonalds.co.jp/quality/allergy_Nutrition/nutrient/"
CHAIN_NAME = "マクドナルド"

options = Options()
# options.add_argument('--headless')  # 必要に応じて有効化（CI環境ではON推奨）
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--lang=ja-JP')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')

# ↓ 一時的なuser-data-dirで競合を完全防止
user_data_dir = tempfile.mkdtemp()
options.add_argument(f'--user-data-dir={user_data_dir}')

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
driver.get(URL)
time.sleep(8)  # ネットワーク速度次第で調整

html = driver.page_source
driver.quit()

soup = BeautifulSoup(html, "lxml")

menu_list = []

# 本命テーブルだけ抽出
for table in soup.find_all("table", class_="allergy-info__table"):
    # tbody内のデータ行のみ抽出
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

df = pd.DataFrame(menu_list)
df.to_csv("menu_data_all_chains.csv", index=False)
print("menu_data_all_chains.csv をマクドナルドの最新PFC情報で更新しました！")
