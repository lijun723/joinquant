"""
╔══════════════════════════════════════════════════════════════╗
║  策略一：双均线趋势跟踪（沪深300选股版）                      ║
║  Strategy: Dual Moving Average Trend Following              ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 一、策略原理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  趋势跟踪是量化交易最经典的策略之一，核心思想是 "顺势而为"。

  本策略将双均线交叉系统应用于沪深300成分股的选股：
  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │   金叉买入信号：MA5 上穿 MA20                        │
  │   → 短期均线突破长期均线，趋势向上确立               │
  │   → 说明该股票近期上涨动能强于长期趋势               │
  │                                                     │
  │   死叉卖出信号：MA5 下穿 MA20                        │
  │   → 短期均线跌破长期均线，趋势转弱                   │
  │   → 说明该股票近期下跌动能强于长期趋势               │
  │                                                     │
  └─────────────────────────────────────────────────────┘

  选股方式：
    每周从沪深300的300只成分股中，计算出每只股票的均线交叉信号强度，
    选出金叉信号最强的 TOP N 只等权持有。
    死叉或信号转弱的股票卖出。

  适用市场环境：震荡上涨或单边上涨的牛市 / 结构性行情
  不适用的环境：窄幅横盘震荡（均线频繁交叉，反复打脸）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 二、策略参数
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  参数名          默认值    说明
  ─────────────────────────────────────────
  short_ma           5      短期均线周期（交易日）
  long_ma           20      长期均线周期（交易日）
  top_n             10      持有股票数量
  rebalance_day      1      调仓日（1=周一）
  stop_loss        -8%      单票止损线
  lookback          60      数据回溯天数

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 三、回测设置建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  回测区间：2020-01-01 至 2024-12-31
  初始资金：1,000,000 元
  基准：沪深300指数 (000300.XSHG)
  佣金滑点：使用 JoinQuant 默认值（买入万3 + 卖出万3+千1印花税）

  特别注意：
  - 本策略使用 jqboson 引擎兼容写法
  - 不使用 set_commission / set_slippage（新版引擎已移除）
  - 不使用 get_current_data()[stock].close（改用 attribute_history）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import numpy as np
import pandas as pd


def initialize(context):
    """策略初始化 — 设置参数并注册定时任务"""

    # ═══════════════════════════════════════════════════
    # 策略参数（可调）
    # ═══════════════════════════════════════════════════

    g.index_code = '000300.XSHG'   # 沪深300指数代码
    g.short_ma = 5                 # 短期均线周期
    g.long_ma = 20                 # 长期均线周期
    g.top_n = 10                   # 每次调仓买入的股票数量
    g.rebalance_weekday = 1        # 每周一调仓（1=周一）
    g.lookback = 60                # 回看天数（够计算均线即可）
    g.stop_loss = -0.08            # 单票止损线（-8%）

    # 每周调仓
    run_weekly(rebalance, weekday=g.rebalance_weekday, time='before_open')

    # 每日止损检查
    run_daily(check_stop_loss, time='open')

    # 输出策略信息
    log.info('═' * 50)
    log.info('  策略：双均线趋势跟踪（沪深300选股版）')
    log.info(f'  参数：MA{g.short_ma} / MA{g.long_ma}，持有 TOP {g.top_n}')
    log.info(f'  调仓：每周{g.rebalance_weekday}开盘前，止损：{abs(g.stop_loss)*100:.0f}%')
    log.info('═' * 50)


# ═══════════════════════════════════════════════════════════
# 核心函数一：均线交叉信号计算
# ═══════════════════════════════════════════════════════════

def get_ma_signal(stock):
    """
    计算单只股票的双均线交叉信号。

    信号强度计算方式：
      金叉强度 = (MA5 - MA20) / 当前价格
      值越大 → 金叉越明确，趋势越强

    返回值：
      > 0  → 多头排列或刚金叉，正值越大信号越强
      = 0  → 均线粘合，无明确方向
      < 0  → 空头排列或刚死叉
    """
    df = attribute_history(stock, g.lookback, '1d', ['close'])
    if df.empty or len(df) < g.long_ma + 5:
        return 0.0

    close = df['close']
    ma_short = close.rolling(window=g.short_ma).mean()
    ma_long = close.rolling(window=g.long_ma).mean()

    if len(ma_short) < 2 or len(ma_long) < 2:
        return 0.0

    today_diff = ma_short.iloc[-1] - ma_long.iloc[-1]
    yesterday_diff = ma_short.iloc[-2] - ma_long.iloc[-2]

    current_price = close.iloc[-1]
    if current_price <= 0:
        return 0.0

    # 信号归一化：均线差距 / 价格
    normalized_signal = today_diff / current_price

    # 刚金叉（昨日短<长，今日短>长）→ 加分奖励
    if yesterday_diff <= 0 and today_diff > 0:
        normalized_signal *= 1.5  # 金叉启动点给1.5倍权重

    # 刚死叉（昨日短>长，今日短<长）→ 强负信号
    elif yesterday_diff >= 0 and today_diff < 0:
        normalized_signal *= 2.0  # 死叉点给2倍权重，确保卖出

    return round(normalized_signal, 6)


# ═══════════════════════════════════════════════════════════
# 核心函数二：调仓逻辑
# ═══════════════════════════════════════════════════════════

def rebalance(context):
    """定期调仓：选股 → 卖出 → 买入"""

    # ── Step 1: 获取沪深300成分股 ──
    all_stocks = get_index_stocks(g.index_code)
    if not all_stocks:
        log.warn('⚠️ 无法获取沪深300成分股')
        return
    log.info(f'📊 扫描 {len(all_stocks)} 只成分股...')

    # ── Step 2: 计算每只股票的交叉信号 ──
    candidates = []
    for stock in all_stocks:
        signal = get_ma_signal(stock)
        if signal > 0:  # 只保留多头信号
            candidates.append((stock, signal))

    if not candidates:
        log.info('⏸️ 当前无多头信号股票，空仓等待')
        # 清空所有持仓
        for stock in list(context.portfolio.positions.keys()):
            if context.portfolio.positions[stock].amount > 0:
                order_target(stock, 0)
        return

    # ── Step 3: 按信号强度排序，选 TOP N ──
    candidates.sort(key=lambda x: x[1], reverse=True)
    buy_list = [s[0] for s in candidates[:g.top_n]]

    log.info(f'🏆 选中 TOP {len(buy_list)}：{[s[:6] for s in buy_list]}')

    # ── Step 4: 处理停牌和ST ──
    current_data = get_current_data()
    buy_list = [
        s for s in buy_list
        if s in current_data
        and not current_data[s].paused
        and not current_data[s].is_st
    ]
    log.info(f'✅ 过滤后有效买入：{len(buy_list)} 只')

    # ── Step 5: 卖出不在买入列表的持仓 ──
    for stock in list(context.portfolio.positions.keys()):
        if stock not in buy_list and context.portfolio.positions[stock].amount > 0:
            order_target(stock, 0)
            log.info(f'📉 卖出 {stock}（信号转弱或被替换）')

    # ── Step 6: 买入目标股票 ──
    if not buy_list:
        return

    cash_per_stock = context.portfolio.available_cash / len(buy_list)

    for stock in buy_list:
        if context.portfolio.positions[stock].amount > 0:
            continue  # 已有持仓，不动

        order_value(stock, cash_per_stock)
        price_df = attribute_history(stock, 1, '1d', ['close'])
        current_price = price_df['close'].iloc[-1] if not price_df.empty else 0
        log.info(f'📈 买入 {stock} @ {current_price:.2f}')

    log.info(f'✅ 调仓完成')


# ═══════════════════════════════════════════════════════════
# 核心函数三：止损检查
# ═══════════════════════════════════════════════════════════

def check_stop_loss(context):
    """每日检查持仓止损"""
    for stock in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[stock]
        if position.amount == 0:
            continue

        cost = position.avg_cost
        if cost <= 0:
            continue

        df = attribute_history(stock, 2, '1d', ['close'])
        if df.empty:
            continue

        current_price = df['close'].iloc[-1]
        pnl_pct = (current_price - cost) / cost

        if pnl_pct < g.stop_loss:
            order_target(stock, 0)
            log.info(f'🛑 止损 {stock}（亏 {pnl_pct*100:.1f}%）')


# ═══════════════════════════════════════════════════════════
# 参数优化建议
# ═══════════════════════════════════════════════════════════
#
# 可以尝试的参数组合：
#   1. (5, 20)   → 经典组合，偏短线，交易频率高
#   2. (10, 30)  → 中线组合，减少假信号
#   3. (20, 60)  → 长线组合，捕捉大趋势，交易次数少
#   4. (5, 60)   → 混合组合，金叉条件更严格
#
# 调仓频率：
#   每周调仓 vs 双周调仓 — 双周可以降低交易成本
#
# TOP N 数量：
#   5只（集中） vs 15只（分散）— 集中度越高收益波动越大
