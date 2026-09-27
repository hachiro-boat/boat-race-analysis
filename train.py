import os
from ultralytics import YOLO

def main():
    # 1. 事前学習済み軽量モデル（yolov8n.pt）のロード
    model = YOLO('yolov8n.pt')

    # 2. 学習の実行
    results = model.train(
        data='dataset.yaml',   # データセット設定ファイルのパス
        epochs=50,             # エポック数
        imgsz=640,             # 画像サイズ
        batch=8,              # バッチサイズ
        name='boat_race_yolo', # 出力フォルダ名
        exist_ok=True
    )

    print("学習が完了しました！")
    print(f"最良モデルのパス: runs/detect/boat_race_yolo/weights/best.pt")

if __name__ == '__main__':
    main()