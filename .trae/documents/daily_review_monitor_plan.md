# 每日复盘与持仓监测系统开发计划

## 一、需求概述

开发一个多时间点的股票监测系统，包含三个核心模块：
- **晨间复盘模块**（每日7:00）：美股市场分析、A股/港股新闻、持仓价格区间分析
- **午间监测模块**（每日12:00）：关注股票技术指标监测
- **晚间监测模块**（每日19:00）：持仓股票深度技术分析

## 二、现有能力分析

### 2.1 已有能力（可复用）

| 模块 | 文件路径 | 说明 |
|------|----------|------|
| 数据获取 | `data_provider/` | AkShare、yfinance、PyTDX、Tushare、Baostock |
| 技术分析 | `src/stock_analyzer.py` | MA、MACD、RSI、趋势判断、量能分析 |
| 市场复盘 | `src/core/market_review.py` | A股/美股大盘复盘 |
| 调度系统 | `src/scheduler.py` | 定时任务调度（单时间点） |
| 持仓管理 | `src/services/portfolio_service.py` | 持仓、交易记录管理 |
| 报告生成 | `src/services/report_renderer.py` | Jinja2模板渲染 |
| 通知服务 | `src/notification_sender/` | 企业微信、飞书、Telegram、邮件等 |

### 2.2 需要新增的能力

1. **多时间点调度**：扩展调度器支持7:00、12:00、19:00三个时间点
2. **美股指数数据**：道琼斯、纳斯达克指数获取
3. **板块涨跌分析**：美股板块涨跌排名
4. **价格区间分析**：3个月/1个月价格区间计算、预警价格计算
5. **KDJ指标**：新增KDJ技术指标计算
6. **背离检测**：顶背离/底背离形态识别
7. **60/120分钟分析**：分钟级别技术指标分析
8. **综合评分系统**：技术指标综合评分与操作建议

## 三、技术方案

### 3.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    调度管理器 (SchedulerManager)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ 7:00 AM  │  │ 12:00 PM │  │ 19:00 PM │                   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                   │
└───────┼─────────────┼─────────────┼─────────────────────────┘
        │             │             │
        ▼             ▼             ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ 晨间复盘模块  │ │ 午间监测模块  │ │ 晚间监测模块  │
│ MorningReview │ │ NoonMonitor   │ │ EveningMonitor│
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                      核心服务层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ USMarketData │  │ PriceRange   │  │ Technical    │      │
│  │ Service      │  │ Analyzer     │  │ Monitor      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ NewsService  │  │ KDJCalculator│  │ Divergence   │      │
│  │              │  │              │  │ Detector     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据层 & 报告生成                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ DataProvider │  │ ReportRender │  │ Notification │      │
│  │ (已有)       │  │ (扩展)       │  │ (已有)       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 新增文件清单

#### 3.2.1 核心服务模块

| 文件路径 | 职责 |
|----------|------|
| `src/services/morning_review.py` | 晨间复盘服务（美股指数、新闻、价格区间） |
| `src/services/noon_monitor.py` | 午间监测服务（技术指标监测） |
| `src/services/evening_monitor.py` | 晚间监测服务（深度技术分析） |
| `src/services/price_range_analyzer.py` | 价格区间分析服务 |
| `src/services/technical_monitor.py` | 技术指标监测服务（KDJ、背离检测） |
| `src/services/us_market_service.py` | 美股市场数据服务（指数、板块） |
| `src/scheduler_manager.py` | 多时间点调度管理器 |

#### 3.2.2 报告模板

| 文件路径 | 职责 |
|----------|------|
| `templates/report_morning.j2` | 晨间复盘报告模板 |
| `templates/report_noon.j2` | 午间监测报告模板 |
| `templates/report_evening.j2` | 晚间监测报告模板 |

### 3.3 修改文件清单

| 文件路径 | 修改内容 |
|----------|----------|
| `src/config.py` | 新增配置项（时间点、股票列表等） |
| `src/stock_analyzer.py` | 新增KDJ指标计算方法 |
| `main.py` | 增加新模块入口参数 |
| `.env.example` | 新增配置项说明 |

## 四、详细实现方案

### 4.1 晨间复盘模块 (Morning Review)

#### 4.1.1 美股市场分析

**数据来源**：
- 道琼斯指数：`^DJI` (yfinance)
- 纳斯达克指数：`^IXIC` (yfinance)
- 板块数据：yfinance sector ETFs (XLK, XLF, XLE, etc.)

**实现逻辑**：
```python
class USMarketService:
    def get_index_data(self) -> Dict:
        """获取道琼斯、纳斯达克指数数据"""
        
    def get_sector_rankings(self) -> List[Dict]:
        """获取板块涨跌排名"""
        
    def generate_sector_chart(self) -> str:
        """生成板块涨跌分布图表（Base64图片）"""
```

#### 4.1.2 A股/港股市场动态

**数据来源**：
- 新闻搜索：复用现有 `SearchService`
- 政策信息：Tavily/SerpAPI 搜索

**实现逻辑**：
```python
class NewsService:
    def fetch_overnight_news(self, hours: int = 12) -> List[Dict]:
        """获取夜间至早间新闻"""
        
    def categorize_by_sector(self, news: List[Dict]) -> Dict[str, List]:
        """按板块分类新闻"""
        
    def mark_portfolio_related(self, news: List[Dict], portfolio: List[str]) -> List[Dict]:
        """标记持仓相关新闻"""
```

#### 4.1.3 持仓股票价格区间分析

**计算逻辑**：
```python
class PriceRangeAnalyzer:
    def analyze_price_range(
        self, 
        code: str, 
        days: int = 90
    ) -> PriceRangeResult:
        """
        计算价格区间数据：
        - 绝对最低点（最低价）、出现日期
        - 绝对最高点（最高价）、出现日期
        - 收盘最低点、出现日期
        - 收盘最高点、出现日期
        - 各关键点至今涨跌幅
        """
        
    def calculate_warning_prices(
        self, 
        low_price: float
    ) -> Dict[str, float]:
        """
        计算预警价格：
        - 上涨20%价格
        - 上涨30%价格
        - 上涨40%价格
        """
        
    def get_current_position(
        self, 
        current_price: float,
        low_price: float,
        high_price: float
    ) -> str:
        """判断当前价格在区间中的位置"""
```

### 4.2 午间监测模块 (Noon Monitor)

#### 4.2.1 技术指标监测

**新增KDJ指标**：
```python
def calculate_kdj(
    df: pd.DataFrame, 
    n: int = 9, 
    m1: int = 3, 
    m2: int = 3
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    计算KDJ指标
    RSV = (Close - LowN) / (HighN - LowN) * 100
    K = SMA(RSV, M1)
    D = SMA(K, M2)
    J = 3K - 2D
    """
```

**背离检测**：
```python
class DivergenceDetector:
    def detect_top_divergence(
        self, 
        prices: pd.Series, 
        indicator: pd.Series
    ) -> Optional[DivergenceResult]:
        """检测顶背离：价格创新高，指标未创新高"""
        
    def detect_bottom_divergence(
        self, 
        prices: pd.Series, 
        indicator: pd.Series
    ) -> Optional[DivergenceResult]:
        """检测底背离：价格创新低，指标未创新低"""
        
    def calculate_strength(self, divergence: DivergenceResult) -> float:
        """计算背离强度（0-100）"""
```

**60/120分钟分析**：
```python
class TechnicalMonitor:
    def analyze_intraday(
        self, 
        code: str, 
        interval: int = 60
    ) -> IntradayAnalysisResult:
        """
        分钟级别技术分析：
        - 均线系统状态
        - MACD状态
        - KDJ状态
        - 背离检测
        """
        
    def generate_score(self, result: IntradayAnalysisResult) -> int:
        """生成综合评分（0-100）"""
        
    def generate_advice(self, score: int) -> str:
        """生成操作建议"""
```

### 4.3 晚间监测模块 (Evening Monitor)

#### 4.3.1 深度技术分析

在午间监测基础上增加：
- 收盘后完整数据分析
- 支撑位/压力位识别
- 背离确认与风险评级
- 成交量验证
- 持仓策略建议

```python
class EveningMonitor:
    def deep_analysis(self, code: str) -> DeepAnalysisResult:
        """
        深度技术分析：
        - 完整技术指标
        - 支撑压力位
        - 背离确认
        - 成交量验证
        - 风险评级
        """
        
    def generate_strategy_advice(
        self, 
        result: DeepAnalysisResult,
        position: Optional[Position]
    ) -> str:
        """生成持仓策略建议"""
```

### 4.4 多时间点调度

```python
class SchedulerManager:
    def __init__(self):
        self.schedulers = {
            'morning': Scheduler(schedule_time='07:00'),
            'noon': Scheduler(schedule_time='12:00'),
            'evening': Scheduler(schedule_time='19:00'),
        }
        
    def setup_tasks(self, config: Config):
        """配置各时间点任务"""
        
    def run(self):
        """运行调度器"""
```

## 五、配置项设计

### 5.1 新增环境变量

```bash
# 调度时间配置
MORNING_REVIEW_TIME=07:00
NOON_MONITOR_TIME=12:00
EVENING_MONITOR_TIME=19:00

# 功能开关
ENABLE_MORNING_REVIEW=true
ENABLE_NOON_MONITOR=true
ENABLE_EVENING_MONITOR=true

# 关注股票列表（午间监测用）
WATCH_LIST=600519,300750,000001

# 持仓股票列表（从Portfolio服务获取或手动配置）
# PORTFOLIO_STOCKS=600519,300750

# 价格区间分析周期
PRICE_RANGE_PERIODS=30,90  # 1个月、3个月

# 预警阈值
PRICE_WARNING_LEVELS=20,30,40  # 上涨20%、30%、40%

# KDJ参数
KDJ_N=9
KDJ_M1=3
KDJ_M2=3

# 背离检测参数
DIVERGENCE_LOOKBACK=20  # 回溯周期
```

## 六、报告格式设计

### 6.1 晨间复盘报告

```markdown
# 🌅 晨间复盘报告 - {date}

## 📊 美股市场分析

### 主要指数
- 道琼斯工业平均指数: {price} ({change}%)
- 纳斯达克综合指数: {price} ({change}%)

### 板块表现
| 板块 | 涨跌幅 | 驱动方向 |
|------|--------|----------|
| ... | ... | ... |

![板块分布图]

## 📰 A股/港股市场动态

### 重要新闻
#### 科技板块
- [新闻标题](链接) - 🔴影响持仓

#### 金融板块
- [新闻标题](链接)

## 💰 持仓股票价格区间分析

### {股票名称} ({代码})

#### 近3个月价格区间（{start_date}至今，共{days}天）
| 指标 | 价格 | 日期 | 至今涨跌幅 |
|------|------|------|------------|
| 绝对最低点 | {low} | {date} | {change}% |
| 绝对最高点 | {high} | {date} | {change}% |
| 收盘最低点 | {close_low} | {date} | {change}% |
| 收盘最高点 | {close_high} | {date} | {change}% |

#### 价格预警
- 当前价格: {current}
- ⚠️ 较最低点上涨20%: {price_20}
- ⚠️ 较最低点上涨30%: {price_30}
- ⚠️ 较最低点上涨40%: {price_40}
- 📍 当前位置: {position}

#### 近1个月价格区间
...
```

### 6.2 午间监测报告

```markdown
# ☀️ 午间监测报告 - {date} 12:00

## 📈 关注股票技术指标监测

### {股票名称} ({代码})

#### 均线系统（60分钟）
- MA5: {ma5} | MA10: {ma10} | MA20: {ma20}
- 状态: {status} (多头/空头/盘整)

#### MACD指标
- DIF: {dif} | DEA: {dea} | MACD: {macd}
- 信号: {signal} (金叉/死叉/多头/空头)

#### KDJ指标
- K: {k} | D: {d} | J: {j}
- 状态: {status} (超买/超卖/中性)

#### 背离检测
- 顶背离: {top_divergence} (强度: {strength})
- 底背离: {bottom_divergence} (强度: {strength})

#### 综合评分
- 评分: {score}/100
- 操作建议: {advice}

---
生成时间: {timestamp}
```

### 6.3 晚间监测报告

```markdown
# 🌙 晚间监测报告 - {date} 19:00

## 📊 关注股票技术指标监测
[同午间监测内容]

## 🔬 持仓股票深度技术分析

### {股票名称} ({代码})

#### 均线系统详细分析
- 支撑位: {support_levels}
- 压力位: {resistance_levels}
- 趋势强度: {trend_strength}

#### MACD详细解读
- 背离形成过程: {divergence_process}
- 确认程度: {confirmation_level}

#### KDJ详细解读
- 钝化状态: {blunting_status}
- 修正可能性: {correction_probability}

#### 背离信号确认
- 顶背离: {confirmed} | 风险等级: {risk_level}
- 底背离: {confirmed} | 风险等级: {risk_level}

#### 成交量验证
- 量价关系: {volume_price_relation}
- 有效性: {validity}

#### 风险评级与持仓策略
- 技术面风险评级: {risk_rating} (高/中/低)
- 持仓策略建议: {strategy_advice}

---
生成时间: {timestamp}
```

## 七、实施步骤

### 阶段一：基础设施（1-2天）

1. **扩展调度系统**
   - 修改 `src/scheduler.py` 支持多时间点
   - 创建 `src/scheduler_manager.py`

2. **新增配置项**
   - 修改 `src/config.py`
   - 更新 `.env.example`

### 阶段二：晨间复盘模块（2-3天）

1. **美股市场服务**
   - 创建 `src/services/us_market_service.py`
   - 实现指数数据获取
   - 实现板块排名分析

2. **价格区间分析**
   - 创建 `src/services/price_range_analyzer.py`
   - 实现价格区间计算
   - 实现预警价格计算

3. **晨间复盘服务**
   - 创建 `src/services/morning_review.py`
   - 整合各子模块
   - 创建报告模板

### 阶段三：技术指标增强（1-2天）

1. **KDJ指标**
   - 在 `src/stock_analyzer.py` 新增KDJ计算

2. **背离检测**
   - 创建 `src/services/divergence_detector.py`
   - 实现顶背离/底背离检测

### 阶段四：午间/晚间监测模块（2-3天）

1. **技术监测服务**
   - 创建 `src/services/technical_monitor.py`
   - 实现60/120分钟分析

2. **午间监测服务**
   - 创建 `src/services/noon_monitor.py`
   - 创建报告模板

3. **晚间监测服务**
   - 创建 `src/services/evening_monitor.py`
   - 实现深度分析
   - 创建报告模板

### 阶段五：集成与测试（1-2天）

1. **主程序集成**
   - 修改 `main.py`
   - 添加命令行参数

2. **测试**
   - 单元测试
   - 集成测试
   - 报告格式验证

## 八、风险与应对

### 8.1 数据源风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| yfinance API限制 | 美股数据获取失败 | 增加重试机制、缓存数据 |
| 新闻搜索配额耗尽 | 新闻分析缺失 | 多数据源备份、降级处理 |
| 分钟数据不可用 | 技术分析受限 | 使用日K数据替代 |

### 8.2 性能风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 多股票分析耗时 | 报告生成延迟 | 并行处理、异步执行 |
| 大量数据查询 | 数据库压力 | 增加缓存、分批处理 |

### 8.3 兼容性风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 与现有功能冲突 | 系统不稳定 | 独立模块设计、充分测试 |
| 配置项冲突 | 功能异常 | 配置项命名空间隔离 |

## 九、验证计划

### 9.1 功能验证

- [ ] 晨间复盘报告生成正确
- [ ] 午间监测报告生成正确
- [ ] 晚间监测报告生成正确
- [ ] 多时间点调度正常工作
- [ ] 价格区间计算准确
- [ ] KDJ指标计算正确
- [ ] 背离检测准确
- [ ] 报告推送正常

### 9.2 集成验证

- [ ] 与现有调度系统兼容
- [ ] 与持仓服务集成正常
- [ ] 与通知服务集成正常
- [ ] Web界面显示正常

### 9.3 回归测试

- [ ] 现有功能不受影响
- [ ] CI门禁通过
- [ ] 前端构建正常

## 十、后续优化方向

1. **数据可视化**：增加图表生成（K线图、指标图）
2. **历史对比**：支持历史报告查询与趋势对比
3. **智能预警**：基于规则的自动预警推送
4. **Web界面**：增加监测报告查看页面
5. **自定义模板**：支持用户自定义报告模板
