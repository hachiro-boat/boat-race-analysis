import os
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
from ultralytics import YOLO

# ==========================================
# 1. データベース関数
# ==========================================
DB_NAME = 'boat_race.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS race_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            video_name TEXT NOT NULL,
            ahead_of_all INTEGER DEFAULT 0,
            between_1_and_2 INTEGER DEFAULT 0,
            between_2_and_3 INTEGER DEFAULT 0,
            between_3_and_4 INTEGER DEFAULT 0,
            behind_all INTEGER DEFAULT 0,
            total_valid_frames INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_analysis(player_name, video_name, counts, total_valid):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO race_analysis 
        (player_name, video_name, ahead_of_all, between_1_and_2, between_2_and_3, between_3_and_4, behind_all, total_valid_frames)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        player_name,
        video_name,
        counts['ahead_of_all'],
        counts['between_1_and_2'],
        counts['between_2_and_3'],
        counts['between_3_and_4'],
        counts['behind_all'],
        total_valid
    ))
    conn.commit()
    conn.close()

def get_player_stats(player_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            COUNT(id) as race_count,
            SUM(ahead_of_all),
            SUM(between_1_and_2),
            SUM(between_2_and_3),
            SUM(between_3_and_4),
            SUM(behind_all),
            SUM(total_valid_frames)
        FROM race_analysis
        WHERE player_name = ?
    ''', (player_name,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_all_players():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT player_name FROM race_analysis')
    players = [row[0] for row in cursor.fetchall()]
    conn.close()
    return players

# DBの初期化
init_db()

# ==========================================
# 2. Streamlit UI 画面設計
# ==========================================
st.set_page_config(page_title="ボートレース 5号艇進入解析", layout="wide")
st.title("🚤 ボートレース 5号艇進入位置・確率解析アプリ")

# サイドバー：ナビゲーション
menu = st.sidebar.radio("メニュー", ["🎥 動画解析・データ追加", "📊 選手通算データ確認"])

# YOLOモデルの読み込み（キャッシュ化して高速化）
@st.cache_resource
def load_model():
    return YOLO('models/best.pt')

model = load_model()

# ------------------------------------------
# メニュー1: 動画解析・データ追加
# ------------------------------------------
if menu == "🎥 動画解析・データ追加":
    st.header("新しいレース動画の解析")
    
    col1, col2 = st.columns(2)
    with col1:
        player_name = st.text_input("5号艇の選手名を入力", placeholder="例: 宗行治哉")
    with col2:
        uploaded_file = st.file_uploader("レース動画を選択 (.mp4)", type=["mp4", "avi", "mov"])

    if st.button("🚀 解析を開始する") and player_name and uploaded_file:
        # アップロードされた動画を一時保存
        temp_video_path = f"temp_{uploaded_file.name}"
        with open(temp_video_path, "wb") as f:
            f.write(uploaded_file.read())

        st.info("AIによる位置検出を行っています... しばらくお待ちください。")
        progress_bar = st.progress(0)

        position_counts = {
            'ahead_of_all': 0,
            'between_1_and_2': 0,
            'between_2_and_3': 0,
            'between_3_and_4': 0,
            'behind_all': 0,
            'undetected': 0
        }

        # YOLO推論
        results = model.track(source=temp_video_path, stream=True, conf=0.25, tracker="bytetrack.yaml")

        for i, result in enumerate(results):
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                boat_positions = {}
                for box in boxes:
                    cls_id = int(box.cls[0])
                    class_name = model.names[cls_id]
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    boat_positions[class_name] = (x1 + x2) / 2

                required_boats = ['boat_1', 'boat_2', 'boat_3', 'boat_4', 'boat_5']
                if all(b in boat_positions for b in required_boats):
                    target_boats = {b: boat_positions[b] for b in ['boat_1', 'boat_2', 'boat_3', 'boat_4']}
                    sorted_targets = sorted(target_boats.items(), key=lambda item: item[1])
                    b5_pos = boat_positions['boat_5']

                    if b5_pos < sorted_targets[0][1]:
                        position_counts['ahead_of_all'] += 1
                    elif sorted_targets[0][1] <= b5_pos < sorted_targets[1][1]:
                        position_counts['between_1_and_2'] += 1
                    elif sorted_targets[1][1] <= b5_pos < sorted_targets[2][1]:
                        position_counts['between_2_and_3'] += 1
                    elif sorted_targets[2][1] <= b5_pos < sorted_targets[3][1]:
                        position_counts['between_3_and_4'] += 1
                    else:
                        position_counts['behind_all'] += 1
                else:
                    position_counts['undetected'] += 1

        # 一時ファイルの削除
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

        total_valid = sum([v for k, v in position_counts.items() if k != 'undetected'])

        if total_valid > 0:
            save_analysis(player_name, uploaded_file.name, position_counts, total_valid)
            st.success(f"✅ 解析が完了し、データベースに保存されました！（全 {total_valid} フレーム）")
        else:
            st.error("有効な艇の組み合わせが検出できませんでした。")

# ------------------------------------------
# メニュー2: 選手通算データ確認
# ------------------------------------------
elif menu == "📊 選手通算データ確認":
    st.header("選手別 通算進入確率")
    
    players = get_all_players()
    if not players:
        st.warning("まだデータベースに解析データが登録されていません。先に「動画解析」を実行してください。")
    else:
        selected_player = st.selectbox("選手を選択してください", players)
        
        if selected_player:
            race_cnt, ahead, b12, b23, b34, behind, total = get_player_stats(selected_player)
            
            if total and total > 0:
                st.subheader(f"【{selected_player} 選手】（解析レース数: {race_cnt} レース / 総観測: {total} フレーム）")
                
                # データフレーム作成
                df = pd.DataFrame({
                    '進入位置': ['全グループの先頭', '1号艇と2号艇の間', '2号艇と3号艇の間', '3号艇と4号艇の間', '全グループの後方'],
                    'フレーム数': [ahead, b12, b23, b34, behind],
                    '確率 (%)': [
                        round((ahead/total)*100, 1),
                        round((b12/total)*100, 1),
                        round((b23/total)*100, 1),
                        round((b34/total)*100, 1),
                        round((behind/total)*100, 1)
                    ]
                })

                col_chart, col_table = st.columns([3, 2])
                
                with col_chart:
                    # 棒グラフ描画
                    fig = px.bar(
                        df, 
                        x='進入位置', 
                        y='確率 (%)', 
                        text='確率 (%)',
                        color='進入位置',
                        title=f"{selected_player} 選手の進入パターン確率"
                    )
                    fig.update_traces(texttemplate='%{text}%', textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)

                with col_table:
                    st.dataframe(df, hide_index=True, use_container_width=True)