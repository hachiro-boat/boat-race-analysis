import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup

# --- Google Spreadsheets 設定 ---
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 1. サービスアカウントの鍵ファイル
creds = Credentials.from_service_account_file('secret_key.json', scopes=SCOPE)
client = gspread.authorize(creds)

# 2. スプレッドシートを開く（ここにコピーしたスプレッドシートIDを入れてください）
SPREADSHEET_ID = '1uPIw3EBMDd3HYnaAuoAomCCC6eVui85P6bpxbDnaBCc'
sheet = client.open_by_key(SPREADSHEET_ID).sheet1

def add_race_data(player_name, entry_pattern, race_info):
    """
    スプレッドシートに1行データを追加する関数
    """
    row = [player_name, entry_pattern, race_info]
    sheet.append_row(row)
    print(f"追加完了: {row}")

# --- テスト実行 ---
if __name__ == '__main__':
    # テストデータで書き込みを確認
    add_race_data('毒島誠', '123/456', '2026-10-02 桐生12R')