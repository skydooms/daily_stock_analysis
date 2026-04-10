#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据文件格式
"""

import zipfile
import pandas as pd
from pathlib import Path


def main():
    """检查数据格式"""
    zip_file = Path(r'd:\project\data\A股分时数据\A股_分时数据_沪深\1分钟_按月归档\2025-01\20250102_1min.zip')
    
    if not zip_file.exists():
        print(f"文件不存在: {zip_file}")
        return
    
    print(f"检查文件: {zip_file}\n")
    
    with zipfile.ZipFile(zip_file, 'r') as zf:
        file_list = zf.namelist()
        print(f"Zip文件包含 {len(file_list)} 个文件")
        
        if file_list:
            print(f"\n第一个文件: {file_list[0]}")
            
            with zf.open(file_list[0]) as f:
                df = pd.read_csv(f, nrows=5)
                print("\n数据前5行:")
                print(df)
                print("\n列名:")
                print(df.columns.tolist())


if __name__ == '__main__':
    main()
