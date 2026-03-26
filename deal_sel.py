import pandas as pd

def parse_ths_cel(file_path):
    """
    解析同花顺自选股导出的 .cel 文件
    返回：股票代码、名称、市场（沪/深/北等）
    """
    stock_list = []

    with open(file_path, "r", encoding="gbk", errors="ignore") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or len(line) < 10:
            continue

        # 同花顺 cel 格式：每行用 | 分隔
        parts = line.split("|")
        if len(parts) < 4:
            continue

        # 字段：市场代码 | 股票代码 | 股票名称 | ...
        market_code = parts[0]
        stock_code = parts[1]
        stock_name = parts[2]

        # 识别市场
        market = ""
        if market_code == "1":
            market = "沪市"
        elif market_code == "2":
            market = "深市"
        elif market_code == "3":
            market = "北交所"
        elif market_code == "6":
            market = "港股"
        elif market_code == "10":
            market = "美股"
        else:
            market = f"其他({market_code})"

        stock_list.append({
            "代码": stock_code,
            "名称": stock_name,
            "市场": market
        })

    return stock_list

# ====================== 使用示例 ======================
if __name__ == "__main__":
    # 1. 替换成你的 .cel 文件路径
    cel_file = r"C:\Users\Administrator\Desktop\科技港股.sel"
    # 2. 解析
    stocks = parse_ths_cel(cel_file)

    # 3. 转成 DataFrame（方便查看/导出）
    df = pd.DataFrame(stocks)

    # 打印查看
    print(df)

    # 4. 导出为 Excel（推荐）
    df.to_excel("同花顺自选股解析结果.xlsx", index=False)

    # 导出为 CSV
    # df.to_csv("同花顺自选股.csv", index=False, encoding="utf-8-sig")