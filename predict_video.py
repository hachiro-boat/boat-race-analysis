import streamlit as st
import pandas as pd
import json
import os

# データの保存先ファイル名（自動作成されます）
DATA_FILE = "data.json"

st.set_page_config(page_title="ボートレース 進入・間隙データ記憶アプリ", layout="centered")

st.title("🚤 5号艇 進入・間隙データ記録・検索アプリ")

# --- ファイルからデータを読み込む関数 ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

# --- データをファイルに保存する関数 ---
def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# セッション状態の初期化（ファイルから読み込み）
if "records" not in st.session_state:
    st.session_state.records = load_data()

# --- 1. データ入力エリア ---
st.header("📝 進入データの記録")

with st.form(key="entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        racer_name = st.text_input("選手名（5号艇）", placeholder="例: 毒島誠")
    with col2:
        race_info = st.text_input("レース情報（任意）", placeholder="例: 住之江12R / 2026-09-28")

    st.write("**どの艇とどの艇の間に入っていったかを選択してください**")
    
    col3, col4 = st.columns(2)
    with col3:
        left_boat = st.selectbox("左側の艇（内側など）", ["1号艇", "2号艇", "3号艇", "4号艇", "6号艇", "最内（差し切り）"])
    with col4:
        right_boat = st.selectbox("右側の艇（外側など）", ["1号艇", "2号艇", "3号艇", "4号艇", "6号艇", "最外（まくり）"])

    submit_button = st.form_submit_button(label="データを記録・記憶する")

if submit_button:
    if not racer_name.strip():
        st.error("選手名を入力してください。")
    else:
        gap_pattern = f"{left_boat} と {right_boat} の間"
        new_record = {
            "選手名": racer_name.strip(),
            "進入パターン": gap_pattern,
            "レース情報": race_info.strip() if race_info else "未入力",
        }
        st.session_state.records.append(new_record)
        save_data(st.session_state.records)
        st.success(f"「{racer_name}」選手の進入パターン（{gap_pattern}）を記録・保存しました！")

st.markdown("---")

# --- 2. 名前検索＆集計エリア ---
st.header("🔍 選手名でパターン・件数を検索")

search_query = st.text_input("検索したい選手名を入力", placeholder="例: 毒島")

if search_query.strip():
    filtered = [
        rec for rec in st.session_state.records 
        if search_query.strip().lower() in rec["選手名"].lower()
    ]
    
    if filtered:
        df = pd.DataFrame(filtered)
        
        st.subheader(f"📊 「{search_query}」選手の検索結果")
        st.write(f"総記録件数: **{len(filtered)} 件**")
        
        summary = df["進入パターン"].value_counts().reset_index()
        summary.columns = ["進入パターン（どの艇の間か）", "件数"]
        
        st.table(summary)
        
        with st.expander("詳細な記録一覧を見る"):
            st.dataframe(df, use_container_width=True)
    else:
        st.warning(f"「{search_query}」選手の記録データは見つかりませんでした。")

elif st.session_state.records:
    st.info(f"💡 現在、合計 **{len(st.session_state.records)} 件** のデータが記録・保存されています。")
    with st.expander("全記録一覧を表示"):
        st.dataframe(pd.DataFrame(st.session_state.records), use_container_width=True)

st.markdown("---")

# --- 3. バックアップ・復元エリア ---
st.header("💾 バックアップ & データ復元")

col_exp, col_imp = st.columns(2)

with col_exp:
    st.subheader("📥 バックアップ（保存）")
    if st.session_state.records:
        df_export = pd.DataFrame(st.session_state.records)
        csv_data = df_export.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="CSVでバックアップをダウンロード",
            data=csv_data,
            file_name="boat_race_data_backup.csv",
            mime="text/csv",
        )
    else:
        st.caption("記録データがないためダウンロードできません。")

with col_imp:
    st.subheader("📤 バックアップから復元")
    uploaded_csv = st.file_uploader("保存したCSVファイルをアップロード", type=["csv"])
    if uploaded_csv is not None:
        try:
            imported_df = pd.read_csv(uploaded_csv)
            imported_records = imported_df.to_dict(orient="records")
            if st.button("このデータをアプリに復元・統合する"):
                st.session_state.records.extend(imported_records)
                save_data(st.session_state.records)
                st.success("データの復元が完了しました！")
                st.rerun()
        except Exception as e:
            st.error("CSVファイルの読み込みに失敗しました。")