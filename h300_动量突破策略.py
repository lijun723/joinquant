"""
╔══════════════════════════════════════════════════════════════╗
║  策略三：动量突破策略（沪深300选股版）                        ║
║  Strategy: Momentum Breakout                                ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 一、策略原理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  动量效应（Momentum Effect）是量化金融中最经典的异象之一，
  由 Jegadeesh & Titman (1993) 首次系统论证。

  核心思想：过去表现好的股票，未来一段时间内继续表现好的概率更大。
  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │   "强者恒强，弱者恒弱"                               │
  │                                                     │
  │   每月买入过去 N 日涨幅最大的 TOP K 只股票           │
  │   卖出不再位于 TOP 列表的股票                        │
  │                                                     │
  │   辅助因子：成交量放大 = 趋势确认信号                 │
  │   动量 + 放量同时成立 → 突破更可靠                   │
  │                                                     │
  └─────────────────────────────────────────────────────┘

  本策略的动量定义：
    主因子：过去60日累计涨幅（总收益率）
    辅助因子：近20日均量 / 前40日均量（量比）
    综合得分 = 动量分 × 0.7 + 量比分 × 0.3

  适用市场环境：单边上涨趋势 / 结构性牛市
  不适用的环境：剧烈反转的震荡市（动量策略容易追高被套）

  经典的 "12M-1M" 动量策略是持有过去12个月（剔除最近1个月）
  涨幅最大的股票。本策略简化为60日（≈3个月）以适应A股换手率
  较高的特点。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 二、策略参数
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  参数名            默认值    说明
  ─────────────────────────────────────────────
  momentum_period     60      动量周期（交易日，≈3个月）
  top_n                8      持仓数量
  rebalance_day        1      每月1号调仓
  volume_lookback     20      成交量均线周期
  stop_loss          -10%     止损线
  min_momentum         0      最小动量阈值（负动能不买）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 三、回测设置建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  回测区间：2018-01-01 至 2024-12-31
  初始资金：1,000,000 元
  基准：沪深300指数 (000300.XSHG)
  佣金滑点：JoinQuant 默认值

  注意：
  - 动量策略在 A 股存在显著的反转效应，月度调仓比周度更合适
  - 建议拉长回测区间到 7-10 年，观察策略在不同牛熊周期中的表现
  - 2021 年之后 A 股结构性行情中动量策略表现分化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import numpy as np
import pandas as pd


def initialize(context):
    """策略初始化"""

    # ═══════════════════════════════════════════════════
    # 策略参数（可调）
    # ═══════════════════════════════════════════════════

    g.index_code = '000300.XSHG'     # 沪深300
    g.momentum_period = 60           # 动量周期（60个交易日 ≈ 3个月）
    g.top_n = 8                      # 持仓数量
    g.rebalance_day = 1              # 每月1号调仓
    g.volume_lookback = 20           # 成交量均线周期
    g.stop_loss = -0.10              # 止损线 -10%
    g.min_momentum = 0.0             # 最小动量（负动量不买）

    # 每月调仓
    run_monthly(rebalance, monthday=g.rebalance_day, time='before_open')

    # 每日止损
    run_daily(check_stop_loss, time='open')

    log.info('═' * 50)
    log.info('  策略：动量突破（沪深300选股版）')
    log.info(f'  参数：动量 {g.momentum_period}日，持有 TOP {g.top_n}')
    log.info(f'  调仓：每月{g.rebalance_day}号，止损 {abs(g.stop_loss)*100:.0f}%')
    log.info('═' * 50)


# ═══════════════════════════════════════════════════════════
# 核心函数一：动量评分
# ═══════════════════════════════════════════════════════════

def score_momentum(stock):
    """
    计算单只股票的动量综合得分。

    评分公式：
      动量分 = (当前价 - momentum_period天前价格) / momentum_period天前价格
      量比分 = min(近20日平均成交量 / 前40日平均成交量, 2.0) / 2.0
      综合分 = 动量分 × 0.7 + 量比分 × 0.3

    动量因子理论依据：
    - Jegadeesh & Titman (1993): 3-12个月动量显著为正
    - A股实证：3个月动量效果最好，12个月存在反转

    成交量辅助逻辑：
    - 动量 + 放量 = 真实突破（有资金推动）
    - 动量 + 缩量 = 虚涨（可能是庄股或流动性陷阱）
    """
    df = attribute_history(stock, g.momentum_period + 30, '1d',
                           ['close', 'volume'])
    if df.empty or len(df) < g.momentum_period:
        return -999.0

    close = df['close']

    # ── 主因子：N日累计收益率 ──
    total_return = (close.iloc[-1] - close.iloc[-g.momentum_period]) / \
                   close.iloc[-g.momentum_period]

    # ── 辅助因子：量比 ──
    # 近期成交量均值 vs 更早期的成交量均值
    recent_vol = df['volume'].iloc[-g.volume_lookback:].mean()
    hist_vol = df['volume'].iloc[-(g.momentum_period):-g.volume_lookback].mean()

    # 应对数据不足的情况
    if np.isnan(hist_vol) or hist_vol <= 0:
        hist_vol = recent_vol

    vol_ratio = recent_vol / hist_vol if hist_vol > 0 else 1.0
    vol_score = min(vol_ratio, 2.0) / 2.0  # 归一化到 [0, 1]

    # ── 综合评分 ──
    score = total_return * 0.7 + vol_score * 0.3
    return score


# ═══════════════════════════════════════════════════════════
# 核心函数二：月度调仓
# ═══════════════════════════════════════════════════════════

def rebalance(context):
    """每月调仓：扫描 → 评分 → 排名 → 买卖"""

    # ── Step 1: 获取成分股并评分 ──
    all_stocks = get_index_stocks(g.index_code)
    if not all_stocks:
        log.warn('⚠️ 无法获取沪深300成分股')
        return

    log.info(f'📊 沪深300共 {len(all_stocks)} 只成分股，开始动量评分...')

    scored = []
    for stock in all_stocks:
        score = score_momentum(stock)
        if score > g.min_momentum:  # 只保留正动量
            scored.append((stock, score))

    # 按得分降序排列
    scored.sort(key=lambda x: x[1], reverse=True)

    if not scored:
        log.info('⏸️ 无正动量股票，空仓等待')
        for stock in list(context.portfolio.positions.keys()):
            if context.portfolio.positions[stock].amount > 0:
                order_target(stock, 0)
        return

    # ── Step 2: 选出 TOP N ──
    top_stocks_raw = [s[0] for s in scored[:g.top_n]]
    log.info(f'🏆 TOP {g.top_n}：{[s[:6] for s in top_stocks_raw]}')
    log.info(f'  动量得分区间：{scored[0][1]:.4f} ~ {scored[min(len(scored), g.top_n)-1][1]:.4f}')

    # ── Step 3: 过滤停牌和ST ──
    current_data = get_current_data()
    
    if top_stocks_raw:
        test_stock = top_stocks_raw[0]
        test_result = '访问成功'
        try:
            test_data = current_data[test_stock]
            if test_data:
                test_result = f'paused={test_data.paused}, is_st={test_data.is_st}'
            else:
                test_result = '数据为空'
        except Exception as e:
            test_result = f'访问失败({str(e)[:20]})'
        log.info(f'🔧 current_data类型={type(current_data).__name__}, '
                 f'测试股票{test_stock[:6]}结果={test_result}')
    
    top_stocks = []
    filtered_details = []
    for s in top_stocks_raw:
        try:
            stock_data = current_data[s]
        except Exception as e:
            filtered_details.append(f'{s[:6]}: 访问失败({str(e)[:20]})')
            continue
        
        if stock_data is None:
            filtered_details.append(f'{s[:6]}: 数据为空')
            continue
        
        try:
            is_paused = stock_data.paused
            is_st = stock_data.is_st
        except Exception as e:
            filtered_details.append(f'{s[:6]}: 属性访问失败({str(e)[:20]})')
            continue
        
        if is_paused:
            filtered_details.append(f'{s[:6]}: 停牌')
            continue
        if is_st:
            filtered_details.append(f'{s[:6]}: ST股')
            continue
        
        top_stocks.append(s)
    
    if filtered_details:
        log.info(f'🔍 被过滤的股票：{", ".join(filtered_details)}')
    
    log.info(f'✅ 过滤后有效买入：{len(top_stocks)} 只')

    # ── Step 4: 卖出 ──
    for stock in list(context.portfolio.positions.keys()):
        if stock not in top_stocks and context.portfolio.positions[stock].amount > 0:
            order_target(stock, 0)
            log.info(f'📉 卖出 {stock}（排名下降）')

    # ── Step 5: 买入 ──
    if not top_stocks:
        return

    cash_per_stock = context.portfolio.available_cash / len(top_stocks)

    for stock in top_stocks:
        if context.portfolio.positions[stock].amount > 0:
            continue

        order_value(stock, cash_per_stock)
        price_df = attribute_history(stock, 1, '1d', ['close'])
        current_price = price_df['close'].iloc[-1] if not price_df.empty else 0
        log.info(f'📈 买入 {stock} @ {current_price:.2f}')

    log.info(f'✅ 调仓完成')


# ═══════════════════════════════════════════════════════════
# 核心函数三：止损
# ═══════════════════════════════════════════════════════════

def check_stop_loss(context):
    """每日止损检查"""
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

        pnl = (df['close'].iloc[-1] - cost) / cost
        if pnl < g.stop_loss:
            order_target(stock, 0)
            log.info(f'🛑 止损 {stock}（亏 {pnl*100:.1f}%）')


# ═══════════════════════════════════════════════════════════
# 参数优化建议
# ═══════════════════════════════════════════════════════════
#
# 动量周期对比（关键参数）：
#   20日（≈1个月）→ 极其短线，交易频率高
#   60日（≈3个月）→ 经典中短线（本策略默认）
#   120日（≈6个月）→ 中线
#   240日（≈12个月）→ 长线
#
# A股动量 vs 反转：
#   短周期（<1个月）：A股呈现反转效应（涨多了跌）
#   中周期（3-6个月）：A股呈现动量效应
#   长周期（>12个月）：A股呈现反转效应
#   所以动量周期设置在 40-80 日效果最好
#
# 调仓频率影响：
#   月度调仓已足够，周度调仓交易成本太高
#   可以考虑双月调仓降低换手率
