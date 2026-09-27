import streamlit as st
import pandas as pd

st.set_page_config(page_title="ボートレース 進入・間隙データ記憶アプリ", layout="centered")

st.title("🚤 5号艇 進入・間隙データ記録・検索アプリ")

# データ記憶領域（Session State）の初期化
if "records" not in st.session_state:
    st.session_state.records = []

# --- 1. データ入力エリア ---
st.header("📝 進入データの記録")

with st.form(key="entry_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        racer_name = st.text_input("選手名（5号艇）", placeholder="例: 毒島誠")
    with col2:
        race_info = st.text_input("レース情報（任意）", placeholder="例: 住之江12R / 2026-09-27")

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
        st.success(f"「{racer_name}」選手の進入パターン（{gap_pattern}）を記録しました！")

st.markdown("---")

# --- 2. 名前検索＆集計エリア ---
st.header("🔍 選手名でパターン・件数を検索")

search_query = st.text_input("検索したい選手名を入力", placeholder="例: 毒島")

if search_query.strip():
    # 検索キーワードに一致するデータを抽出
    filtered = [
        rec for rec in st.session_state.records 
        if search_query.strip().lower() in rec["選手名"].lower()
    ]
    
    if filtered:
        df = pd.DataFrame(filtered)
        
        st.subheader(f"📊 「{search_query}」選手の検索結果")
        st.write(f"総記録件数: **{len(filtered)} 件**")
        
        # 進入パターンごとの件数を集計
        summary = df["進入パターン"].value_counts().reset_index()
        summary.columns = ["進入パターン（どの艇の間か）", "件数"]
        
        # 集計テーブルの表示
        st.table(summary)
        
        # 履歴詳細
        with st.expander("詳細な記録一覧を見る"):
            st.dataframe(df, use_container_width=True)
    else:
        st.warning(f"「{search_query}」選手の記録データは見つかりませんでした。")

elif st.session_state.records:
    st.info(f"💡 現在、合計 **{len(st.session_state.records)} 件** のデータが記憶されています。")
    with st.expander("全記録一覧を表示"):
        st.dataframe(pd.DataFrame(st.session_state.records), use_container_width=True)