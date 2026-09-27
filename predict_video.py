import streamlit as st
from ultralytics import YOLO
import tempfile
import cv2
import pandas as pd

st.title("ボートレース5号艇 差し・間隙分析アプリ")

# 1. データの記憶領域（Session State）の初期化
if "history" not in st.session_state:
    st.session_state.history = []  # dict: {"racer_name": str, "gap": str, "frame": int}

# モデルの読み込み
model = YOLO('models/best.pt')

# 2. 選手名入力と動画アップロード
racer_name = st.text_input("5号艇の選手名を入力してください", value="登録選手A")
uploaded_file = st.file_uploader("分析したい動画(mp4)を選択してください", type=['mp4', 'avi', 'mov'])

if uploaded_file is not None and racer_name:
    if st.button("動画を解析して記憶する"):
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        
        cap = cv2.VideoCapture(tfile.name)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        st_frame = st.empty()
        
        frame_count = 0
        detected_gaps = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # YOLOで推論
            results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
            
            # 艇の検出位置を解析
            boats = []
            boat_5_x = None
            
            if results[0].boxes is not None:
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id] if hasattr(model, 'names') else str(cls_id)
                    
                    # バウンディングボックスの中心X座標
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    center_x = (x1 + x2) / 2.0
                    
                    boats.append({"name": cls_name, "x": center_x})
                    if cls_name == "boat_5" or cls_name == "5":
                        boat_5_x = center_x

            # 5号艇が検出されていて、他の艇もいる場合に左右の艇（間隙）を判定
            if boat_5_x is not None and len(boats) > 1:
                # X座標順（左から右）にソート
                boats_sorted = sorted(boats, key=lambda b: b["x"])
                
                # 5号艇のインデックスを探す
                b5_idx = next((i for i, b in enumerate(boats_sorted) if b["name"] in ["boat_5", "5"]), None)
                
                if b5_idx is not None:
                    left_boat = boats_sorted[b5_idx - 1]["name"] if b5_idx > 0 else "大外"
                    right_boat = boats_sorted[b5_idx + 1]["name"] if b5_idx < len(boats_sorted) - 1 else "インコース最内"
                    
                    gap_str = f"{left_boat} と {right_boat} の間"
                    detected_gaps.append(gap_str)
                    
                    # 履歴に記憶
                    st.session_state.history.append({
                        "racer_name": racer_name,
                        "gap": gap_str,
                        "frame": frame_count
                    })

            # 描画と表示
            annotated_frame = results[0].plot()
            annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            st_frame.image(annotated_frame_rgb, channels="RGB", use_container_width=True)
            
            if total_frames > 0:
                progress_bar.progress(frame_count / total_frames)
                status_text.text(f"解析中... ({frame_count}/{total_frames} フレーム)")

        cap.release()
        st.success(f"{racer_name} 選手の解析データを記憶しました！")

st.markdown("---")

# 3. 名前検索と件数表示セクション
st.header("🔍 選手名で進入位置・間隙パターンを検索")

search_query = st.text_input("検索したい選手名を入力してください")

if search_query:
    # 該当する選手のデータを抽出
    filtered_data = [item for item in st.session_state.history if search_query.lower() in item["racer_name"].lower()]
    
    if filtered_data:
        df = pd.DataFrame(filtered_data)
        
        # どの艇の間に入ったかの件数を集計
        summary = df["gap"].value_counts().reset_index()
        summary.columns = ["進入パターン（どの艇の間か）", "検出件数（フレーム数）"]
        
        st.subheader(f"📊 「{search_query}」選手の分析結果")
        st.write(f"総検出データ数: **{len(filtered_data)} 件**")
        
        # 結果を表で表示
        st.dataframe(summary, use_container_width=True)
        
        # 詳細ログの表示
        with st.expander("詳細なフレーム別ログを表示"):
            st.dataframe(df, use_container_width=True)
    else:
        st.info(f"「{search_query}」選手の記憶データは見つかりませんでした。")
elif st.session_state.history:
    st.write("💡 全体の記憶データ件数:", len(st.session_state.history), "件")