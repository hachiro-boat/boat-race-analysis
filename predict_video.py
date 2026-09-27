from ultralytics import YOLO

# 1. 学習済みモデルの読み込み
model = YOLO('runs/detect/boat_race_yolo/weights/best.pt')

# 2. 動画ファイルに対するトラッキング推論
# ※ race_video.mp4 を実際にテストしたい動画ファイル名に変更してください
results = model.track(
    source='レコーディング 2026-09-27 082717.mp4', # 動画ファイルのパス
    save=True,               # 検出結果動画を保存
    conf=0.25,               # 確信度のしきい値（低すぎると誤検出、高すぎると見落とし）
    tracker="bytetrack.yaml" # 追跡アルゴリズム（Bytetrack）
)

print("動画の解析が完了しました！ runs/detect/track フォルダを確認してください。")