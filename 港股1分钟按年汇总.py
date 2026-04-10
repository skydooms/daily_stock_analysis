import os
import re
import zipfile
import pandas as pd
import logging
from collections import defaultdict
from tqdm import tqdm

SOURCE_DIR = "/media/sky/Data/stock/港股_分时数据/1分钟_按月归档"
OUTPUT_DIR = "/media/sky/Data/stock/港股_分时数据/1分钟_按年汇总_tmp"
FINAL_DIR = "/media/sky/Data/stock/港股_分时数据/1分钟_按年汇总"

FILENAME_PATTERN = re.compile(r"(\d{8})_1min\.zip")
CHUNK_SIZE = 50_000
ENCODING = "utf-8-sig"
CLEAN_TMP = True

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_zip_files():
    zip_files = []
    for root, _, files in os.walk(SOURCE_DIR):
        for f in files:
            if FILENAME_PATTERN.match(f):
                zip_files.append(os.path.join(root, f))
    return zip_files


def process_zip(zip_path):
    logger.info(f"开始处理 ZIP: {zip_path}")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        csv_files = [m for m in zf.namelist() if m.endswith(".csv")]

        for member in tqdm(csv_files, desc="CSV 文件", leave=False):
            stock_code = os.path.basename(member).replace(".csv", "")

            with zf.open(member) as f:
                for chunk in pd.read_csv(
                        f,
                        chunksize=CHUNK_SIZE,
                        parse_dates=["时间"]
                ):
                    chunk["year"] = chunk["时间"].dt.year

                    for year, group in chunk.groupby("year"):
                        year_dir = os.path.join(OUTPUT_DIR, str(year))
                        os.makedirs(year_dir, exist_ok=True)

                        out_file = os.path.join(year_dir, f"{stock_code}_{year}.csv")

                        group.drop(columns="year").to_csv(
                            out_file,
                            mode="a",
                            header=not os.path.exists(out_file),
                            index=False,
                            encoding=ENCODING
                        )


def pack_by_year():
    os.makedirs(FINAL_DIR, exist_ok=True)

    for year in tqdm(os.listdir(OUTPUT_DIR), desc="年度打包", unit="year"):
        year_dir = os.path.join(OUTPUT_DIR, year)
        zip_path = os.path.join(FINAL_DIR, f"{year}_1min.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in os.listdir(year_dir):
                file_path = os.path.join(year_dir, file)
                zf.write(file_path, arcname=file)

        logger.info(f"生成年度 ZIP: {zip_path}")


def main():
    zip_files = collect_zip_files()
    logger.info(f"发现 ZIP 文件 {len(zip_files)} 个")

    for zip_path in tqdm(zip_files, desc="处理 ZIP", unit="zip"):
        process_zip(zip_path)

    pack_by_year()

    if CLEAN_TMP:
        import shutil
        shutil.rmtree(OUTPUT_DIR)
        logger.info("清理临时目录完成")


if __name__ == "__main__":
    main()
