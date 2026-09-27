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
    
    # アップロードされた動画に対して推論/追跡を実行
    results = model.track(
        source=tfile.name,
        tracker="bytetrack.yaml",
        show=False
    )
    
    st.success("処理が完了しました！")