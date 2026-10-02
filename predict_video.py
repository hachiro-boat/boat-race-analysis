import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- 1. Google スプレッドシート接続設定 ---
# ご自身のスプレッドシートURL（/d/ と /edit の間の文字列）に置き換えてください
SPREADSHEET_ID = "1uPIw3EBMDd3HYnaAuoAomCCC6eVui85P6bpxbDnaBCc"

def get_gspread_client():
    """Streamlit Secrets から Google サービスアカウント認証情報を取得"""
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Secretsの辞書をコピー
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    if "private_key" in creds_dict:
        pk = creds_dict["private_key"]
        # エスケープ文字 \n の置換
        pk = pk.replace("\\n", "\n")
        
        # PEMのヘッダー/フッター部分と鍵本体を整理してパディングズレを防止
        if "-----BEGIN PRIVATE KEY-----" in pk:
            lines = [line.strip() for line in pk.strip().split("\n") if line.strip()]
            header = "-----BEGIN PRIVATE KEY-----"
            footer = "-----END PRIVATE KEY-----"
            body_lines = [l for l in lines if not l.startswith("-----")]
            body = "".join(body_lines)
            
            # Base64パディング(=)の補正
            missing_padding = len(body) % 4
            if missing_padding:
                body += "=" * (4 - missing_padding)
                
            # 64文字ごとに改行して正しいPEM形式を再構築
            chunked_body = "\n".join([body[i:i+64] for i in range(0, len(body), 64)])
            creds_dict["private_key"] = f"{header}\n{chunked_body}\n{footer}\n"

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPE
    )
    return gspread.authorize(creds)

def load_data_from_sheets():
    """スプレッドシートからデータを取得"""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        data = sheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"スプレッドシートからのデータ取得に失敗しました: {e}")
        return []

def append_data_to_sheets(racer_name, gap_pattern, race_info_str):
    """スプレッドシートに1行データを追加"""
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        sheet.append_row([racer_name, gap_pattern, race_info_str])
        return True
    except Exception as e:
        st.error(f"スプレッドシートへの保存に失敗しました: {e}")
        return False

# --- 管理者用パスワード設定 ---
ADMIN_PASSWORD = "1234"  # お好きなパスワードに変更してください

# 全国24場リスト
BOAT_RACE_STADIUMS = [
    "桐生", "戸田", "江戸川", "平和島", "多摩川", "浜名湖",
    "蒲郡", "常滑", "津", "三国", "びわこ", "住之江",
    "尼崎", "鳴門", "丸亀", "児島", "宮島", "徳山",
    "下関", "若松", "芦屋", "福岡", "唐津", "大村"
]

# 進入パターンの固定リスト
GAP_PATTERNS = [
    "最内",
    "4号艇と2号艇の間",
    "2号艇と1号艇の間",
    "1号艇と3号艇の間",
    "最外"
]

st.set_page_config(page_title="ボートレース 進入・間隙データ記憶アプリ", layout="centered")

st.title("🚤 5号艇 進入・間隙データ記録・分析アプリ")

# データの読み込み（スプレッドシートから最新データを取得）
records = load_data_from_sheets()

# --- レース情報文字列から「開催場」と「着順」を分解取得する補助関数 ---
def parse_record(rec):
    race_info = rec.get("レース情報", "")
    parts = [p.strip() for p in str(race_info).split("/")]
    stadium = parts[1] if len(parts) >= 2 else "不明"
    rank = parts[2] if len(parts) >= 3 else "不明"
    return {
        "選手名": rec.get("選手名", ""),
        "進入パターン": rec.get("進入パターン", ""),
        "開催場": stadium,
        "着順": rank,
        "レース情報": race_info
    }

# データフレームの準備
all_parsed = [parse_record(r) for r in records]
df_all = pd.DataFrame(all_parsed) if all_parsed else pd.DataFrame()

# --- タブ分け（検索・集計） ---
tab1, tab2 = st.tabs(["🔍 選手名で検索", "🏟️ ボートレース場分析"])

# ---------------------------------------------------------
# TAB 1: 選手名検索（パーセンテージ対応版）
# ---------------------------------------------------------
with tab1:
    st.header("🔍 選手名でパターン・件数を検索")
    search_query = st.text_input("検索したい選手名を入力", placeholder="例: 毒島")

    if search_query.strip() and not df_all.empty:
        filtered_df = df_all[df_all["選手名"].astype(str).str.lower().str.contains(search_query.strip().lower(), na=False)]
        
        if not filtered_df.empty:
            racer_total = len(filtered_df)
            st.subheader(f"📊 「{search_query}」選手の検索結果 (全 {racer_total} 件)")
            
            # --- 1. 進入パターンのパーセンテージ集計 ---
            st.markdown("### 1. 進入パターンの選択割合（%）")
            pattern_counts = filtered_df["進入パターン"].value_counts()
            pattern_data = []
            for pat in GAP_PATTERNS:
                cnt = pattern_counts.get(pat, 0)
                pct = (cnt / racer_total * 100) if racer_total > 0 else 0
                pattern_data.append({
                    "進入パターン": pat,
                    "件数": f"{cnt} 件",
                    "選択割合 (%)": f"{pct:.1f} %"
                })
            st.table(pd.DataFrame(pattern_data))
            
            # --- 2. 各進入パターンごとの着順内訳（%） ---
            st.markdown("### 2. 進入パターンごとの着順割合（%）")
            for pat in GAP_PATTERNS:
                pat_df = filtered_df[filtered_df["進入パターン"] == pat]
                pat_total = len(pat_df)
                
                with st.expander(f"📍 進入パターン: 【{pat}】 (該当データ: {pat_total} 件)"):
                    if pat_total > 0:
                        rank_counts = pat_df["着順"].value_counts()
                        rank_data = []
                        all_ranks = ["1着", "2着", "3着", "4着", "5着", "6着", "転覆・落水・F等"]
                        for r in all_ranks:
                            r_cnt = rank_counts.get(r, 0)
                            r_pct = (r_cnt / pat_total * 100)
                            rank_data.append({
                                "着順": r,
                                "件数": f"{r_cnt} 件",
                                "着順割合 (%)": f"{r_pct:.1f} %"
                            })
                        st.table(pd.DataFrame(rank_data))
                    else:
                        st.caption("※この進入パターンの記録はまだありません。")

            with st.expander("詳細な記録一覧を見る"):
                st.dataframe(filtered_df[["選手名", "進入パターン", "レース情報"]], use_container_width=True)
        else:
            st.warning(f"「{search_query}」選手の記録データは見つかりませんでした。")
    elif not df_all.empty:
        st.info(f"💡 現在、合計 **{len(df_all)} 件** のデータが記録・保存されています。")
        with st.expander("全記録一覧を表示"):
            st.dataframe(df_all[["選手名", "進入パターン", "レース情報"]], use_container_width=True)
    else:
        st.info("まだ記録データがありません。")

# ---------------------------------------------------------
# TAB 2: ボートレース場別分析
# ---------------------------------------------------------
with tab2:
    st.header("🏟️ ボートレース場別の進入・着順割合分析")
    
    selected_stadium = st.selectbox("分析したいレース場を選択してください", BOAT_RACE_STADIUMS)
    
    if not df_all.empty:
        stadium_df = df_all[df_all["開催場"] == selected_stadium]
        
        if not stadium_df.empty:
            total_count = len(stadium_df)
            st.subheader(f"📊 【{selected_stadium}】の集計結果 (全 {total_count} 件)")
            
            # --- 1. 進入パターンのパーセンテージ集計 ---
            st.markdown("### 1. 進入パターンの出現割合（%）")
            pattern_counts = stadium_df["進入パターン"].value_counts()
            pattern_data = []
            for pat in GAP_PATTERNS:
                cnt = pattern_counts.get(pat, 0)
                pct = (cnt / total_count * 100) if total_count > 0 else 0
                pattern_data.append({
                    "進入パターン": pat,
                    "件数": f"{cnt} 件",
                    "割合 (%)": f"{pct:.1f} %"
                })
            st.table(pd.DataFrame(pattern_data))
            
            # --- 2. 各進入パターンごとの着順内訳（%） ---
            st.markdown("### 2. 進入パターンごとの着順割合（%）")
            for pat in GAP_PATTERNS:
                pat_df = stadium_df[stadium_df["進入パターン"] == pat]
                pat_total = len(pat_df)
                
                with st.expander(f"📍 進入パターン: 【{pat}】 (該当データ: {pat_total} 件)"):
                    if pat_total > 0:
                        rank_counts = pat_df["着順"].value_counts()
                        rank_data = []
                        all_ranks = ["1着", "2着", "3着", "4着", "5着", "6着", "転覆・落水・F等"]
                        for r in all_ranks:
                            r_cnt = rank_counts.get(r, 0)
                            r_pct = (r_cnt / pat_total * 100)
                            rank_data.append({
                                "着順": r,
                                "件数": f"{r_cnt} 件",
                                "着順割合 (%)": f"{r_pct:.1f} %"
                            })
                        st.table(pd.DataFrame(rank_data))
                    else:
                        st.caption("※この進入パターンの記録はまだありません。")
        else:
            st.warning(f"「{selected_stadium}」での記録データはまだ登録されていません。")
    else:
        st.info("データが登録されると、場ごとの割合が表示されます。")

st.markdown("---")

# --- 3. 管理者認証エリア ---
st.header("🔒 管理者メニュー（データ入力・バックアップ）")

input_password = st.text_input("管理者パスワードを入力してください", type="password")

if input_password == ADMIN_PASSWORD:
    st.success("認証に成功しました。管理メニューを利用できます。")
    
    # --- 進入データの記録 ---
    st.subheader("📝 進入データの記録")

    with st.form(key="entry_form", clear_on_submit=True):
        racer_name = st.text_input("選手名（5号艇）", placeholder="例: 毒島誠")

        gap_pattern = st.selectbox("5号艇の進入位置を選択してください", GAP_PATTERNS)

        st.markdown("**レース情報の詳細選択**")
        col_stadium, col_rank = st.columns(2)
        with col_stadium:
            stadium = st.selectbox("開催場（全国24場）", BOAT_RACE_STADIUMS)
        with col_rank:
            rank = st.selectbox("着順", ["1着", "2着", "3着", "4着", "5着", "6着", "転覆・落水・F等"])

        col_year, col_month = st.columns(2)
        current_year = datetime.now().year
        with col_year:
            year = st.selectbox("年（西暦）", list(range(current_year, 2019, -1)))
        with col_month:
            month = st.selectbox("月", [f"{m}月" for m in range(1, 13)])

        submit_button = st.form_submit_button(label="データを記録・スプレッドシートに保存")

    if submit_button:
        if not racer_name.strip():
            st.error("選手名を入力してください。")
        else:
            race_info_str = f"{year}年{month} / {stadium} / {rank}"
            
            # スプレッドシートへ直接書き込み
            if append_data_to_sheets(racer_name.strip(), gap_pattern, race_info_str):
                st.success(f"「{racer_name}」選手のデータをスプレッドシートに自動保存しました！")
                st.rerun()

    st.markdown("---")

    # --- バックアップ & データ復元 ---
    st.subheader("💾 バックアップ & データ復元")

    col_exp, col_imp = st.columns(2)

    with col_exp:
        st.caption("📥 バックアップ（保存）")
        if not df_all.empty:
            csv_data = df_all[["選手名", "進入パターン", "レース情報"]].to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="CSVでバックアップをダウンロード",
                data=csv_data,
                file_name="boat_race_data_backup.csv",
                mime="text/csv",
            )
        else:
            st.caption("記録データがないためダウンロードできません。")

    with col_imp:
        st.caption("📤 バックアップから一括復元")
        uploaded_csv = st.file_uploader("保存したCSVファイルをアップロード", type=["csv"])
        if uploaded_csv is not None:
            try:
                imported_df = pd.read_csv(uploaded_csv)
                if st.button("このデータをスプレッドシートに追加・復元する"):
                    client = get_gspread_client()
                    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
                    for _, row in imported_df.iterrows():
                        sheet.append_row([row.get("選手名", ""), row.get("進入パターン", ""), row.get("レース情報", "")])
                    st.success("スプレッドシートへの復元・統合が完了しました！")
                    st.rerun()
            except Exception as e:
                st.error("CSVファイルの読み込みに失敗しました。")

elif input_password:
    st.error("パスワードが正しくありません。")