# JoinQuant（聚宽）量化交易 45 天强化计划

**开始日期：** 2026-07-07（Day 1）
**当前进度：** ✅ 已完成 Day 1–15（第一阶段全部通关）
**下一阶段：** Day 16–45（第二阶段：策略开发 + 风控体系 → 第三阶段：模拟盘 → 实盘）
**目标：** 每天一个代码实验，45 天后能自己写策略、跑回测、做模拟盘
**压缩说明：** 从 90 天压缩至 45 天，保持每天动手实操+验证，去掉了重复性内容，强化了核心技能的密度

---

## 📋 使用说明

- 每天 1-2 小时
- 先看今天的代码 → 复制到 JoinQuant → 运行 → 改参数再跑 → 对比结果
- **"不动手就不算学"**——代码都必须实际跑一遍
- 早 8 点会收到当天任务提醒，晚 9 点有复习题

---

# ✅ 第一阶段：基础实操（Day 1–15）—— 已完成

## Week 1：跑通第一个回测（Day 1–7）

---

### Day 1 — 登录 JoinQuant + 跑通环境

**🎯 今日目标：** 登录 JoinQuant，在"研究环境"里跑出第一行代码

**📝 步骤：**
1. 打开浏览器 → [joinquant.com](https://www.joinquant.com)
2. 点右上角「登录」→ 选择「微信登录」，扫码
3. 登录后点顶部导航 → **「研究平台」**
4. 左侧点 **「新建」** → 选择 **「Python 3 研究 notebook」**
5. 在第一个 cell 里粘贴下面的代码，按 `Shift+Enter` 运行

**💻 代码：**
```python
# 第一行 JoinQuant 代码 — 获取贵州茅台行情
from jqdata import *
import pandas as pd
import numpy as np

# 获取茅台最近 10 天的行情
df = get_price('600519.XSHG', count=10, frequency='daily',
               fields=['close', 'volume', 'paused'])
print(df)
print(f"\n最新收盘价: {df['close'].iloc[-1]:.2f}")
print(f"10日均价: {df['close'].mean():.2f}")
```

**✅ 验证标准：** 看到打印出了 10 行带日期、收盘价、成交量的表格。

**📌 核心理解：** JoinQuant 的数据就是 `get_price(股票代码, 参数)` 这么简单。代码=代码，后面所有策略都从这里开始。

---

### Day 2 — pandas 数据处理基础

**🎯 今日目标：** 学会用 pandas 处理行情数据——这是量化的基本功

**📝 步骤：**
1. 还是在 JoinQuant 研究环境，开一个新 notebook
2. 把下面代码分段粘贴到 cell 里，逐个 Shift+Enter 运行

**💻 代码：**
```python
# cell 1: 获取数据
df = get_price('000300.XSHG', start_date='2024-01-01', 
               end_date='2024-12-31', frequency='daily',
               fields=['close', 'volume'])
print(f"数据量: {len(df)} 行")
print(df.head())

# cell 2: 滚动计算（均线）
df['MA5'] = df['close'].rolling(5).mean()
df['MA20'] = df['close'].rolling(20).mean()
print(df[['close', 'MA5', 'MA20']].tail())

# cell 3: 未来函数演示（⚠️ 重点！）
df['wrong_signal'] = df['close'].shift(-1)  # ❌ 用了未来数据！
df['correct_signal'] = df['close'].shift(1) # ✅ 只用到历史数据
print(df[['close', 'wrong_signal', 'correct_signal']].head(10))
```

**🔬 实验任务：**
观察 `shift(-1)` 和 `shift(1)` 的区别。`shift(-1)` 拿到了"明天的数据"——这就是量化里最致命的**未来函数**。

**✅ 验证标准：** 看到 MA5 和 MA20 两列数据，理解为什么 `shift(1)` 才是正确的。

---

### Day 3 — 画图：把数据变成图表

**🎯 今日目标：** 画出 K 线和均线图，直观感受数据

**📝 步骤：** 在 JoinQuant 研究环境运行下面代码

**💻 代码：**
```python
# cell 1: 获取数据和计算指标
df = get_price('600519.XSHG', start_date='2024-06-01', 
               end_date='2024-12-31', frequency='daily',
               fields=['close', 'volume'])
df['MA5'] = df['close'].rolling(5).mean()
df['MA20'] = df['close'].rolling(20).mean()
df['MA60'] = df['close'].rolling(60).mean()

# cell 2: 画图
import matplotlib.pyplot as plt
plt.figure(figsize=(14, 6))
plt.plot(df.index, df['close'], label='收盘价', color='black', linewidth=1)
plt.plot(df.index, df['MA5'], label='MA5', linestyle='--')
plt.plot(df.index, df['MA20'], label='MA20', linestyle='--')
plt.plot(df.index, df['MA60'], label='MA60', linestyle='--')
plt.title('贵州茅台 2024 下半年 K 线与均线')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

**🔬 实验任务：**
- 把股票换成 `'000001.XSHE'`（平安银行），看看均线形态有什么不同？
- 把日期改到 `2022-01-01`，看看牛熊周期的区别

**✅ 验证标准：** 画出了一张清晰的股价+均线图，能看到金叉和死叉的位置。

---

### Day 4 — 第一个回测：双均线策略（粘贴即跑）

**🎯 今日目标：** 今天的代码直接粘贴到 JoinQuant **策略回测模块**，跑通人生第一个回测。

**📝 步骤：**
1. 回到 JoinQuant 首页 → 点顶部「量化研究平台」
2. 在左侧「策略研究」下 → 点 **「新建策略」**
3. 把标题改成 `双均线策略`
4. **用下面代码覆盖全部内容**
5. 右上角设置回测区间：`2020-01-01 至 2024-12-31`
6. 初始资金：`1,000,000`
7. 点 **「运行回测」**

**💻 代码（粘贴到策略编辑器）：**
```python
def initialize(context):
    run_daily(ma_strategy, time='before_open')
    g.stock = '000001.XSHE'

def ma_strategy(context):
    df = attribute_history(g.stock, 50, '1d', ['close'])
    if df.empty or len(df) < 3:
        return
    close = df['close']
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    
    # 信号：前日 vs 今日均线关系
    buy = ma5.iloc[-2] <= ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]
    sell = ma5.iloc[-2] >= ma20.iloc[-2] and ma5.iloc[-1] < ma20.iloc[-1]
    
    pos = context.portfolio.positions[g.stock].amount
    if buy and pos == 0:
        order_value(g.stock, context.portfolio.available_cash)
    elif sell and pos > 0:
        order_target(g.stock, 0)
```

**🔬 实验任务（跑完第一次后）：**
1. 把 `g.stock` 换成 `'600519.XSHG'`（茅台），再跑一次
2. 把 MA5/MA20 改成 MA10/MA30，再跑一次
3. 对比三组结果：哪组年化收益最高？哪组最大回撤最小？

**✅ 验证标准：** 回测跑出结果，看到资金曲线和绩效指标表。

---

### Day 5 — 读懂回测报告

**🎯 今日目标：** 理解回测结果页面每一项指标的含义

**📝 步骤：**
1. 用 Day 4 跑出来的回测结果
2. 点 **「回测报告」** → 逐项看以下指标

**📊 回测报告解读表：**

| 指标 | 含义 | 好/坏标准 | 你的策略值 |
|------|------|----------|-----------|
| 年化收益率 | 折算成一年的收益率 | >10% 不错，>20% 优秀 | __% |
| 基准收益率 | 同期沪深 300 涨幅 | 高于基准才算有真本事 | __% |
| 最大回撤 | 从最高点最多亏了多少 | <15% 安全，>30% 危险 | __% |
| 夏普比率 | 每承担 1 单位风险赚多少 | >1 好，>2 优秀 | __ |
| 胜率 | 赚钱的交易占比 | >40% 合格 | __% |
| 交易次数 | 总共交易了几次 | 太少可能是参数问题 | __次 |

**🔬 实验任务：**
把上一步 MA10/MA30 的结果也打开，对比两张报告：
- 哪个夏普更高？
- 哪个最大回撤更小？
- 如果让你选一个实盘，你选哪个？为什么？

---

### Day 6 — 参数敏感性实验

**🎯 今日目标：** 跑 5 组不同参数，理解"过拟合"是什么

**📝 步骤：**
1. 在 Day 4 的策略里，依次把 MA 参数改成下面 5 组，**每改一次跑一次回测**
2. 记录每次的年化收益率

**💻 实验记录表：**

| 组号 | MA 参数 | 年化收益 | 最大回撤 | 交易次数 | 你的判断 |
|------|---------|---------|---------|---------|---------|
| 1 | MA5/MA20 | _____% | _____% | _____次 | |
| 2 | MA10/MA30 | _____% | _____% | _____次 | |
| 3 | MA20/MA60 | _____% | _____% | _____次 | |
| 4 | MA5/MA60 | _____% | _____% | _____次 | |
| 5 | MA10/MA60 | _____% | _____% | _____次 | |

**🔬 关键问题：**
- 最好的一组参数，年化收益是____%？
- 最差的一组参数，年化收益是____%？
- 如果"最好"的比"次好"的好很多（比如 30% vs 10%），那就是**过拟合**的信号

**✅ 今天的结论：** 没有"最好"的参数——只有"在不同市场下表现尚可"的参数。

---

### Day 7 — ✅ 第一周复盘

**🎯 今日任务：** 不做新东西，回顾本周

**📝 步骤：**
1. 打开你 Day 4-6 跑过的所有回测结果
2. 选出你认为最有潜力的一个策略
3. 回答以下三个问题（写到 JoinQuant 研究环境的笔记里）：

**❓ 三个问题：**
```
1. 我的策略赚的是什么钱？
   （趋势来了跟趋势，还是波动大了做反转？）
   
2. 我的策略最怕什么市场？
   （连续震荡会不会反复打脸？单边下跌会不会死扛？）
   
3. 如果明天就要实盘，我敢不敢上？
   不敢的原因是什么？
```

**✅ 第一周目标达成：** 你已经跑通了"数据获取→策略编写→回测→评价"的完整流程。

---

## Week 2：数据指标 + 趋势策略（Day 8–15）

### Day 8 — 获取财务数据

**🎯 今日目标：** 用 `get_fundamentals()` 拉取真实财务数据

**💻 代码（JoinQuant 研究环境）：**
```python
# 获取沪深300成分股的最新PE和ROE
from jqdata import *

# 取沪深300成分股前10只的财务数据
df = get_fundamentals(query(
    valuation.code, valuation.pe_ratio, indicator.roe
).filter(
    valuation.code.in_(get_index_stocks('000300.XSHG'))
).order_by(
    valuation.pe_ratio.asc()
).limit(10))

print("沪深300估值最低的10只股票：")
print(df)
```

**🔬 实验任务：**
- 改成按 ROE 从高到低排序：`indicator.roe.desc()`
- 加上市盈率小于 20 的过滤条件
- 数一数：沪深300里同时满足 PE<20 且 ROE>15% 的有几只？

---

### Day 9 — 手写 MACD + 金叉死叉信号

**🎯 今日目标：** 用手算一遍 MACD，彻底搞懂，并生成交易信号

**💻 代码：**
```python
# 手写 MACD 计算
df = get_price('600519.XSHG', start_date='2024-01-01', 
               end_date='2024-12-31', frequency='daily',
               fields=['close'])

close = df['close']
ema12 = close.ewm(span=12, adjust=False).mean()
ema26 = close.ewm(span=26, adjust=False).mean()
dif = ema12 - ema26
dea = dif.ewm(span=9, adjust=False).mean()
macd_bar = (dif - dea) * 2

result = pd.DataFrame({'close': close, 'DIF': dif, 'DEA': dea, 'MACD': macd_bar})
print(result.tail(5))
print(f"\n最后交易日DIF: {dif.iloc[-1]:.2f}, DEA: {dea.iloc[-1]:.2f}")
print(f"{'金叉信号' if dif.iloc[-1] > dea.iloc[-1] else '死叉信号'}")
```

**🔬 实验任务：**
- DIF 在 DEA 上方还是下方？说明当前是金叉还是死叉？
- 把周期改成日线数据，看看茅台历史上金叉/死叉和股价涨跌的关系

---

### Day 10 — 条件选股：用财务指标筛选牛股

**🎯 今日目标：** 用财务指标筛选出值得关注的股票，为多股策略做准备

**💻 代码：**
```python
# 选股：PE<20, ROE>15%, 营收增长>10%
df = get_fundamentals(query(
    valuation.code, valuation.pe_ratio, 
    indicator.roe, indicator.inc_revenue_year_on_year
).filter(
    valuation.pe_ratio < 20,
    indicator.roe > 15,
    indicator.inc_revenue_year_on_year > 10,
    valuation.code.in_(get_index_stocks('000300.XSHG'))
))

print(f"符合条件的股票: {len(df)} 只")
print(df)
```

**🔬 实验任务：**
- 把条件放宽：PE<30 能多选出几只？
- 把条件收紧：ROE>20% 还能剩下几只？
- 选出来的股票里，找一只你认识的，去研究它的基本面

---

### Day 11 — 多股票回测 + 画买卖点

**🎯 今日目标：** 把双均线策略应用到多只股票上，把买卖点画到 K 线图上

**💻 代码第一段（多股票回测——在策略编辑器）：**
```python
def initialize(context):
    run_daily(ma_strategy, time='before_open')
    g.stocks = ['000001.XSHE', '600519.XSHG', '000651.XSHE', '000333.XSHE', '002415.XSHE']
    g.ma_short = 5
    g.ma_long = 20

def ma_strategy(context):
    for stock in g.stocks:
        df = attribute_history(stock, 50, '1d', ['close'])
        if df.empty or len(df) < 3:
            continue
        close = df['close']
        ma_short = close.rolling(g.ma_short).mean()
        ma_long = close.rolling(g.ma_long).mean()
        
        buy = ma_short.iloc[-2] <= ma_long.iloc[-2] and ma_short.iloc[-1] > ma_long.iloc[-1]
        sell = ma_short.iloc[-2] >= ma_long.iloc[-2] and ma_short.iloc[-1] < ma_long.iloc[-1]
        
        pos = context.portfolio.positions[stock].amount
        if buy and pos == 0:
            order_value(stock, context.portfolio.available_cash / len(g.stocks))
        elif sell and pos > 0:
            order_target(stock, 0)
```

**💻 代码第二段（在研究环境画买卖点）：**
```python
# 画 K 线 + 买卖点标记
import matplotlib.pyplot as plt

df = get_price('000001.XSHE', start_date='2024-06-01', end_date='2024-12-31', frequency='daily', fields=['close'])
df['MA5'] = df['close'].rolling(5).mean()
df['MA20'] = df['close'].rolling(20).mean()

# 生成买卖信号
df['buy'] = (df['MA5'].shift(1) <= df['MA20'].shift(1)) & (df['MA5'] > df['MA20'])
df['sell'] = (df['MA5'].shift(1) >= df['MA20'].shift(1)) & (df['MA5'] < df['MA20'])

plt.figure(figsize=(14, 6))
plt.plot(df.index, df['close'], label='收盘价', color='gray', alpha=0.5)
plt.plot(df.index, df['MA5'], label='MA5', linestyle='--')
plt.plot(df.index, df['MA20'], label='MA20', linestyle='--')
plt.scatter(df.index[df['buy']], df['close'][df['buy']], marker='^', color='red', s=100, label='买入')
plt.scatter(df.index[df['sell']], df['close'][df['sell']], marker='v', color='green', s=100, label='卖出')
plt.title('双均线策略买卖信号')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
```

**✅ 验证标准：** 图上看到红色买入标记和绿色卖出标记，能直观判断信号的好坏。

---

### Day 12 — 加入止损 + 回撤控制

**🎯 今日目标：** 在双均线策略中加入止损和回撤控制两个风控手段

**💻 代码（在策略编辑器中修改）：**
```python
def initialize(context):
    run_daily(ma_strategy, time='before_open')
    g.stock = '000001.XSHE'
    g.stop_loss_pct = 0.08  # 单笔止损8%

def ma_strategy(context):
    df = attribute_history(g.stock, 50, '1d', ['close'])
    if df.empty or len(df) < 3:
        return
    
    close = df['close']
    current_price = close.iloc[-1]
    
    # === 止损检查 ===
    pos = context.portfolio.positions[g.stock]
    if pos.amount > 0:
        cost = pos.avg_cost
        loss_pct = (current_price - cost) / cost
        if loss_pct < -g.stop_loss_pct:
            order_target(g.stock, 0)
            log.info(f"触发止损: {loss_pct:.1%}，已清仓")
            return
    
    # === 总回撤检查 ===
    total_returns = context.portfolio.returns
    if total_returns < -0.15:
        log.warn(f"总回撤超过15%({total_returns:.1%})，暂停交易")
        return
    
    # === 均线信号 ===
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    buy = ma5.iloc[-2] <= ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]
    sell = ma5.iloc[-2] >= ma20.iloc[-2] and ma5.iloc[-1] < ma20.iloc[-1]
    
    if buy and pos.amount == 0:
        order_value(g.stock, context.portfolio.available_cash)
    elif sell and pos.amount > 0:
        order_target(g.stock, 0)
```

**🔬 实验任务：**
- 跑一次带止损的 vs 不带止损的，对比最大回撤和年化收益
- 把止损改成 5% 和 12%，看看对结果的影响

**✅ 验证标准：** 带止损后最大回撤明显减小（通常下降 30-50%），但收益也可能略降——这就是风控的代价。

---

### Day 13 — 趋势策略实战：海龟交易法简化版

**🎯 今日目标：** 实现一个通道突破策略（唐奇安通道），这是海龟交易法的核心

**💻 代码（策略编辑器）：**
```python
def initialize(context):
    run_daily(turtle_strategy, time='before_open')
    g.stock = '000001.XSHE'
    g.entry_period = 20   # 突破周期
    g.exit_period = 10    # 离场周期

def turtle_strategy(context):
    df = attribute_history(g.stock, max(g.entry_period, g.exit_period) + 1, '1d', ['close', 'high', 'low'])
    if df.empty or len(df) < g.entry_period + 1:
        return
    
    # 唐奇安通道
    recent_high = df['high'].rolling(g.entry_period).max()
    recent_low = df['low'].rolling(g.entry_period).min()
    exit_low = df['low'].rolling(g.exit_period).min()
    
    current_close = df['close'].iloc[-1]
    prev_high = recent_high.iloc[-2]
    prev_low = recent_low.iloc[-2]
    
    pos = context.portfolio.positions[g.stock].amount
    # 突破前20日最高点 → 买入
    if current_close > prev_high and pos == 0:
        order_value(g.stock, context.portfolio.available_cash)
    # 跌破前10日最低点 → 卖出
    elif current_close < exit_low.iloc[-2] and pos > 0:
        order_target(g.stock, 0)
```

**🔬 实验任务：**
- 对比海龟策略和双均线策略在同一只股票、同一时间段的收益和回撤
- 调整 entry_period 为 10/20/30，看哪个参数最优

**✅ 验证标准：** 跑通回测，能看到通道突破策略在趋势行情中表现更好。

---

### Day 14 — 均值回归：布林带策略

**🎯 今日目标：** 实现布林带均值回归策略——和趋势策略反着做

**💻 代码（策略编辑器）：**
```python
def initialize(context):
    run_daily(bollinger_strategy, time='before_open')
    g.stock = '000001.XSHE'
    g.period = 20
    g.std = 2

def bollinger_strategy(context):
    df = attribute_history(g.stock, g.period + 1, '1d', ['close'])
    if df.empty or len(df) < g.period + 1:
        return
    
    close = df['close']
    ma = close.rolling(g.period).mean()
    upper = ma + g.std * close.rolling(g.period).std()
    lower = ma - g.std * close.rolling(g.period).std()
    
    current = close.iloc[-1]
    prev_close = close.iloc[-2]
    pos = context.portfolio.positions[g.stock].amount
    
    # 跌破下轨 → 买入（回归预期）
    if prev_close <= lower.iloc[-2] and pos == 0:
        order_value(g.stock, context.portfolio.available_cash)
    # 涨破上轨 → 卖出（回归预期）
    elif prev_close >= upper.iloc[-2] and pos > 0:
        order_target(g.stock, 0)

def sell_condition(context):
    pass
```

**🔬 实验任务：**
- 在震荡行情中跑布林带 vs 在趋势行情中跑布林带，看差异
- 和 Day 13 的海龟策略对比：**同一个时间段，哪个赚了？**
- **关键理解：** 没有哪个策略永远有效——趋势策略赚趋势的钱，均值回归赚震荡的钱

---

### Day 15 — ✅ 第一阶段复盘：策略对比 + 选型考核

**🎯 今日任务：** 复盘过去 14 天，完成第一次策略选型考核

**📝 步骤：**
1. 打开你跑过的所有回测：双均线、通道突破、布林带
2. 在同一时间段（建议 2020-2024）对比三者的绩效

**📊 三策略对比表：**

| 策略 | 年化收益 | 最大回撤 | 夏普比率 | 胜率 | 最佳市场环境 |
|------|---------|---------|---------|------|------------|
| 双均线趋势 | _____% | _____% | _____ | _____% | |
| 通道突破 | _____% | _____% | _____ | _____% | |
| 布林带回归 | _____% | _____% | _____ | _____% | |

**❓ 考核问题（回答并记录）：**
```
1. 这三种策略分别赚的是什么钱？
2. 如果未来一个月是震荡市，你会选哪个？
3. 如果未来一个月是大牛市，你会选哪个？
4. 有没有哪个策略在任何市场都表现很好？（答案应该是否定的——如果有，你找到圣杯了）
5. 目前你最喜欢哪个策略？为什么？
```

**✅ 第一阶段目标达成：** 你已经掌握了 3 种策略类型（趋势+突破+回归），能跑回测、读报告、做风控。可以进入策略开发阶段了。

---

# 第二阶段：策略开发 + 风控体系（Day 16–30）

## Week 3：多因子 + 策略深度（Day 16–23）

### Day 16 — 打分选股：价值+质量+动量三因子

**🎯 今日目标：** 实现多因子打分选股模型，按综合得分选前 10 名买入

**💻 代码（研究环境）：**
```python
# 多因子打分选股
from jqdata import *

# 获取沪深300全部股票
stocks = get_index_stocks('000300.XSHG')

# 拉取三因子数据
df = get_fundamentals(query(
    valuation.code, valuation.pe_ratio,       # 价值因子
    indicator.roe,                               # 质量因子
    indicator.inc_revenue_year_on_year,          # 成长因子
    valuation.market_cap                          # 市值
).filter(
    valuation.code.in_(stocks)
))

# 打分（分位数法）
df['pe_score'] = 1 - (df['pe_ratio'].rank() / len(df))  # PE越低分越高
df['roe_score'] = df['roe'].rank() / len(df)             # ROE越高分越高
df['growth_score'] = df['inc_revenue_year_on_year'].rank() / len(df)
df['total_score'] = (df['pe_score'] + df['roe_score'] + df['growth_score']) / 3

# 选出前10名
top10 = df.sort_values('total_score', ascending=False).head(10)
print("综合得分最高的10只股票：")
print(top10[['code', 'pe_ratio', 'roe', 'total_score']])
```

**🔬 实验任务：**
- 把打分权重改成 PE 占 50%、ROE 占 25%、成长占 25%，看前 10 有何变化
- 换成中证 500 的股票再跑一次

---

### Day 17 — 打分选股回测：每月调仓

**🎯 今日目标：** 把 Day 16 的打分模型实现为完整的每月调仓策略

**💻 代码（策略编辑器——关键代码）：**
```python
def initialize(context):
    run_monthly(rebalance, monthday=1, time='before_open')  # 每月1号调仓
    g.stock_count = 10

def rebalance(context):
    stocks = get_index_stocks('000300.XSHG')
    df = get_fundamentals(query(
        valuation.code, valuation.pe_ratio,
        indicator.roe, indicator.inc_revenue_year_on_year
    ).filter(valuation.code.in_(stocks)))
    
    # 打分
    df['score'] = (
        (1 - df['pe_ratio'].rank() / len(df)) +   # PE
        df['roe'].rank() / len(df) +                # ROE
        df['inc_revenue_year_on_year'].rank() / len(df)
    ) / 3
    
    buy_list = df.sort_values('score', ascending=False).head(g.stock_count)['code'].tolist()
    
    # 卖出不在列表中的持仓
    for stock in context.portfolio.positions:
        if stock not in buy_list:
            order_target(stock, 0)
    
    # 买入新选出的股票
    cash_per = context.portfolio.available_cash / len(buy_list)
    for stock in buy_list:
        order_value(stock, cash_per)
```

**🔬 实验任务：**
- 改为每月 15 号调仓，对比月头和月中的差异
- 把选股数改成 5 只和 20 只，对比结果

**✅ 验证标准：** 看到了每月调仓的完整回测结果，资金曲线是阶梯式增长的。

---

### Day 18 — IC 分析：因子有效性检验

**🎯 今日目标：** 计算 PE 因子与未来收益的相关性（IC 值），判断因子是否靠谱

**💻 代码（研究环境）：**
```python
# IC 分析：PE 因子与未来 20 日收益的相关性
stocks = get_index_stocks('000300.XSHG')
dates = get_trade_days(start_date='2024-01-01', end_date='2024-12-31', count=None)
trade_dates = list(dates)[::20]  # 每20日取一个截面

ic_values = []
for i, date in enumerate(trade_dates):
    if i + 1 >= len(trade_dates):
        break
    # 截面 PE
    q = query(valuation.code, valuation.pe_ratio).filter(valuation.code.in_(stocks))
    pe_df = get_fundamentals(q, date=date)
    
    # 未来 20 日收益
    future_date = trade_dates[i + 1]
    future_prices = get_price([s for s in pe_df['code']], start_date=date, 
                              end_date=future_date, frequency='daily', fields=['close'])
    
    if future_prices.empty:
        continue
    
    # 计算每只股票的收益率
    returns = future_prices['close'].groupby('code').apply(
        lambda x: (x.iloc[-1] - x.iloc[0]) / x.iloc[0]
    )
    
    merged = pe_df.set_index('code').join(returns.rename('return'))
    merged = merged.dropna()
    if len(merged) > 5:
        ic = merged['pe_ratio'].corr(merged['return'])
        ic_values.append(ic)

print(f"IC 均值: {np.mean(ic_values):.3f}")
print(f"IC 标准差: {np.std(ic_values):.3f}")
print(f"IC > 0 比例: {sum(1 for v in ic_values if v > 0) / len(ic_values):.1%}")
```

**✅ 验证标准：** 看到 IC 均值（接近 0 说明 PE 因子预测能力弱，绝对值越大越好）和 IC>0 比例（越高因子越稳定）。

---

### Day 19 — 动量因子 + 反转因子策略

**🎯 今日目标：** 实现动量策略（追涨）和反转策略（抄底），对比效果

**💻 代码（研究环境——先算再策略回测）：**
```python
# 动量因子：过去 60 日涨幅最高的股票
stocks = get_index_stocks('000300.XSHG')
df_momentum = get_price(stocks, start_date='2024-01-01', end_date='2024-12-31', 
                        frequency='daily', fields=['close'], skip_paused=True)
# 计算每只股票的 60 日收益率
returns_60d = {}
for stock in stocks:
    try:
        prices = df_momentum['close'][stock]
        if len(prices) >= 60:
            ret = (prices.iloc[-1] - prices.iloc[-60]) / prices.iloc[-60]
            returns_60d[stock] = ret
    except:
        pass

sorted_by_momentum = sorted(returns_60d.items(), key=lambda x: x[1], reverse=True)
print("动量最强（涨幅最大）的前 10 只：")
for stock, ret in sorted_by_momentum[:10]:
    print(f"  {stock}: {ret:.1%}")

print("\n反转最强（跌幅最大）的前 10 只：")
for stock, ret in sorted_by_momentum[-10:][::-1]:
    print(f"  {stock}: {ret:.1%}")
```

**🔬 实验任务：**
- 把动量周期改成 20 日、120 日，对比结果——哪组最好？
- 在策略编辑器中，实现一个每月买动量前 10 的策略，回测看效果

---

### Day 20 — 四种策略大对比 + 策略选择框架

**🎯 今日目标：** 在相同条件下对比趋势、均值回归、动量、反转四种策略，建立策略选择思维

**📝 步骤：**
1. 打开你前面跑过的所有回测结果（双均线、布林带、动量、反转）
2. 确保都是同一时间段（2020-01 到 2024-12）
3. 填写下表

**📊 四策略终极对比：**

| 策略 | 年化收益 | 最大回撤 | 夏普 | 2020年 | 2021年 | 2022年 | 2023年 | 2024年 |
|------|---------|---------|------|-------|-------|-------|-------|-------|
| 双均线趋势 | | | | | | | | |
| 布林带回归 | | | | | | | | |
| 动量 | | | | | | | | |
| 反转 | | | | | | | | |

**❓ 回答：**
```
1. 2022 年（熊市）哪种策略表现最好？为什么？
2. 2020 年（牛市）哪种策略表现最好？为什么？
3. 有没有一种策略能适应所有年份？如果没有——这说明什么？
```

**✅ 关键结论：** 量化交易的核心不是找一个永远有效的策略，而是**知道当前是什么市场，用对应的策略**。

---

### Day 21-22 — 风控体系强化（止损+仓位+组合）

**🎯 今日目标：** 把三种风控手段整合进一个策略：凯利公式仓位 + ATR 止损 + 组合限制

**💻 Day 21 代码（研究环境——凯利公式计算器）：**
```python
# 凯利公式：f* = (p * b - q) / b
# p = 胜率, q = 1-p, b = 盈亏比
win_rate = 0.45   # 假设胜率 45%
profit_ratio = 2.0  # 盈亏比 2:1

kelly_f = (win_rate * profit_ratio - (1 - win_rate)) / profit_ratio
print(f"凯利比例: {kelly_f:.2%}")
print(f"建议仓位（1/4凯利）: {kelly_f / 4:.2%}")
```

**💻 Day 22 代码（策略编辑器——完整风控策略）：**
```python
def initialize(context):
    run_daily(trade_with_risk_control, time='before_open')
    g.stock = '000001.XSHE'
    # 风控参数
    g.max_single_pos = 0.3      # 单只上限 30%
    g.max_drawdown = 0.15       # 总回撤上限 15%
    g.atr_multiple = 2.0        # ATR 止损倍数

def trade_with_risk_control(context):
    # === 1. 总回撤检查 ===
    if context.portfolio.returns < -g.max_drawdown:
        for stock in list(context.portfolio.positions.keys()):
            order_target(stock, 0)
        log.warn("总回撤超限，全部清仓")
        return
    
    # === 2. ATR 止损检查（已有持仓） ===
    for stock in list(context.portfolio.positions.keys()):
        pos = context.portfolio.positions[stock]
        if pos.amount == 0:
            continue
        df = attribute_history(stock, 20, '1d', ['close', 'high', 'low'])
        if df.empty:
            continue
        # 计算 ATR
        tr = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        ], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        stop_price = df['close'].iloc[-1] - g.atr_multiple * atr
        if stop_price > 0:  # 虚拟止损检查
            cost = pos.avg_cost
            loss_pct = (stop_price - cost) / cost
            if loss_pct < -0.08:  # 如果 ATR 止损位低于成本 8%
                order_target(stock, 0)
                log.info(f"{stock} ATR止损触发")
    
    # === 3. 均线信号 + 仓位控制 ===
    df = attribute_history(g.stock, 50, '1d', ['close'])
    if df.empty:
        return
    close = df['close']
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    
    buy = ma5.iloc[-2] <= ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]
    pos = context.portfolio.positions[g.stock].amount
    
    if buy and pos == 0:
        # 只用可用资金的 30%（单只上限）
        order_value(g.stock, context.portfolio.available_cash * g.max_single_pos)
```

**✅ 验证标准：** 风险控制生效——极端行情下回撤被控制在预设范围内。

---

### Day 23 — ✅ 第二周复盘 + 风控测试

**🎯 今日任务：** 复盘策略+风控进度，做一次极端行情压力测试

**📝 压力测试：**
1. 把你的最佳策略放在 **2015-06 到 2016-01**（股灾期间）回测
2. 对比带风控和不带风控的差异
3. 记录以下数据：

| 指标 | 不带风控 | 带风控 | 改善幅度 |
|------|---------|-------|---------|
| 最大回撤 | _____% | _____% | 减少____% |
| 年化收益 | _____% | _____% | 变化____% |
| 最终收益 | _____ | _____ | _____ |

**❓ 思考题：**
```
风控减少了回撤，但也可能减少了收益——这个代价你愿意接受吗？
极端行情（如 2015 股灾）中，你的策略能活下来吗？
```

---

## Week 4：策略工厂 + 实战整合（Day 24–30）

### Day 24 — 构建通用策略框架

**🎯 今日目标：** 写一个可以快速切换策略的函数式框架

**💻 代码（策略编辑器）：**
```python
def initialize(context):
    run_daily(run_strategy, time='before_open')
    g.stock = '000001.XSHE'
    g.strategy = 'trend'  # 可切换: trend, reversal, bollinger
    g.params = {'ma_short': 5, 'ma_long': 20}  # 策略参数

def run_strategy(context):
    df = attribute_history(g.stock, 60, '1d', ['close'])
    if df.empty:
        return
    
    if g.strategy == 'trend':
        signal = trend_signal(df, g.params)
    elif g.strategy == 'reversal':
        signal = reversal_signal(df, g.params)
    elif g.strategy == 'bollinger':
        signal = bollinger_signal(df, g.params)
    else:
        return
    
    pos = context.portfolio.positions[g.stock].amount
    if signal == 1 and pos == 0:
        order_value(g.stock, context.portfolio.available_cash)
    elif signal == -1 and pos > 0:
        order_target(g.stock, 0)

def trend_signal(df, params):
    close = df['close']
    ma_s = close.rolling(params['ma_short']).mean()
    ma_l = close.rolling(params['ma_long']).mean()
    if ma_s.iloc[-2] <= ma_l.iloc[-2] and ma_s.iloc[-1] > ma_l.iloc[-1]:
        return 1
    elif ma_s.iloc[-2] >= ma_l.iloc[-2] and ma_s.iloc[-1] < ma_l.iloc[-1]:
        return -1
    return 0

def reversal_signal(df, params):
    close = df['close']
    ma = close.rolling(params.get('period', 20)).mean()
    std = close.rolling(params.get('period', 20)).std()
    if close.iloc[-1] < ma.iloc[-1] - 2 * std.iloc[-1]:
        return 1  # 超卖买入
    elif close.iloc[-1] > ma.iloc[-1] + 2 * std.iloc[-1]:
        return -1  # 超买卖出
    return 0

def bollinger_signal(df, params):
    return reversal_signal(df, params)
```

**🔬 实验任务：**
- 把 `g.strategy` 改成 `'reversal'` 跑一次回测，看结果是否和之前一致
- 给趋势策略加一个参数 `'ma_long': 30` 再跑

---

### Day 25 — 策略组合：多策略投票

**🎯 今日目标：** 让多个策略对同一只股票投票，多数一致才交易

**💻 代码（策略编辑器）：**
```python
def initialize(context):
    run_daily(voting_strategy, time='before_open')
    g.stock = '000001.XSHE'

def voting_strategy(context):
    df = attribute_history(g.stock, 60, '1d', ['close', 'high', 'low'])
    if df.empty:
        return
    
    votes = []
    
    # 策略1：双均线
    close = df['close']
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    if ma5.iloc[-1] > ma20.iloc[-1]:
        votes.append(1)   # 看多
    else:
        votes.append(-1)  # 看空
    
    # 策略2：价格 vs MA60（长期趋势）
    ma60 = close.rolling(60).mean()
    if close.iloc[-1] > ma60.iloc[-1]:
        votes.append(1)
    else:
        votes.append(-1)
    
    # 策略3：RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    if rsi.iloc[-1] > 50:
        votes.append(1)
    else:
        votes.append(-1)
    
    avg_vote = sum(votes) / len(votes)
    pos = context.portfolio.positions[g.stock].amount
    
    if avg_vote > 0 and pos == 0:   # 多数看多
        order_value(g.stock, context.portfolio.available_cash)
    elif avg_vote < 0 and pos > 0:  # 多数看空
        order_target(g.stock, 0)
```

**🔬 实验任务：**
- 跑一次投票策略 vs 单一双均线策略，对比稳定性和收益
- 把投票改成"全部一致才交易"，看交易次数和收益的变化

---

### Day 26 — 多策略投票进阶：加权投票 + 不同时间框架

**🎯 今日目标：** 给每个策略分配不同权重，并在不同时间框架上运行投票

**💻 代码（策略编辑器）：**
```python
def initialize(context):
    run_daily(weighted_voting, time='before_open')
    g.stock = '000001.XSHE'
    # 权重：信任度高的策略权重更大
    g.weights = {'trend_ma': 0.4, 'trend_long': 0.3, 'rsi': 0.2, 'volume': 0.1}

def weighted_voting(context):
    df = attribute_history(g.stock, 60, '1d', ['close', 'volume'])
    if df.empty:
        return
    close = df['close']
    
    # 策略1：双均线（短周期）
    ma5 = close.rolling(5).mean()
    ma20 = close.rolling(20).mean()
    v1 = 1 if ma5.iloc[-1] > ma20.iloc[-1] else -1
    
    # 策略2：均线位置（长周期）
    ma60 = close.rolling(60).mean()
    v2 = 1 if close.iloc[-1] > ma60.iloc[-1] else -1
    
    # 策略3：RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    v3 = 1 if rsi.iloc[-1] > 50 else -1
    
    # 策略4：成交量确认（放量上涨=强信号）
    vol_ma5 = df['volume'].rolling(5).mean()
    v4 = 1 if df['volume'].iloc[-1] > vol_ma5.iloc[-1] and close.iloc[-1] > close.iloc[-2] else -1
    
    # 加权总分
    total = (v1 * g.weights['trend_ma'] + v2 * g.weights['trend_long'] + 
             v3 * g.weights['rsi'] + v4 * g.weights['volume'])
    
    pos = context.portfolio.positions[g.stock].amount
    if total > 0 and pos == 0:
        order_value(g.stock, context.portfolio.available_cash)
    elif total < 0 and pos > 0:
        order_target(g.stock, 0)
```

**🔬 实验任务：**
- 跑一次加权投票 vs 普通投票，看是否有改善
- 调整权重，找出当前股票的最优权重组合
- **关键理解：** 加权投票比简单多数决更灵活——权重本身就是一种参数优化

---

### Day 27 — 策略绩效报告自动化

**🎯 今日目标：** 写一个函数，自动计算并打印所有绩效指标

**💻 代码（研究环境）：**
```python
# 自动绩效报告生成器
def performance_report(df, initial_capital=1000000):
    """df需包含日期索引和 total_returns 列"""
    import numpy as np
    
    # 年化收益率
    days = len(df)
    total_ret = df['total_returns'].iloc[-1]
    annual_ret = (1 + total_ret) ** (252 / days) - 1
    
    # 最大回撤
    cumulative = (1 + df['total_returns'])
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()
    
    # 夏普比率
    daily_ret = df['total_returns'].diff()
    sharpe = np.sqrt(252) * daily_ret.mean() / daily_ret.std() if daily_ret.std() > 0 else 0
    
    print("=" * 40)
    print("📊 策略绩效报告")
    print("=" * 40)
    print(f"回测天数: {days}")
    print(f"总收益率: {total_ret:.2%}")
    print(f"年化收益率: {annual_ret:.2%}")
    print(f"最大回撤: {max_dd:.2%}")
    print(f"夏普比率: {sharpe:.2f}")
    print(f"日均收益: {daily_ret.mean():.4%}")
    print(f"收益波动率: {daily_ret.std():.4%}")
    print("=" * 40)

# 使用示例
# 假设你有一个回测结果
# df = get_price('000001.XSHE', ...)
# performance_report(df)
```

---

### Day 28 — 模拟交易上线准备

**🎯 今日目标：** 在 JoinQuant 创建模拟交易，把最佳策略上线跑模拟盘

**📝 步骤：**
1. 登录 JoinQuant → 点 **「我的策略」**
2. 选你过去两周表现最好的一个策略
3. 点 **「创建模拟交易」**
4. 设置：初始资金 `1,000,000`，开始日期 `明天`
5. 点 **「启动」**
6. 截图或记录下来模拟盘创建成功的页面

**✅ 验证标准：** 模拟交易已启动，状态显示"运行中"。

**📌 重要：** 从今天开始，每天早上看一眼模拟盘——信号出了吗？和预期一致吗？

---

### Day 29 — 中期考核 + 实盘计划制定

**🎯 今日任务：** 完成中期考核，制定实盘上线计划

**📝 考核任务：**
1. **从零写一个新策略**（不能直接复制已有代码），包含：
   - 至少一种交易信号（均线/MACD/布林带等）
   - 止损或回撤风控
   - 跑回测 2020-2024
2. **写一份简短的分析报告**，包括：
   - 策略思路（一句话说清赚什么钱）
   - 回测绩效（年化、回撤、夏普）
   - 你给这个策略打几分（1-10）？为什么？

**📋 实盘计划表（填写）：**

| 项目 | 内容 |
|------|------|
| 选哪个策略实盘？ | |
| 初始资金 | （建议 ≤ 5,000 元） |
| 哪家券商？ | |
| 预计上线日期 | |
| 最大可接受亏损 | |
| 什么条件下会停掉实盘？ | |

---

### Day 30 — 第二阶段复盘 + 实盘方案定稿

**🎯 今日任务：** 复盘第二阶段，定稿实盘方案

**📝 步骤：**
1. 完成 Day 29 的考核策略回测和报告
2. 填写"实盘计划表"的每一项
3. 把实盘计划表截图保存

**❓ 复盘问题：**
```
1. 这个月你从零写了几个策略？
2. 现在你能区分"策略问题"和"参数问题"了吗？
3. 你选的实盘策略，它的最大风险是什么？
4. 如果这个策略实盘前三个月亏 20%，你会怎么办？
```

**✅ 第二阶段目标达成：** 你有了策略框架、风控体系、模拟盘运行中。进入实战阶段。

---

# 第三阶段：模拟盘 → 实盘（Day 31–45）

## Week 5：模拟盘运行 + 实盘准备（Day 31–37）

### Day 31 — 模拟盘第一天：记录

**🎯 今日目标：** 登录 JoinQuant，打开模拟盘，记录第一天的状态

**📝 检查清单：**
- [ ] 模拟盘是否正常发送了信号？
- [ ] 今天的信号是什么？（买入/卖出/持仓不动）
- [ ] 当前持仓市值多少？
- [ ] 累计收益多少？

**💬 记录：**
```
日期: 2026-__
模拟盘状态: 运行中/暂停/报错
今日信号: 
持仓:
收益:
心情/想法:
```

---

### Day 32 — 模拟盘 vs 回测对比

**🎯 今日目标：** 对比模拟盘和回测的差异

**💻 代码（研究环境）：**
```python
# 读取模拟盘历史交易记录（JoinQuant 模拟盘可导出）
# 对比模拟盘 vs 回测的每日收益
sim_returns = [/* 填入模拟盘每日收益率 */]
backtest_returns = [/* 填入回测每日收益率 */]

import matplotlib.pyplot as plt
plt.figure(figsize=(12, 5))
plt.plot(sim_returns, label='模拟盘', linestyle='-')
plt.plot(backtest_returns, label='回测', linestyle='--')
plt.title('模拟盘 vs 回测：每日收益对比')
plt.legend()
plt.grid(alpha=0.3)
plt.show()

# 计算相关性
import numpy as np
corr = np.corrcoef(sim_returns, backtest_returns)[0, 1]
print(f"模拟盘与回测相关性: {corr:.3f}")
```

**🔬 关键问题：**
- 如果相关性 < 0.7，说明回测和实盘差异很大——可能是**滑点、手续费、成交延迟**的问题
- 差异在哪？你能找出具体原因吗？

---

### Day 33 — 实盘交易成本计算

**🎯 今日目标：** 算清你的策略每月要交多少交易成本

**💻 代码（研究环境）：**
```python
# 交易成本计算器
commission_rate = 0.00025  # 佣金万分之2.5
stamp_tax_rate = 0.001     # 印花税千分之1（卖出时收）
min_commission = 5          # 最低佣金5元

# 假设你的策略每月交易 N 次
trades_per_month = 4        # 填入你的策略月均交易次数
avg_trade_value = 5000      # 平均每笔交易金额

commission_per_trade = max(avg_trade_value * commission_rate, min_commission)
stamp_tax = avg_trade_value * stamp_tax_rate
total_cost = (commission_per_trade * 2 + stamp_tax) * trades_per_month

print(f"每月交易成本估算:")
print(f"  佣金: {commission_per_trade * 2 * trades_per_month:.2f} 元")
print(f"  印花税: {stamp_tax * trades_per_month:.2f} 元")
print(f"  合计: {total_cost:.2f} 元/月")
print(f"  年化: {total_cost * 12:.2f} 元")
```

**🔬 实验任务：**
- 如果策略改为每周交易一次，成本变化多少？
- 如果你的策略年化收益只有 10%，成本占收益的百分之多少？
- 这个成本你接受吗？

---

### Day 34 — 券商选择 + 量化接口调研

**🎯 今日目标：** 了解各券商对个人量化交易的支持情况

**📝 调研清单：**
检查以下券商是否支持量化（用 JoinQuant 的券商对接功能）：

| 券商 | 是否对接JoinQuant | 佣金费率 | 是否支持API | 备注 |
|------|-----------------|---------|-----------|------|
| 华泰证券 | 是 | 万1.3-万2.5 | 涨乐财富通 | |
| 中信证券 | 是 | 万2.5 | 信e投 | |
| 国泰君安 | 是 | 万2.5 | 君弘 | |
| 平安证券 | 是 | 万2.5 | 平安证券 | |
| 东方财富 | 是 | 万2.5 | 东方财富 | |

**📌 操作：** 在 JoinQuant → 设置 → 券商管理，查看是否已有券商账号绑定。

---

### Day 35 — 实盘第一次入金 + 手动跟单

**🎯 今日目标：** 入金 ≤ 5,000 元到券商账户，按模拟盘信号手动下单

**📝 步骤：**
1. 打开券商 App
2. 入金（建议不超过 5,000 元）
3. 打开 JoinQuant 模拟盘，查看今天的交易信号
4. 在券商 App 按模拟盘的信号手动下单
5. 截屏保存：买入/卖出成功的页面

**⚠️ 铁律：**
- **第一笔不要超过 5,000 元**——这是学费
- **不要自己判断，完全跟模拟盘信号**——测试的是策略，不是你的直觉
- 如果信号和你的判断冲突——**跟信号，不要跟感觉**

---

### Day 36 — 实盘跟单第二天 + 交易日志

**🎯 今日目标：** 继续跟模拟盘信号，写交易日志

**📝 交易日志模板：**
```
日期: 
操作: 买入/卖出/持仓
金额: 
执行价格: 
偏离模拟盘信号价: +___% / -___% （滑点）
心情: 
学到的东西: 
```

**🔬 观察：** 你的成交价格和模拟盘信号价格差多少？这就是**滑点**。

---

### Day 37 — ✅ 第一周模拟盘复盘

**🎯 今日任务：** 复盘第一周模拟盘+实盘运行情况

**📊 一周总结表：**

| 项目 | 值 |
|------|-----|
| 模拟盘累计收益 | _____% |
| 实盘累计收益 | _____% |
| 信号次数 | _____次 |
| 实际执行次数 | _____次 |
| 平均滑点 | _____% |
| 最大单日亏损 | _____% |

**❓ 复盘问题：**
```
1. 这一周实盘跟单有几次没执行？为什么？
2. 滑点比你预期的多还是少？
3. 每天晚上看账户的时候，心情如何？
4. 你觉得自己能坚持执行这套系统多久？
```

---

## Week 6：稳定运行 + 毕业（Day 38–45）

### Day 38 — 策略跟踪表建立

**🎯 今日目标：** 建一个简单的 Excel/Google Sheet 跟踪表

**📊 跟踪表模板（建议用 Google Sheets）：**
| 日期 | 模拟盘收益 | 实盘收益 | 沪深300 | 信号 | 执行情况 | 备注 |
|------|----------|---------|--------|------|---------|------|
| | | | | | | |

**📝 操作：** 打开 Google Sheets → 新建 → 填入上述表头 → 每天或每周更新一次

---

### Day 39 — 策略体检：有没有过拟合？

**🎯 今日目标：** 把你的策略放到不同时间段验证

**💻 代码（在回测中分别跑以下时段）：**

| 时段 | 市场特征 | 你的策略年化收益 | 最大回撤 |
|------|---------|----------------|---------|
| 2017-01 至 2018-12 | 慢牛→熊市 | _____% | _____% |
| 2019-01 至 2020-12 | 反弹牛市 | _____% | _____% |
| 2021-01 至 2022-12 | 震荡+下跌 | _____% | _____% |
| 2023-01 至 2024-12 | 结构性行情 | _____% | _____% |

**🔬 判断：** 如果策略在某个年份亏很多——搞清楚是**策略本身的问题**还是**市场不适合这种策略**。后者可以接受，前者需要优化。

---

### Day 40 — 实盘检查 + 常见坑回顾

**🎯 今日目标：** 做一次全面的实盘检查，回顾所有容易踩的坑

**📝 检查清单：**
- [ ] 模拟盘还在正常运行吗？
- [ ] 实盘账户余额充足吗？
- [ ] 有没有未成交的挂单？
- [ ] 策略参数有没有被改过？
- [ ] 有没有因为"我觉得"而不是信号交易？

**⚠️ 量化交易十大常见坑（过一遍）：**
1. **未来函数** — 用了未来数据（如 shift(-1)）
2. **过拟合** — 参数针对历史数据调得太完美
3. **幸存者偏差** — 只用现在的成分股，忽略了退市的股票
4. **滑点低估** — 回测假设成交价=收盘价，实际差很多
5. **手续费忽略** — 高频策略的手续费可能吃掉所有收益
6. **过度交易** — 信号太多，佣金把利润吃光
7. **情绪干扰** — 亏了不敢跟信号，赚了想多买
8. **路径依赖** — 破产式亏损：一次爆仓就没机会翻盘
9. **黑箱策略** — 自己都说不清楚策略逻辑
10. **忽视流动性** — 小盘股买卖差价大，成交困难

---

### Day 41-42 — 实盘持续跟踪 + 优化

**🎯 今日目标：** 持续跟踪模拟盘和实盘，记录差异

**📝 每天 5 分钟：**
1. 打开模拟盘 → 看今天信号
2. 在券商 App 执行（如果当日有信号）
3. 更新跟踪表
4. 写一行日志：`今天信号=卖出，执行了，滑点0.3%`

---

### Day 43 — 策略改进实验

**🎯 今日目标：** 基于过去两周的模拟盘数据，对策略做一次小改进

**💻 策略改进步骤：**
1. 查看过去两周的模拟盘交易记录
2. 找出亏损最多的 3 笔交易
3. 它们有什么共同点？（同一天？同方向？特定行情？）
4. 想一个改进方案，**跑回测验证**
5. 如果回测改善明显，更新模拟盘策略

**🔬 示例：**
```
问题：双均线在震荡市中连续亏损 4 次
改进：加入 RSI 过滤器，RSI<30 才允许做多
验证：回测中加入 RSI 条件，最大回撤从 18% 降到 12%
```

---

### Day 44 — ✅ 全计划复盘

**🎯 今日任务：** 回顾整个 45 天的学习旅程

**📊 45 天成果清单：**
- [ ] 能独立在 JoinQuant 写策略
- [ ] 跑过至少 5 个完整回测
- [ ] 理解未来函数、过拟合、幸存者偏差
- [ ] 掌握 3+ 种策略类型（趋势/回归/动量/多因子）
- [ ] 建立了风控体系（止损/仓位/回撤）
- [ ] 正在运行模拟盘
- [ ] 实盘在运行（或已完成实盘准备）
- [ ] 建立了交易日志习惯

**❓ 最终复盘问题：**
```
1. 这 45 天最大的收获是什么？
2. 现在回头看第 1 天的你——多了什么能力？
3. 接下来你想研究什么方向？（期权/期货/加密货币/更复杂的多因子/机器学习？）
4. 给 45 天前的自己一句建议。
```

---

### Day 45 — 🎉 毕业日！

**🎯 恭喜！你完成了 45 天量化学习计划！**

你现在能做的事情：
- ✅ 用 JoinQuant 获取数据、计算指标、画图
- ✅ 编写和回测多种策略（趋势、均值回归、动量、多因子）
- ✅ 理解回测报告中的核心指标
- ✅ 建立风控体系
- ✅ 运行模拟盘和实盘

**📌 毕业后的持续建议：**
1. **坚持写交易日志** — 每天 2 分钟，坚持一年
2. **每周复盘** — 周六花 15 分钟看这一周的收益和操作
3. **每月优化** — 小步改进，不要大改策略
4. **一年内不要实盘加钱** — 用 5,000 元跑满一年
5. **读书** — 《打开量化投资的黑箱》《Python 金融大数据分析》

---

## ⚠️ 实操铁律

1. **所有代码都要实际跑一遍**，光看不算学
2. **每改一个参数都要重新跑回测**，不要凭感觉猜结果
3. **亏钱了先问自己"是策略的问题还是我执行的问题"**，不要一亏就改策略
4. **实盘第一笔不超过 5,000 元**，亏完了也不影响生活的金额
5. **每天 10 分钟就够了**，关键是坚持，不是时间长短
6. **压缩了时间但不要压缩动手**——45 天里每一步都要亲手跑

---

*计划最后更新：2026-07-09（从 90 天压缩为 45 天）*
