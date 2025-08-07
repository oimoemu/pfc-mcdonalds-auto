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

            # ★商品名はh2.menu_ttlで取得！
            menu_name = s.select_one("h2.menu_ttl")
            menu_name = menu_name.get_text(strip=True) if menu_name else ""
            # カテゴリはp.category spanで（なければ空欄）
            category = s.select_one("p.category span")
            category = category.get_text(strip=True) if category else ""

            menu_list.append({
                "チェーン名": CHAIN_NAME,
                "カテゴリ": category,
                "メニュー名": menu_name,
                "カロリー": pfc["カロリー"],
                "たんぱく質": pfc["たんぱく質"],
                "脂質": pfc["脂質"],
                "炭水化物": pfc["炭水化物"]
            })
            time.sleep(0.5)
        except Exception as e:
            print(f"エラー: {url} {e}")

    print(f"ココスメニュー抽出件数: {len(menu_list)}")
    return menu_list
