# scripts/update_menu_all_chains.py

import pandas as pd
# ここはあなたの構成に合わせて import
from scrape_cocos import scrape_cocos        # ← これが list[dict] なら後で DataFrame 化します
from scrape_bikkuri_donkey_nutrition import scrape_bikkuri_donkey_nutrition
# from scrape_mcdonalds import scrape_mcdonalds など、チェーン別の関数も適宜

def main():
    frames = []

    # 例：マクドナルド（関数が list[dict] を返すなら DataFrame にして append）
    # mcd_list = scrape_mcdonalds()
    # frames.append(pd.DataFrame(mcd_list))

    # 例：ココス（あなたの scrape_cocos が list[dict] なら DataFrame 化）
    cocos_list = scrape_cocos()
    frames.append(pd.DataFrame(cocos_list))

    # びっくりドンキー（これは DataFrame を返す実装にしてある）
    bd_df = scrape_bikkuri_donkey_nutrition(headless=True)
    frames.append(bd_df)

    # すべて縦結合（列が合わなくても union される）
    df_all = pd.concat(frames, ignore_index=True)

    # 欲しい列の揃え（存在しない列は自動で NaN）
    want_cols = ["店舗名","チェーン名","chain", "カテゴリ","category", "メニュー名","name",
                 "カロリー","kcal", "たんぱく質","protein_g", "脂質","fat_g", "炭水化物","carb_g"]
    keep = [c for c in want_cols if c in df_all.columns]
    df_all = df_all[keep].copy()

    # 列名を最終スキーマに寄せる
    rename_map = {
        "chain": "店舗名",
        "チェーン名": "店舗名",
        "category": "カテゴリ",
        "name": "メニュー名",
        "kcal": "カロリー",
        "protein_g": "たんぱく質",
        "fat_g": "脂質",
        "carb_g": "炭水化物",
    }
    df_all.rename(columns=rename_map, inplace=True)

    # 数値は文字が混じっていても数値化（できないものは NaN）
    for col in ["カロリー","たんぱく質","脂質","炭水化物"]:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

    # 重複排除（チェーン＋メニュー名＋数値で重複行を消す例）
    subset_cols = [c for c in ["店舗名","メニュー名","カロリー","たんぱく質","脂質","炭水化物"] if c in df_all.columns]
    if subset_cols:
        df_all.drop_duplicates(subset=subset_cols, inplace=True)

    # CSV 出力
    df_all.to_csv("menu_data_all_chains.csv", index=False)
    print("menu_data_all_chains.csv を更新しました:", len(df_all), "行")

if __name__ == "__main__":
    main()
