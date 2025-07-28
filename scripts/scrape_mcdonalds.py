from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import pandas as pd
from bs4 import BeautifulSoup
import time

URL = "https://www.mcdonalds.co.jp/quality/basic_information/menu_information/"
CHAIN_NAME = "マクドナルド"

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
driver.get(URL)
time.sleep(3)  # 初期ロード待ち

# すべてのタブのボタンを取得
tab_buttons = driver.find_elements('css selector', 'li.p-menuTab__item > a')

print(f"取得したタブ数: {len(tab_buttons)}")

menu_list = []

for i, tab in enumerate(tab_buttons):
    # タブをクリック
    driver.execute_script("arguments[0].click();", tab)
    time.sleep(2)  # 切り替え待ち

    html = driver.page_source
    soup = BeautifulSoup(html, "lxml")
    tables = soup.select("div.p-menuTab__panel.is-show table")

    print(f"[{i+1}] 取得テーブル数: {len(tables)}")

    for table in tables:
        category_tag = table.find_previous("h3")
        category = category_tag.get_text(strip=True) if category_tag else "未分類"

        rows = table.select("tr")
        for row in rows[1:]:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) >= 5:
                menu_list.append({
                    "チェーン名": CHAIN_NAME,
                    "カテゴリ": category,
                    "メニュー名": cols[0],
                    "カロリー": cols[1].replace("kcal", ""),
                    "たんぱく質": cols[2].replace("g", ""),
                    "脂質": cols[3].replace("g", ""),
                    "炭水化物": cols[4].replace("g", ""),
                })

print(f"取得メニュー数: {len(menu_list)}")

if len(menu_list) > 0:
    df = pd.DataFrame(menu_list)
    df.to_csv("menu_data_mcdonalds.csv", index=False)
    print("メニュー取得＆CSV出力完了！")
else:
    print("データが取得できませんでした。")

driver.quit()
