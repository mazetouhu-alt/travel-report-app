"""
Gemini API連携モジュール
- 「目的」「具体的な活動内容」のメモ書きを、ビジネス文書として適切な
  トーンの文章に整形する
- 無料運用のため、Google AI Studioで発行できる無料のGemini APIキーを使用
  （Google公式の統一SDK "google-genai" を使用。モデルは無料枠のある gemini-2.5-flash）
"""
from google import genai
from google.genai import types
import streamlit as st

MODEL = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 600  # 出力トークン上限（応答速度・無料枠の消費を抑えるため）


@st.cache_resource(show_spinner=False)
def _get_client() -> genai.Client:
    api_key = st.secrets["GEMINI_API_KEY"]
    # 新しい形式のAPIキー（AQ.〜）に対応させるため、http_optionsで明示的に指定します
    return genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})


def polish_business_text(field_label: str, raw_text: str, context: dict) -> str:
    """
    箇条書き/メモ書きのテキストを、上司に提出できるビジネス文書調の文章に整形する。

    Args:
        field_label: "目的" または "具体的な活動内容・成果" など、整形対象の項目名
        raw_text: ユーザーが入力したメモ書き
        context: 期間・担当者・場所・訪問先など、文脈として渡す周辺情報の辞書

    Returns:
        整形後のテキスト（プレーンテキスト、見出し記号やMarkdownは付けない）
    """
    if not raw_text or not raw_text.strip():
        return ""

    client = _get_client()

    context_text = "\n".join(f"{k}: {v}" for k, v in context.items() if v)

    system_prompt = (
        "あなたは日本企業の出張報告書作成を支援するアシスタントです。"
        "ユーザーが入力した箇条書き・メモ書きを、上司にそのまま提出できる、"
        "である調のフォーマルなビジネス文書の文章に整形してください。"
        "\n\n制約:\n"
        "・出力は整形後の本文のみとし、前置きや説明、Markdown記号（##や**など）は一切付けない\n"
        "・メモに書かれていない事実を推測で付け加えない\n"
        "・簡潔さを保ちつつ、ビジネス文書として自然な日本語にする\n"
        f"・今回整形する項目は「{field_label}」です"
    )

    user_message = (
        (f"[出張の概要]\n{context_text}\n\n" if context_text else "")
        + f"[{field_label}のメモ]\n{raw_text}"
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.3,
        ),
    )

    return (response.text or "").strip()
