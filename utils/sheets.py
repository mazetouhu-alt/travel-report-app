"""
Googleスプレッドシート連携モジュール
- サービスアカウントで認証し、gspreadでシートの読み書きを行う
- 1行 = 1件の出張報告。先頭列 "ID" で行を一意に識別し、
  修正時はIDが一致する行を上書きする
"""
import uuid
import datetime as dt

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# スプレッドシートの列構成（1行目のヘッダー）
# 列の並び順を変える場合は _record_to_row() も合わせて修正すること
HEADERS = [
    "ID",
    "更新日時",
    "期間",
    "担当者",
    "場所",
    "訪問先",
    "宿泊有無",
    "目的",
    "具体的な活動内容",
]


@st.cache_resource(show_spinner=False)
def _get_client() -> gspread.Client:
    """サービスアカウント情報から認証済みgspreadクライアントを作成（キャッシュ）"""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_worksheet() -> gspread.Worksheet:
    """対象スプレッドシート内の対象シートを取得。無ければ作成してヘッダーを設定"""
    client = _get_client()
    spreadsheet_id = st.secrets["SPREADSHEET_ID"]
    sheet_name = st.secrets.get("SHEET_NAME", "出張報告書")

    sh = client.open_by_key(spreadsheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=1000, cols=len(HEADERS))
        ws.append_row(HEADERS)
        return ws

    # ヘッダー行が無い/不完全な場合は補正
    first_row = ws.row_values(1)
    if first_row != HEADERS:
        if not first_row:
            ws.append_row(HEADERS)
        # 既存ヘッダーがある場合は変更しない（列構成が異なる既存シートを壊さないため）
    return ws


def load_records() -> pd.DataFrame:
    """全件をDataFrameで取得（呼び出し側で都度キャッシュ制御する想定なのでここではキャッシュしない）"""
    ws = _get_worksheet()
    records = ws.get_all_records()  # ヘッダー行を自動でキーとして辞書化
    df = pd.DataFrame(records)
    return df


def _record_to_row(record: dict) -> list:
    """フォームの辞書データをHEADERS順のリストに変換"""
    return [
        record.get("ID", ""),
        record.get("更新日時", ""),
        record.get("期間", ""),
        record.get("担当者", ""),
        record.get("場所", ""),
        record.get("訪問先", ""),
        record.get("宿泊有無", ""),
        record.get("目的", ""),
        record.get("具体的な活動内容", ""),
    ]


def save_record(record: dict) -> str:
    """
    新規追加または既存行の上書き更新を行う。
    record に "ID" が空の場合は新規発行して追加。
    既存のIDが指定されている場合は該当行を上書き。
    戻り値: 保存したレコードのID
    """
    ws = _get_worksheet()

    record = dict(record)  # 呼び出し元の辞書を汚さないようコピー
    record["更新日時"] = dt.datetime.now().strftime("%Y/%m/%d %H:%M")

    if not record.get("ID"):
        # 新規作成
        record["ID"] = uuid.uuid4().hex[:12]
        ws.append_row(_record_to_row(record), value_input_option="USER_ENTERED")
        return record["ID"]

    # 既存行を検索して上書き
    cell = None
    try:
        cell = ws.find(record["ID"], in_column=1)
    except gspread.exceptions.CellNotFound:
        cell = None

    if cell is None:
        # IDはあるが行が見つからない場合は新規行として追加
        ws.append_row(_record_to_row(record), value_input_option="USER_ENTERED")
    else:
        row_number = cell.row
        ws.update(
            f"A{row_number}:I{row_number}",
            [_record_to_row(record)],
            value_input_option="USER_ENTERED",
        )
    return record["ID"]
