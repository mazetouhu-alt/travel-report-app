"""
出張報告書PDF生成モジュール（fpdf2使用）

【重要】fpdf2の標準フォントは日本語に対応していないため、
Unicode対応フォント（Noto Sans JP等）をTTFファイルとして
assets/fonts/ に配置してから使用してください。
配置手順は README.md を参照。
"""
import os

from fpdf import FPDF

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "NotoSansJP-Regular.ttf")
FONT_BOLD = os.path.join(FONT_DIR, "NotoSansJP-Bold.ttf")


class ReportPDF(FPDF):
    def header(self):
        pass  # 独自にタイトルを描画するため、共通ヘッダーは使わない

    def footer(self):
        self.set_y(-15)
        self.set_font("NotoSansJP", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"{self.page_no()}", align="C")


def _register_fonts(pdf: ReportPDF):
    if not os.path.exists(FONT_REGULAR):
        raise FileNotFoundError(
            "日本語フォントが見つかりません。\n"
            f"'{FONT_REGULAR}' に NotoSansJP-Regular.ttf を配置してください。"
            "（README.mdのPDFフォント設定の手順を参照）"
        )
    pdf.add_font("NotoSansJP", "", FONT_REGULAR)
    if os.path.exists(FONT_BOLD):
        pdf.add_font("NotoSansJP", "B", FONT_BOLD)
    else:
        # Boldファイルが無い場合はRegularで代用（見た目は太字にならない）
        pdf.add_font("NotoSansJP", "B", FONT_REGULAR)


def _section_title(pdf: ReportPDF, text: str):
    pdf.set_font("NotoSansJP", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    pdf.ln(3)


def _body_text(pdf: ReportPDF, text: str):
    pdf.set_font("NotoSansJP", "", 10.5)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 6.5, text if text else "（未入力）")
    pdf.ln(2)


def generate_pdf(data: dict) -> bytes:
    """
    出張報告書データからPDFを生成し、バイト列で返す。

    Args:
        data: {
            "period": str, "staff": str, "location": str, "destination": str,
            "accommodation": str, "purpose": str, "activity": str
        }
    Returns:
        PDFファイルのバイト列（st.download_button にそのまま渡せる）
    """
    pdf = ReportPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    _register_fonts(pdf)

    # タイトル
    pdf.set_font("NotoSansJP", "B", 20)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 14, "出張報告書", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # 基本情報テーブル
    info_rows = [
        ("期間", data.get("period", "")),
        ("担当者", data.get("staff", "")),
        ("場所", data.get("location", "")),
        ("訪問先", data.get("destination", "")),
        ("宿泊有無", data.get("accommodation", "")),
    ]
    label_w = 32
    value_w = 190 - label_w
    for label, value in info_rows:
        pdf.set_font("NotoSansJP", "B", 10.5)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(label_w, 8, label, border=1, fill=True)
        pdf.set_font("NotoSansJP", "", 10.5)
        pdf.cell(value_w, 8, value or "-", border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # 目的
    _section_title(pdf, "目的")
    _body_text(pdf, data.get("purpose", ""))
    pdf.ln(2)

    # 具体的な活動内容・成果
    _section_title(pdf, "具体的な活動内容・成果")
    _body_text(pdf, data.get("activity", ""))

    return bytes(pdf.output())
