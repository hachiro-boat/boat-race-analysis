from ultralytics import YOLO

# 1. 学習済みモデルの読み込み
model = YOLO('runs/detect/boat_race_yolo/weights/best.pt')

# 2. テストしたい画像に対して検出を実行
# ※ test.jpg の部分を、テストしたい画像ファイル名に変更してください
results = model.predict(source='images/スクリーンショット 2026-09-27 004314.png', save=True, conf=0.25)

print("検出が完了しました！結果は runs/detect/predict フォルダに保存されました。")