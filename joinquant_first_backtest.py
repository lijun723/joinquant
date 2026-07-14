"""
JoinQuant（聚宽）第一个回测策略 — 双均线金叉死叉
==============================================
学习计划 Day 5-6 的实操内容。

使用方法：
1. 登录 joinquant.com → 研究平台（Research）
2. 新建策略 → 复制本文件全部内容粘贴到策略编辑器
3. 回测设置：2020-01-01 至 2024-12-31，初始资金 1,000,000
4. 点击「运行回测」

注意：
- JoinQuant 策略环境内置了 order/attribute_history/run_daily 等函数
- 佣金和滑点使用 JoinQuant 默认值（买入万3 + 卖出万3+千1印花税，最低5元）
- 如需自定义佣金设置，查阅 JoinQuant API 文档
"""
import numpy as np
import pandas as pd


def initialize(context):
    """策略初始化"""
    # 交易标的
    g.stock = '000001.XSHE'  # 平安银行（适合练手）
    
    # 每天开盘前运行策略
    run_daily(ma_strategy, time='before_open')
    
    # ----- 佣金与滑点说明 -----
    # JoinQuant 默认已含：买入万3佣金 + 卖出万3佣金+千1印花税，最低5元
    # 足够模拟真实交易成本，无需额外设置
    # 如需自定义，请在 JoinQuant API 文档中搜索 set_commission


def ma_strategy(context):
    """
    双均线策略核心逻辑：
    - MA5 上穿 MA20 → 全仓买入（金叉）
    - MA5 下穿 MA20 → 清仓卖出（死叉）
    
    关键：用 shift(1) 避免未来函数
    """
    stock = g.stock
    
    # 获取过去50个交易日的收盘价
    df = attribute_history(stock, 50, '1d', ['close'])
    if df.empty or len(df) < 3:
        return
    
    close = df['close']
    current_price = close.iloc[-1]
    
    # 计算均线
    ma5 = close.rolling(window=5).mean()
    ma20 = close.rolling(window=20).mean()
    
    # 当日信号 vs 前一日信号（判断交叉）
    today_signal = 1 if ma5.iloc[-1] > ma20.iloc[-1] else 0
    yesterday_signal = 1 if ma5.iloc[-2] > ma20.iloc[-2] else 0
    
    # 获取当前持仓
    current_amount = context.portfolio.positions[stock].amount
    
    # --- 金叉：昨天MA5<=MA20 且 今天MA5>MA20 ---
    if yesterday_signal == 0 and today_signal == 1:
        if current_amount == 0:
            available_cash = context.portfolio.available_cash
            order_value(stock, available_cash)
            log.info(f"📈 金叉买入 {stock} @ {current_price:.2f}")
    
    # --- 死叉：昨天MA5>=MA20 且 今天MA5<MA20 ---
    elif yesterday_signal == 1 and today_signal == 0:
        if current_amount > 0:
            order_target(stock, 0)
            log.info(f"📉 死叉卖出 {stock} @ {current_price:.2f}")
    
    # 每日持仓状态记录（可选）
    if current_amount > 0:
        context.flag = '持仓'
    else:
        context.flag = '空仓'


# =============================================
# 课后练习（Day 6 任务）
# =============================================
#
# 1. 把股票换成 '600519.XSHG'（茅台），重新跑回测
# 2. 把 MA5/MA20 改成 MA10/MA30 和 MA20/MA60，分别跑一次
# 3. 对比三组参数的年化收益率、最大回撤、夏普比率
# 4. 哪组参数最好？为什么？
# 5. 加上 set_commission 看收益缩水了多少
#
# 进阶练习（Week 3 预习）：
# - 加入止损：单笔亏损超过 -8% 时清仓
# - 加入仓位管理：每次只买入可用资金的 80%
