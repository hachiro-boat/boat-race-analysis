import streamlit as st
from ultralytics import YOLO
import tempfile
import cv2

st.title("ボートレース動画分析 (YOLOv8)")

# モデルの読み込み
model = YOLO('models/best.pt')

# 動画ファイルのアップロードUI
uploaded_file = st.file_uploader("分析したい動画(mp4)を選択してください", type=['mp4', 'avi', 'mov'])

if uploaded_file is not None:
    # 一時ファイルとして保存
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    
    st.write("推論・追跡処理を実行中...")
    
    # 進行状況バーを表示
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 動画を読み込んで1フレームずつ処理＆表示
    cap = cv2.VideoCapture(tfile.name)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    st_frame = st.empty()
    
    frame_count = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # YOLOで追跡実行 (stream=Trueで1フレームずつ処理)
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)
        
        # 検出結果を描画したフレームを取得
        annotated_frame = results[0].plot()
        
        # BGRからRGBに変換してStreamlitに表示
        annotated_frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
        st_frame.image(annotated_frame_rgb, channels="RGB", use_container_width=True)
        
        frame_count += 1
        if total_frames > 0:
            progress = frame_count / total_frames
            progress_bar.progress(progress)
            status_text.text(f"解析中... ({frame_count}/{total_frames} フレーム)")

    cap.release()
    st.success("解析が完了しました！")