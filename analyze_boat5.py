import sqlite3
from datetime import datetime
from ultralytics import YOLO

# ==========================================
# 1. データベース設定 & 初期化
# ==========================================
DB_NAME = 'boat_race.db'

def init_db():
    """データベースとテーブルを作成する"""
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
    """今回の分析結果をDBに保存する"""
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

def show_player_stats(player_name):
    """該当選手の全レース蓄積データから統計確率を算出・表示する"""
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
    
    race_cnt, ahead, b12, b23, b34, behind, total = row
    
    print(f"\n==================================================")
    print(f"📊 【選手通算データ】 選手名: {player_name}")
    print(f"解析レース数: {race_cnt} レース")
    print(f"==================================================")
    
    if total and total > 0:
        print(f"全グループの先頭    : {ahead:5d} フレーム ({ahead/total*100:5.1f}%)")
        print(f"1号艇と2号艇の間    : {b12:5d} フレーム ({b12/total*100:5.1f}%)")
        print(f"2号艇と3号艇の間    : {b23:5d} フレーム ({b23/total*100:5.1f}%)")
        print(f"3号艇と4号艇の間    : {b34:5d} フレーム ({b34/total*100:5.1f}%)")
        print(f"全グループの後方    : {behind:5d} フレーム ({behind/total*100:5.1f}%)")
        print(f"--------------------------------------------------")
        print(f"総観測フレーム数    : {total:5d} フレーム")
    else:
        print("蓄積データがまだありません。")

# ==========================================
# 2. 推論・分析処理
# ==========================================
init_db()

# 分析対象の設定
model = YOLO('runs/detect/boat_race_yolo/weights/best.pt')
video_path = '2026-09-27 082717.mp4'  # 👈 動画ファイル名に合わせて変更
player_name = "宗行治哉"               # 👈 分析対象の5号艇選手名

position_counts = {
    'ahead_of_all': 0,
    'between_1_and_2': 0,
    'between_2_and_3': 0,
    'between_3_and_4': 0,
    'behind_all': 0,
    'undetected': 0
}

print(f"分析を開始します: 動画『{video_path}』 / 選手『{player_name}』")

results = model.track(source=video_path, stream=True, conf=0.25, tracker="bytetrack.yaml")

for result in results:
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        continue
    
    boat_positions = {}
    for box in boxes:
        cls_id = int(box.cls[0])
        class_name = model.names[cls_id]
        
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        center_x = (x1 + x2) / 2
        boat_positions[class_name] = center_x
    
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

# 有効フレーム数
total_valid_frames = sum([v for k, v in position_counts.items() if k != 'undetected'])

# 今回のデータ保存
if total_valid_frames > 0:
    save_analysis(player_name, video_path, position_counts, total_valid_frames)
    print("\n✅ 今回のレース解析データをデータベースに保存しました！")

# 通算データの集計・表示
show_player_stats(player_name)