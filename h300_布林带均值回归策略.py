"""
╔══════════════════════════════════════════════════════════════╗
║  策略二：布林带均值回归（沪深300选股版）                      ║
║  Strategy: Bollinger Bands Mean Reversion                   ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 一、策略原理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  均值回归是金融市场的核心规律之一：价格偏离均值越远，回归的概率越大。

  布林带（Bollinger Bands）由三条线组成：
  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │   上轨 = 中轨 + K × 标准差                           │
  │   中轨 = 过去 N 日的简单移动平均线                    │
  │   下轨 = 中轨 - K × 标准差                           │
  │                                                     │
  │   当股价触及下轨 → 超卖，预期反弹 → 买入信号          │
  │   当股价触及上轨 → 超买，预期回调 → 卖出信号          │
  │   股价在中轨附近 → 无操作                            │
  │                                                     │
  └─────────────────────────────────────────────────────┘

  本策略将布林带均值回归应用于沪深300成分股选股：
  - 每日扫描300只成分股，找出股价触及布林带下轨的股票
  - 选出布林带带宽最大的 TOP N 买入（带宽大=波动大=回归空间大）
  - 股价反弹回中轨附近或触及上轨时卖出

  适用市场环境：震荡市（横盘整理、箱体震荡）
  不适用的环境：单边上涨或单边下跌的强趋势行情
  （单边上涨中过早卖出，单边下跌中不断抄底被套）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 二、策略参数
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  参数名            默认值    说明
  ─────────────────────────────────────────────
  boll_period         20      布林带周期（交易日）
  boll_std            2.0     标准差倍数（带宽）
  max_positions        8      最大持仓数
  max_pool_size       50      候选池大小（选带宽最大的）
  profit_target       4%      止盈线（触及下轨买入后涨4%卖出）
  stop_loss          -7%      止损线
  min_bandwidth      0.06     最小带宽阈值（低于此值不买）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 三、回测设置建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  回测区间：2020-01-01 至 2024-12-31
  初始资金：1,000,000 元
  基准：沪深300指数 (000300.XSHG)
  佣金滑点：JoinQuant 默认值

  策略对比注意事项：
  - 均值回归在震荡市中表现优异，但在 2020 和 2024 的上涨行情中可能跑输趋势策略
  - 这是策略本身的特点，不是 bug
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import numpy as np
import pandas as pd


def initialize(context):
    """策略初始化"""

    # ═══════════════════════════════════════════════════
    # 策略参数（可调）
    # ═══════════════════════════════════════════════════

    g.index_code = '000300.XSHG'   # 沪深300
    g.boll_period = 20             # 布林带周期
    g.boll_std = 2.0               # 标准差倍数
    g.max_positions = 8            # 最大持仓数
    g.max_pool_size = 50           # 候选池大小
    g.profit_target = 0.04         # 止盈 4%
    g.stop_loss = -0.07            # 止损 -7%
    g.min_bandwidth = 0.06         # 最小带宽 6%

    # 每天开盘前运行
    run_daily(rebalance, time='before_open')

    log.info('═' * 50)
    log.info('  策略：布林带均值回归（沪深300选股版）')
    log.info(f'  参数：({g.boll_period}, {g.boll_std})，持仓 {g.max_positions} 只')
    log.info(f'  止盈：{g.profit_target*100:.0f}%，止损：{abs(g.stop_loss)*100:.0f}%')
    log.info('═' * 50)


# ═══════════════════════════════════════════════════════════
# 核心函数一：布林带信号计算
# ═══════════════════════════════════════════════════════════

def calc_bollinger(stock):
    """
    计算单只股票的布林带信号。

    计算公式：
      中轨 = close.rolling(period).mean()
      上轨 = 中轨 + std_mult * close.rolling(period).std()
      下轨 = 中轨 - std_mult * close.rolling(period).std()
      带宽 = (上轨 - 下轨) / 中轨（衡量波动率）

    返回值：
      (signal, bandwidth)
      signal = 1  → 买入（触及或跌破下轨）
      signal = -1 → 卖出（触及或突破上轨）
      signal = 0  → 中轨附近，观望
    """
    df = attribute_history(stock, g.boll_period + 10, '1d', ['close'])
    if df.empty or len(df) < g.boll_period:
        return 0, 0.0

    close = df['close']
    current_price = close.iloc[-1]

    # 计算布林带
    middle = close.rolling(g.boll_period).mean().iloc[-1]
    std = close.rolling(g.boll_period).std().iloc[-1]

    if std == 0 or np.isnan(middle) or np.isnan(std):
        return 0, 0.0

    upper = middle + g.boll_std * std
    lower = middle - g.boll_std * std
    bandwidth = (upper - lower) / middle if middle > 0 else 0

    # ── 信号判断（带2%容差避免频繁触发）──
    if current_price <= lower * 1.02:
        # 下轨附近 → 买入信号
        # 带宽越大，说明波动越大，回归空间越大
        return 1, bandwidth

    if current_price >= upper * 0.98:
        # 上轨附近 → 卖出信号
        return -1, bandwidth

    return 0, bandwidth


# ═══════════════════════════════════════════════════════════
# 核心函数二：每日调仓
# ═══════════════════════════════════════════════════════════

def rebalance(context):
    """每日调仓：扫描信号 → 执行买卖"""

    # ── Step 1: 扫描全部成分股 ──
    all_stocks = get_index_stocks(g.index_code)
    if not all_stocks:
        return

    buy_signal_stocks = []
    sell_signal_stocks = []

    for stock in all_stocks:
        signal, bw = calc_bollinger(stock)
        if signal == 1 and bw >= g.min_bandwidth:
            buy_signal_stocks.append((stock, bw))
        elif signal == -1:
            sell_signal_stocks.append(stock)

    log.info(f'📊 布林带信号：买入候选 {len(buy_signal_stocks)} 只，上轨 {len(sell_signal_stocks)} 只')

    # ── Step 2: 从候选池选带宽最大的 ──
    buy_signal_stocks.sort(key=lambda x: x[1], reverse=True)
    buy_candidates = [s[0] for s in buy_signal_stocks]

    # 过滤停牌和ST
    current_data = get_current_data()
    buy_candidates = [
        s for s in buy_candidates
        if s in current_data
        and not current_data[s].paused
        and not current_data[s].is_st
        and not s.startswith('688')  # 排除科创板
    ]

    final_buy = buy_candidates[:g.max_positions]
    log.info(f'🎯 最终买入：{len(final_buy)} 只')

    # ── Step 3: 卖出逻辑 ──
    for stock in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[stock]
        if position.amount == 0:
            continue

        df = attribute_history(stock, 2, '1d', ['close'])
        if df.empty:
            continue

        current_price = df['close'].iloc[-1]
        cost = position.avg_cost
        if cost <= 0:
            continue

        pnl_pct = (current_price - cost) / cost
        should_sell = False
        reason = ''

        # 条件A：触及上轨
        if stock in sell_signal_stocks:
            should_sell = True
            reason = '触及上轨'
        # 条件B：止盈
        elif pnl_pct >= g.profit_target:
            should_sell = True
            reason = f'止盈({pnl_pct*100:.1f}%)'
        # 条件C：止损
        elif pnl_pct <= g.stop_loss:
            should_sell = True
            reason = f'止损({pnl_pct*100:.1f}%)'

        if should_sell:
            order_target(stock, 0)
            log.info(f'📉 卖出 {stock} — {reason}')

    # ── Step 4: 买入逻辑 ──
    if not final_buy:
        return

    cash_per_stock = context.portfolio.available_cash / len(final_buy)

    for stock in final_buy:
        if context.portfolio.positions[stock].amount > 0:
            continue  # 已持有

        order_value(stock, cash_per_stock)
        price_df = attribute_history(stock, 1, '1d', ['close'])
        current_price = price_df['close'].iloc[-1] if not price_df.empty else 0
        log.info(f'📈 买入 {stock} @ {current_price:.2f}（布林带下轨）')


# ═══════════════════════════════════════════════════════════
# 参数优化建议
# ═══════════════════════════════════════════════════════════
#
# 可尝试的参数组合：
#   1. (20, 2.0) → 经典组合，适用大多数情况
#   2. (10, 2.5) → 更敏感，适合短线
#   3. (50, 2.0) → 更平滑，适合中线
#   4. (20, 1.5) → 带宽窄，信号更多但假信号也多
#
# 止盈止损优化：
#   止盈 3% vs 6%
#   止损 5% vs 10%
#   最优组合取决于市场波动率
#
# 带宽过滤：
#   min_bandwidth = 0.10 → 只做高波动股票
#   min_bandwidth = 0.05 → 低波动也做
