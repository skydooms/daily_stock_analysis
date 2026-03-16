# -*- coding: utf-8 -*-
"""
Generate visualization charts for batch backtest results
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def load_backtest_results():
    """Load backtest results from JSON file"""
    data_path = os.path.join("reports", "backtest_data", "backtest_results.json")
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return None
    
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_strategy_comparison(results, output_dir):
    """Plot strategy comparison bar chart"""
    strategies = {}
    for r in results:
        strategy = r["strategy"]
        if strategy not in strategies:
            strategies[strategy] = {"returns": [], "sharpe": []}
        strategies[strategy]["returns"].append(r["total_return_pct"])
        strategies[strategy]["sharpe"].append(r["sharpe_ratio"])
    
    strategy_names = list(strategies.keys())
    avg_returns = [np.mean(strategies[s]["returns"]) for s in strategy_names]
    avg_sharpe = [np.mean(strategies[s]["sharpe"]) for s in strategy_names]
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    colors = ['#2ecc71' if r >= 0 else '#e74c3c' for r in avg_returns]
    bars1 = axes[0].bar(strategy_names, avg_returns, color=colors, edgecolor='black', linewidth=0.5)
    axes[0].set_title('Average Return by Strategy (%)', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Strategy')
    axes[0].set_ylabel('Return (%)')
    axes[0].axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    axes[0].grid(axis='y', alpha=0.3)
    
    for bar, val in zip(bars1, avg_returns):
        height = bar.get_height()
        axes[0].annotate(f'{val:.2f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3 if height >= 0 else -12),
                        textcoords="offset points",
                        ha='center', va='bottom' if height >= 0 else 'top',
                        fontsize=9)
    
    colors2 = ['#3498db' if s >= 0 else '#e74c3c' for s in avg_sharpe]
    bars2 = axes[1].bar(strategy_names, avg_sharpe, color=colors2, edgecolor='black', linewidth=0.5)
    axes[1].set_title('Average Sharpe Ratio by Strategy', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Strategy')
    axes[1].set_ylabel('Sharpe Ratio')
    axes[1].axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    axes[1].grid(axis='y', alpha=0.3)
    
    for bar, val in zip(bars2, avg_sharpe):
        height = bar.get_height()
        axes[1].annotate(f'{val:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3 if height >= 0 else -12),
                        textcoords="offset points",
                        ha='center', va='bottom' if height >= 0 else 'top',
                        fontsize=9)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, "strategy_comparison.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def plot_stock_performance(results, output_dir):
    """Plot stock performance heatmap"""
    stocks = list(set(r["stock_name"] for r in results))
    strategies = list(set(r["strategy"] for r in results))
    
    returns_matrix = np.zeros((len(stocks), len(strategies)))
    
    for r in results:
        stock_idx = stocks.index(r["stock_name"])
        strategy_idx = strategies.index(r["strategy"])
        returns_matrix[stock_idx, strategy_idx] = r["total_return_pct"]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    im = ax.imshow(returns_matrix, cmap='RdYlGn', aspect='auto', vmin=-25, vmax=10)
    
    ax.set_xticks(np.arange(len(strategies)))
    ax.set_yticks(np.arange(len(stocks)))
    ax.set_xticklabels(strategies)
    ax.set_yticklabels(stocks)
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    
    for i in range(len(stocks)):
        for j in range(len(strategies)):
            text = ax.text(j, i, f'{returns_matrix[i, j]:.1f}%',
                          ha="center", va="center", color="black", fontsize=8)
    
    ax.set_title('Return Rate Heatmap by Stock and Strategy (%)', fontsize=12, fontweight='bold')
    fig.colorbar(im, ax=ax, label='Return (%)')
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, "stock_performance_heatmap.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def plot_risk_return(results, output_dir):
    """Plot risk-return scatter plot"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    strategy_colors = {
        'MA_5_10': '#3498db',
        'MA_10_20': '#2ecc71',
        'MA_5_20': '#9b59b6',
        'MACD': '#e74c3c',
        'RSI': '#f39c12',
    }
    
    for r in results:
        color = strategy_colors.get(r["strategy"], '#95a5a6')
        ax.scatter(r["max_drawdown_pct"], r["total_return_pct"], 
                  c=color, s=100, alpha=0.7, edgecolors='black', linewidth=0.5,
                  label=r["strategy"])
    
    handles = []
    labels_seen = set()
    for strategy, color in strategy_colors.items():
        if strategy not in labels_seen:
            handles.append(plt.scatter([], [], c=color, s=100, label=strategy))
            labels_seen.add(strategy)
    
    ax.legend(handles, strategy_colors.keys(), loc='upper right')
    
    ax.set_xlabel('Max Drawdown (%)', fontsize=11)
    ax.set_ylabel('Return (%)', fontsize=11)
    ax.set_title('Risk-Return Profile by Strategy', fontsize=12, fontweight='bold')
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, "risk_return_scatter.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def plot_win_rate(results, output_dir):
    """Plot win rate comparison"""
    strategies = {}
    for r in results:
        strategy = r["strategy"]
        if strategy not in strategies:
            strategies[strategy] = {"win_rates": [], "trades": []}
        strategies[strategy]["win_rates"].append(r["win_rate"])
        strategies[strategy]["trades"].append(r["total_trades"])
    
    strategy_names = list(strategies.keys())
    avg_win_rates = [np.mean(strategies[s]["win_rates"]) for s in strategy_names]
    total_trades = [sum(strategies[s]["trades"]) for s in strategy_names]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(strategy_names))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, avg_win_rates, width, label='Win Rate (%)', color='#3498db', edgecolor='black')
    
    ax2 = ax.twinx()
    bars2 = ax2.bar(x + width/2, total_trades, width, label='Total Trades', color='#e74c3c', edgecolor='black')
    
    ax.set_xlabel('Strategy', fontsize=11)
    ax.set_ylabel('Win Rate (%)', color='#3498db', fontsize=11)
    ax2.set_ylabel('Total Trades', color='#e74c3c', fontsize=11)
    ax.set_title('Win Rate and Trade Count by Strategy', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(strategy_names)
    
    for bar, val in zip(bars1, avg_win_rates):
        height = bar.get_height()
        ax.annotate(f'{val:.1f}%',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),
                   textcoords="offset points",
                   ha='center', va='bottom', fontsize=8)
    
    for bar, val in zip(bars2, total_trades):
        height = bar.get_height()
        ax2.annotate(f'{val}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)
    
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = os.path.join(output_dir, "win_rate_comparison.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")


def main():
    """Main function"""
    print("=" * 50)
    print("Generating Backtest Visualization Charts")
    print("=" * 50)
    
    results = load_backtest_results()
    if not results:
        print("No results to visualize")
        return
    
    output_dir = os.path.join("reports", "charts")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nLoaded {len(results)} backtest results")
    print(f"Output directory: {output_dir}\n")
    
    plot_strategy_comparison(results, output_dir)
    plot_stock_performance(results, output_dir)
    plot_risk_return(results, output_dir)
    plot_win_rate(results, output_dir)
    
    print("\n" + "=" * 50)
    print("Chart generation completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
