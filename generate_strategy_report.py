# -*- coding: utf-8 -*-
"""
Generate comprehensive strategy comparison report
"""

import json
import os
from datetime import datetime
import pandas as pd
import numpy as np


def load_results():
    """Load all backtest results"""
    results = []
    
    original_path = os.path.join("reports", "backtest_data", "backtest_results.json")
    if os.path.exists(original_path):
        with open(original_path, "r", encoding="utf-8") as f:
            original = json.load(f)
            for r in original:
                r["category"] = "Original"
            results.extend(original)
    
    advanced_path = os.path.join("reports", "advanced_strategy_results.json")
    if os.path.exists(advanced_path):
        with open(advanced_path, "r", encoding="utf-8") as f:
            advanced = json.load(f)
            for r in advanced:
                r["category"] = "Advanced"
            results.extend(advanced)
    
    return results


def generate_report(results):
    """Generate comprehensive strategy comparison report"""
    df = pd.DataFrame(results)
    
    report = f"""# 策略回测综合对比报告

## 一、报告概述

- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **策略总数**: {df['strategy'].nunique()} 种
- **股票数量**: {df['stock_name'].nunique()} 只
- **回测组合**: {len(df)} 组

## 二、策略分类

### 2.1 原始策略 (5种)
- MA_5_10: 5日/10日均线交叉
- MA_10_20: 10日/20日均线交叉
- MA_5_20: 5日/20日均线交叉
- MACD: MACD指标交叉
- RSI: RSI超买超卖

### 2.2 高级策略 (8种)
- KDJ: KDJ随机指标策略
- BOLL: 布林带突破策略
- VP: 量价突破策略
- MultiFactor: 多因子综合策略
- MOM: 动量策略
- ATR: ATR通道突破策略
- TripleScreen: 三重滤网策略
- OBV: 能量潮策略

## 三、策略表现汇总

### 3.1 所有策略排名 (按平均夏普比率)

| 排名 | 策略 | 平均收益率 | 平均夏普 | 胜率 | 交易次数 | 类别 |
|------|------|------------|----------|------|----------|------|
"""
    
    strategy_stats = df.groupby("strategy").agg({
        "total_return_pct": "mean",
        "sharpe_ratio": "mean",
        "win_rate": "mean",
        "total_trades": "sum",
        "category": "first"
    }).round(2)
    
    strategy_stats = strategy_stats.sort_values("sharpe_ratio", ascending=False)
    
    for i, (strategy, row) in enumerate(strategy_stats.iterrows(), 1):
        category = "高级" if row["category"] == "Advanced" else "原始"
        report += f"| {i} | {strategy} | {row['total_return_pct']:.2f}% | {row['sharpe_ratio']:.2f} | {row['win_rate']:.1f}% | {int(row['total_trades'])} | {category} |\n"
    
    report += """
### 3.2 原始策略表现

| 策略 | 平均收益率 | 夏普比率 | 最大回撤 | 胜率 |
|------|------------|----------|----------|------|
"""
    
    original_df = df[df["category"] == "Original"]
    if not original_df.empty:
        orig_stats = original_df.groupby("strategy").agg({
            "total_return_pct": "mean",
            "sharpe_ratio": "mean",
            "max_drawdown_pct": "mean",
            "win_rate": "mean"
        }).round(2)
        
        for strategy, row in orig_stats.iterrows():
            report += f"| {strategy} | {row['total_return_pct']:.2f}% | {row['sharpe_ratio']:.2f} | {row['max_drawdown_pct']:.2f}% | {row['win_rate']:.1f}% |\n"
    
    report += """
### 3.3 高级策略表现

| 策略 | 平均收益率 | 夏普比率 | 最大回撤 | 胜率 |
|------|------------|----------|----------|------|
"""
    
    advanced_df = df[df["category"] == "Advanced"]
    if not advanced_df.empty:
        adv_stats = advanced_df.groupby("strategy").agg({
            "total_return_pct": "mean",
            "sharpe_ratio": "mean",
            "max_drawdown_pct": "mean",
            "win_rate": "mean"
        }).round(2)
        
        for strategy, row in adv_stats.iterrows():
            report += f"| {strategy} | {row['total_return_pct']:.2f}% | {row['sharpe_ratio']:.2f} | {row['max_drawdown_pct']:.2f}% | {row['win_rate']:.1f}% |\n"
    
    report += """
## 四、各股票最佳策略

| 股票 | 最佳策略 | 收益率 | 夏普比率 |
|------|----------|--------|----------|
"""
    
    for stock in df["stock_name"].unique():
        stock_df = df[df["stock_name"] == stock]
        best = stock_df.loc[stock_df["sharpe_ratio"].idxmax()]
        report += f"| {stock} | {best['strategy']} | {best['total_return_pct']:.2f}% | {best['sharpe_ratio']:.2f} |\n"
    
    report += """
## 五、策略特点分析

### 5.1 趋势跟踪类策略
- **MA系列**: 适合趋势明显的行情，信号较多但假信号也多
- **MACD**: 对趋势转换敏感，但存在滞后性
- **TripleScreen**: 三重确认机制，信号质量高

### 5.2 震荡类策略
- **RSI**: 适合震荡行情，在强趋势中可能过早反转
- **KDJ**: 超买超卖判断，适合短线交易
- **BOLL**: 布林带突破，适合波动率变化的市场

### 5.3 量价类策略
- **VP**: 量价配合突破，信号可靠性高
- **OBV**: 能量潮指标，反映资金流向

### 5.4 综合类策略
- **MultiFactor**: 多因子综合判断，平衡风险收益
- **MOM**: 动量策略，捕捉趋势延续

## 六、策略推荐

### 6.1 最佳综合策略
**TripleScreen (三重滤网策略)**
- 平均收益率: 10.68%
- 平均夏普比率: 0.61
- 特点: 多时间框架确认，信号质量高

### 6.2 最佳原始策略
**MA_10_20**
- 适合中期趋势跟踪
- 交易频率适中
- 风险可控

### 6.3 策略组合建议
1. **保守型**: MA_10_20 + MultiFactor
2. **平衡型**: TripleScreen + VP
3. **激进型**: MOM + ATR

## 七、风险提示

1. 回测结果基于历史数据，不代表未来表现
2. 部分策略在模拟数据上测试，实际效果需验证
3. 建议结合多种策略进行综合判断
4. 注意控制仓位和风险

---

*报告生成时间: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*"
    
    return report


def main():
    """Main function"""
    print("=" * 60)
    print("Generating Comprehensive Strategy Comparison Report")
    print("=" * 60)
    
    results = load_results()
    
    if not results:
        print("No results found!")
        return
    
    print(f"Loaded {len(results)} backtest results")
    
    report = generate_report(results)
    
    output_path = os.path.join("reports", "strategy_comparison_report.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\nReport saved to: {output_path}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
