"""
出張報告書作成アプリ（Streamlit）
------------------------------------------------------------
機能:
  1. 入力フォーム（期間・担当者・場所・訪問先・宿泊有無・目的・活動内容）
  2. 「目的」「活動内容」をGemini API（無料）でビジネス文書調に整形（ボタン押下）
  3. 整形後の文章を画面上で直接編集可能
  4. Googleスプレッドシートに保存（gspread）
  5. 入力内容を反映したPDFを生成してダウンロード
  6. 既存データを読み込んで修正・上書き保存
"""
import streamlit as st

from utils import sheets, ai, pdf

st.set_page_config(page_title="出張報告書作成アプリ", page_icon="🧳", layout="centered")

# ------------------------------------------------------------
# セッション状態の初期化
# ------------------------------------------------------------
DEFAULTS = {
    "edit_id": "",       # 空文字なら新規作成、値があれば既存行の上書き更新
    "period": "",
    "staff": "",
    "location": "",
    "destination": "",
    "accommodation": "未選択",
    "purpose": "",
    "activity": "",
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_form():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def load_into_form(row: dict):
    st.session_state["edit_id"] = row.get("ID", "")
    st.session_state["period"] = row.get("期間", "")
    st.session_state["staff"] = row.get("担当者", "")
    st.session_state["location"] = row.get("場所", "")
    st.session_state["destination"] = row.get("訪問先", "")
    st.session_state["accommodation"] = row.get("宿泊有無") or "未選択"
    st.session_state["purpose"] = row.get("目的", "")
    st.session_state["activity"] = row.get("具体的な活動内容", "")


# ------------------------------------------------------------
# サイドバー：既存データの呼び出し（修正機能）
# ------------------------------------------------------------
st.sidebar.header("既存データの呼び出し")

if st.sidebar.button("一覧を再読み込み", use_container_width=True):
    st.cache_data.clear()

try:
    df = st.cache_data(ttl=30)(sheets.load_records)()
except Exception as e:  # noqa: BLE001
    df = None
    st.sidebar.error(f"スプレッドシートの読み込みに失敗しました:\n{e}")

if df is not None and not df.empty:
    options = ["-- 新規作成 --"] + [
        f"{row['期間']} / {row['担当者']} / {row['訪問先']}"
        for _, row in df.iterrows()
    ]
    selected = st.sidebar.selectbox("編集する報告書を選択", options)

    if selected != "-- 新規作成 --":
        idx = options.index(selected) - 1
        if st.session_state.get("_loaded_idx") != idx:
            load_into_form(df.iloc[idx].to_dict())
            st.session_state["_loaded_idx"] = idx
    else:
        if st.session_state.get("_loaded_idx") is not None:
            reset_form()
            st.session_state["_loaded_idx"] = None
else:
    st.sidebar.caption("まだ登録データがありません。")

if st.session_state["edit_id"]:
    st.sidebar.success(f"編集中: ID={st.session_state['edit_id']}")
    if st.sidebar.button("新規作成に切り替え", use_container_width=True):
        reset_form()
        st.session_state["_loaded_idx"] = None
        st.rerun()

# ------------------------------------------------------------
# メインフォーム
# ------------------------------------------------------------
st.title("🧳 出張報告書作成アプリ")
st.caption("入力 → AIで整形 → 編集 → スプレッドシート保存 / PDF出力")

col1, col2 = st.columns(2)
with col1:
    st.session_state["period"] = st.text_input(
        "期間", value=st.session_state["period"], placeholder="例）2026/08/03〜2026/08/04"
    )
    st.session_state["location"] = st.text_input(
        "場所", value=st.session_state["location"], placeholder="例）大阪府大阪市"
    )
    st.session_state["accommodation"] = st.selectbox(
        "宿泊有無",
        ["未選択", "あり", "なし"],
        index=["未選択", "あり", "なし"].index(st.session_state["accommodation"])
        if st.session_state["accommodation"] in ["未選択", "あり", "なし"]
        else 0,
    )
with col2:
    st.session_state["staff"] = st.text_input(
        "担当者", value=st.session_state["staff"], placeholder="例）山田 太郎"
    )
    st.session_state["destination"] = st.text_input(
        "訪問先", value=st.session_state["destination"], placeholder="例）A社 大阪支社"
    )

st.divider()

# --- 目的 ---
st.subheader("目的")
st.session_state["purpose"] = st.text_area(
    "目的（メモ書きでOK。AIボタンでビジネス文書調に整形できます）",
    value=st.session_state["purpose"],
    height=90,
    label_visibility="collapsed",
    placeholder="例）A社との定例商談、新製品の提案",
)
if st.button("✨ 目的をAIで整形", key="btn_purpose"):
    if not st.session_state["purpose"].strip():
        st.warning("先に目的のメモを入力してください。")
    else:
        with st.spinner("AIが文章を整形しています..."):
            context = {
                "期間": st.session_state["period"],
                "訪問先": st.session_state["destination"],
            }
            try:
                st.session_state["purpose"] = ai.polish_business_text(
                    "目的", st.session_state["purpose"], context
                )
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"AI整形に失敗しました: {e}")

# --- 具体的な活動内容・成果 ---
st.subheader("具体的な活動内容・成果")
st.session_state["activity"] = st.text_area(
    "活動内容（メモ書きでOK。AIボタンでビジネス文書調に整形できます）",
    value=st.session_state["activity"],
    height=160,
    label_visibility="collapsed",
    placeholder="例）\n・A社担当者と定例商談を実施\n・新製品の導入状況をヒアリング\n・追加発注の打診を受けた",
)
if st.button("✨ 活動内容をAIで整形", key="btn_activity"):
    if not st.session_state["activity"].strip():
        st.warning("先に活動内容のメモを入力してください。")
    else:
        with st.spinner("AIが文章を整形しています..."):
            context = {
                "期間": st.session_state["period"],
                "訪問先": st.session_state["destination"],
                "目的": st.session_state["purpose"],
            }
            try:
                st.session_state["activity"] = ai.polish_business_text(
                    "具体的な活動内容・成果", st.session_state["activity"], context
                )
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"AI整形に失敗しました: {e}")

st.divider()

# ------------------------------------------------------------
# 保存・PDF出力
# ------------------------------------------------------------
save_col, pdf_col = st.columns(2)

with save_col:
    button_label = "🔄 上書き更新" if st.session_state["edit_id"] else "💾 スプレッドシートに保存"
    if st.button(button_label, type="primary", use_container_width=True):
        record = {
            "ID": st.session_state["edit_id"],
            "期間": st.session_state["period"],
            "担当者": st.session_state["staff"],
            "場所": st.session_state["location"],
            "訪問先": st.session_state["destination"],
            "宿泊有無": st.session_state["accommodation"],
            "目的": st.session_state["purpose"],
            "具体的な活動内容": st.session_state["activity"],
        }
        try:
            new_id = sheets.save_record(record)
            st.session_state["edit_id"] = new_id
            st.cache_data.clear()
            st.success(f"保存しました（ID: {new_id}）")
        except Exception as e:  # noqa: BLE001
            st.error(f"保存に失敗しました: {e}")

with pdf_col:
    if st.button("📄 PDFを作成", use_container_width=True):
        try:
            pdf_bytes = pdf.generate_pdf(
                {
                    "period": st.session_state["period"],
                    "staff": st.session_state["staff"],
                    "location": st.session_state["location"],
                    "destination": st.session_state["destination"],
                    "accommodation": st.session_state["accommodation"],
                    "purpose": st.session_state["purpose"],
                    "activity": st.session_state["activity"],
                }
            )
            st.session_state["_pdf_bytes"] = pdf_bytes
        except Exception as e:  # noqa: BLE001
            st.error(f"PDF生成に失敗しました: {e}")

if st.session_state.get("_pdf_bytes"):
    st.download_button(
        "⬇️ PDFをダウンロード",
        data=st.session_state["_pdf_bytes"],
        file_name=f"出張報告書_{st.session_state['destination'] or 'report'}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
