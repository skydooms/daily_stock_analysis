# 股票管理快速指南

## 🎯 快速开始

### 查看当前股票
```bash
python manage_stocks.py list
```

### 添加股票
```bash
# 添加单只
python manage_stocks.py add 600519

# 添加多只
python manage_stocks.py add 600519,002594,300750

# 添加港股
python manage_stocks.py add 03759.HK,09880.HK

# 添加美股
python manage_stocks.py add AAPL,TSLA,NVDA
```

### 移除股票
```bash
python manage_stocks.py remove AAPL,TSLA
```

---

## 📊 股票代码格式

| 市场 | 格式 | 示例 | 说明 |
|------|------|------|------|
| **A 股** | 6 位数字 | `600519` | 贵州茅台 |
| **A 股** | 6 位数字 | `002594` | 比亚迪 |
| **A 股** | 6 位数字 | `300750` | 宁德时代 |
| **港股** | 5-6 位 + .HK | `03759.HK` | 康龙化成 |
| **港股** | 5-6 位 + .HK | `09880.HK` | 优必选 |
| **港股** | 5-6 位 + .HK | `00700.HK` | 腾讯控股 |
| **美股** | 股票代码 | `AAPL` | 苹果 |
| **美股** | 股票代码 | `TSLA` | 特斯拉 |

---

## 📈 热门股票推荐

### A 股（10 只）
```bash
python manage_stocks.py add 600519,002594,300750,000858,601318,000333,600036,002415,300059,601888
```

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| 600519 | 贵州茅台 | 000858 | 五粮液 |
| 002594 | 比亚迪 | 300750 | 宁德时代 |
| 601318 | 中国平安 | 000333 | 美的集团 |
| 600036 | 招商银行 | 002415 | 海康威视 |
| 300059 | 东方财富 | 601888 | 中国中免 |

### 港股（10 只）
```bash
python manage_stocks.py add 03759.HK,09880.HK,02382.HK,00700.HK,09988.HK,03690.HK,01810.HK,00941.HK,01024.HK,09618.HK
```

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| 03759.HK | 康龙化成 | 09880.HK | 优必选 |
| 02382.HK | 舜宇光学科技 | 00700.HK | 腾讯控股 |
| 09988.HK | 阿里巴巴 | 03690.HK | 美团 |
| 01810.HK | 小米集团 | 00941.HK | 中国移动 |
| 01024.HK | 快手 | 09618.HK | 京东 |

### 美股（10 只）
```bash
python manage_stocks.py add AAPL,TSLA,NVDA,MSFT,GOOGL,AMZN,META,NFLX,AMD,INTC
```

| 代码 | 名称 | 代码 | 名称 |
|------|------|------|------|
| AAPL | 苹果 | TSLA | 特斯拉 |
| NVDA | 英伟达 | MSFT | 微软 |
| GOOGL | 谷歌 | AMZN | 亚马逊 |
| META | Meta | NFLX | 奈飞 |
| AMD | AMD | INTC | 英特尔 |

---

## 🔧 常用命令组合

### 清空并重新设置
```bash
# 清空所有
python manage_stocks.py clear

# 添加新股票
python manage_stocks.py add 600519,002594,300750
```

### 批量添加不同市场
```bash
# A 股
python manage_stocks.py add 600519,002594,300750

# 港股
python manage_stocks.py add 03759.HK,09880.HK,02382.HK

# 美股
python manage_stocks.py add AAPL,TSLA,NVDA
```

### 查看配置
```bash
# 查看.env 文件中的股票配置
grep STOCK_LIST .env
```

---

## ⚠️ 注意事项

1. **A 股代码必须是 6 位数字**
   - ✅ 正确：`002594`
   - ❌ 错误：`2594`

2. **港股必须加 .HK 后缀**
   - ✅ 正确：`03759.HK`
   - ❌ 错误：`03759`

3. **使用英文逗号分隔**
   - ✅ 正确：`600519,002594,300750`
   - ❌ 错误：`600519 002594 300750`

4. **修改后需要重启程序**
   ```bash
   # 如果使用 main.py
   python main.py
   
   # 如果使用批量回测
   python run_batch_backtest.py
   ```

---

## 📝 示例场景

### 场景 1：只关注 A 股
```bash
python manage_stocks.py clear
python manage_stocks.py add 600519,002594,300750,000858,601318
```

### 场景 2：A 股 + 港股
```bash
python manage_stocks.py clear
python manage_stocks.py add 600519,002594,300750,03759.HK,09880.HK,02382.HK
```

### 场景 3：全球配置
```bash
python manage_stocks.py clear
python manage_stocks.py add 600519,002594,300750,03759.HK,09880.HK,AAPL,TSLA,NVDA
```

### 场景 4：回测专用
```bash
python manage_stocks.py clear
python manage_stocks.py add 03759.HK,002821.SZ,09880.HK,300850.SZ,02382.HK
```

---

## 🆘 故障排除

### 问题 1：股票添加失败
```bash
# 检查.env 文件是否存在
ls .env

# 检查权限
chmod 644 .env
```

### 问题 2：股票代码错误
```bash
# 查看已添加的股票
python manage_stocks.py list

# 移除错误的股票
python manage_stocks.py remove 错误代码
```

### 问题 3：配置不生效
```bash
# 重启程序
# 如果正在运行，先 Ctrl+C 停止
python main.py
```

---

## 📚 相关文档

- [HOW_TO_ADD_STOCKS.md](HOW_TO_ADD_STOCKS.md) - 详细指南
- [.env.example](.env.example) - 配置示例
- [docs/FAQ.md](docs/FAQ.md) - 常见问题

---

**最后更新**: 2026-03-15
