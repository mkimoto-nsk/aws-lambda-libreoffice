import boto3
import os
import subprocess
from tempfile import NamedTemporaryFile
from io import BytesIO

s3 = boto3.client('s3')

def lambda_handler(event, context):
    # S3イベントからバケット名とファイル名を取得
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    object_key  = event['Records'][0]['s3']['object']['key']
    file_ext = object_key.split('.')[-1].lower()

    # 一時ファイルパス
    tmp_input  = f"/tmp/{os.path.basename(object_key)}"
    tmp_output = f"/tmp/{os.path.splitext(os.path.basename(object_key))[0]}.pdf"

    # S3からダウンロード
    s3.download_file(bucket_name, object_key, tmp_input)

    # OfficeファイルならLibreOfficeでPDF変換
    if file_ext in ["docx", "xlsx", "pptx"]:
        convert_office_to_pdf(tmp_input, tmp_output)
    elif file_ext == "pdf":
        tmp_output = tmp_input  # 既存PDFはそのまま
    else:
        convert_plain_txt_to_pdf(tmp_input, tmp_output)

    # 変換後ファイルをS3にアップロード
    pdf_key = f"afterConverted/{os.path.splitext(os.path.basename(object_key))[0]}.pdf"
    with open(tmp_output, "rb") as f:
        s3.put_object(Bucket=bucket_name, Key=pdf_key, Body=f.read())

    return {
        "statusCode": 200,
        "body": f"{object_key} を {pdf_key} に変換しました"
    }


# ------------------- 変換系 -------------------

def convert_office_to_pdf(input_path, output_path):
    """
    LibreOfficeを呼び出してOfficeファイルをPDFに変換
    """
    cmd = [
        "libreoffice",
        "--headless",
        "--convert-to", "pdf",
        "--outdir", os.path.dirname(output_path),
        input_path
    ]
    subprocess.run(cmd, check=True)


def convert_plain_txt_to_pdf(input_path, output_path):
    """
    txt/csv/htmlなどプレーンテキストをPDFに変換
    """
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    y = height - 40
    for line in lines:
        c.drawString(40, y, line.strip())
        y -= 15
        if y < 40:
            c.showPage()
            y = height - 40
    c.save()
