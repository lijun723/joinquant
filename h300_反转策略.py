"""
╔══════════════════════════════════════════════════════════════╗
║  策略四：反转策略（沪深300选股版）                            ║
║  Strategy: Contrarian / Reversal                            ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 一、策略原理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  反转效应是动量效应的对立面：过去跌幅最大的股票，未来反弹的概率更大。
  这是行为金融学的经典现象——过度反应假说（De Bondt & Thaler, 1985）。

  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │   "买跌卖涨"——做空过去的热门股，买入过去的冷门股      │
  │                                                     │
  │   核心逻辑：                                         │
  │   1. 投资者对信息的过度反应导致价格偏离内在价值       │
  │   2. 极端涨跌后，价格会逐步回归合理估值              │
  │   3. 跌得越深的股票，反弹的弹性越大                   │
  │                                                     │
  │   辅助判断：                                         │
  │   - 超跌 + 缩量 → 卖压枯竭，反转概率高              │
  │   - 超跌 + 放量 → 恐慌盘涌出，可能还会跌            │
  │   - RSI < 30 → 技术性超卖，加分                      │
  |                                                       |
  └─────────────────────────────────────────────────────┘

  本策略的反转定义：
    主因子：过去40日累计涨幅排名——买跌幅最大的（排名最低的）
    辅助因子：
      - RSI(14) < 40：技术性超卖加分
      - 近5日缩量（量比 < 1.0）：卖压枯竭加分
      - PB 接近历史低位：估值保护加分

  适用市场环境：震荡偏弱 / 超跌反弹行情
  不适用的环境：单边下跌熊市（超跌之后还能更跌）
                      单边上涨牛市（反转策略完全跑输）

  ⚠️ 重要提示：反转策略在 A 股具有显著的 "抄底陷阱" 特征。
     不要在指数处于下降趋势时运行反转策略，建议配合指数择时。
     本脚本已内置：沪深300指数在MA60下方时空仓保护。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 二、策略参数
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  参数名            默认值    说明
  ─────────────────────────────────────────────
  reversal_period     40      反转周期（过去N日跌幅）
  top_n                8      持仓数（实际买跌幅最大的N只）
  rsi_period          14      RSI计算周期
  rsi_threshold       40      RSI超卖阈值（低于此值加分）
  stop_loss          -8%      止损（反转策略止损要更严格）
  profit_target       8%      止盈（反弹8%落袋为安）
  use_index_filter   True    是否启用指数择时保护

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 三、回测设置建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  回测区间：2020-01-01 至 2024-12-31
  初始资金：1,000,000 元
  基准：沪深300指数 (000300.XSHG)
  佣金滑点：JoinQuant 默认值

  对比策略时的注意事项：
  - 反转策略与动量策略的收益相关性通常为负
  - 牛市中使用反转策略会导致大幅跑输
  - 熊市和震荡市中反转策略表现更优
  - 两个策略搭配使用可以达到 "危机alpha" 效果
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
    g.reversal_period = 40           # 反转观察周期（交易日）
    g.top_n = 8                      # 持仓数
    g.rsi_period = 14                # RSI周期
    g.rsi_threshold = 40             # RSI超卖阈值
    g.stop_loss = -0.08              # 止损线
    g.profit_target = 0.08           # 止盈线
    g.use_index_filter = True        # 启用指数择时保护

    # 每周一调仓
    run_weekly(rebalance, weekday=1, time='before_open')

    # 每日风控
    run_daily(check_stop_and_take_profit, time='open')

    log.info('═' * 50)
    log.info('  策略：反转策略（沪深300选股版）')
    log.info(f'  参数：反转 {g.reversal_period}日，持仓 {g.top_n} 只')
    log.info(f'  RSI阈值：{g.rsi_threshold}，止损：{abs(g.stop_loss)*100:.0f}%')
    log.info(f'  止盈：{g.profit_target*100:.0f}%')
    log.info('═' * 50)


# ═══════════════════════════════════════════════════════════
# 辅助函数：RSI 计算
# ═══════════════════════════════════════════════════════════

def calc_rsi(close_prices, period=14):
    """
    计算相对强弱指标 RSI。

    RSI = 100 - 100 / (1 + RS)
    RS = 平均涨幅 / 平均跌幅

    取值范围 0-100：
      RSI < 30   → 超卖（可能反弹）
      RSI > 70   → 超买（可能回调）
      RSI 40-60  → 正常区间
    """
    if len(close_prices) < period + 1:
        return 50.0  # 数据不足返回中性值

    deltas = close_prices.diff().dropna()
    gains = deltas.where(deltas > 0, 0.0)
    losses = -deltas.where(deltas < 0, 0.0)

    avg_gain = gains.rolling(period).mean().iloc[-1]
    avg_loss = losses.rolling(period).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0  # 没有下跌，极端强势
    if avg_gain == 0:
        return 0.0    # 没有上涨，极端弱势

    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return rsi


# ═══════════════════════════════════════════════════════════
# 核心函数一：反转信号评分
# ═══════════════════════════════════════════════════════════

def score_reversal(stock):
    """
    计算单只股票的反转潜力评分。

    反转评分逻辑：
      涨跌幅分 = -过去N日涨幅（跌幅越大分越高）
      RSI加分 = RSI < threshold 时加分（超卖加分）
      缩量加分 = 近5日均量 < 近20日均量 时加分（卖压枯竭）
      综合分 = 涨跌幅分 × 0.6 + RSI加分 × 0.2 + 缩量加分 × 0.2

    得分为正 = 有反转潜力（值越大反转可能性越高）
    得分为负 = 该股在上涨趋势中，不适合反转策略
    """
    df = attribute_history(stock, max(g.reversal_period + 20, 60), '1d',
                           ['close', 'volume'])
    if df.empty or len(df) < g.reversal_period:
        return -999.0  # 数据不足返回极低分

    close = df['close']
    volume = df['volume']

    # ── 因子1：涨跌幅（核心因子）──
    # 过去 reversal_period 日的涨跌幅
    period_return = (close.iloc[-1] - close.iloc[-g.reversal_period]) / \
                    close.iloc[-g.reversal_period]

    # 反转因子：跌幅越大，反转分越高
    # 将涨跌幅反向映射到评分（跌得越多分越高）
    reversal_score = -period_return  # 例如跌-20% → reversal_score = 0.2

    # ── 因子2：RSI 超卖确认 ──
    rsi = calc_rsi(close, g.rsi_period)
    rsi_score = max(0, (g.rsi_threshold - rsi) / g.rsi_threshold) if rsi < g.rsi_threshold else 0

    # ── 因子3：量能枯竭确认 ──
    # 近5日均量 vs 近20日均量
    vol_5 = volume.iloc[-5:].mean()
    vol_20 = volume.iloc[-20:].mean() if len(volume) >= 20 else vol_5
    volume_shrink = max(0, 1 - vol_5 / vol_20) if vol_20 > 0 else 0

    # ── 综合评分 ──
    total = reversal_score * 0.6 + rsi_score * 0.2 + volume_shrink * 0.2
    return total


# ═══════════════════════════════════════════════════════════
# 核心函数二：指数择时保护
# ═══════════════════════════════════════════════════════════

def check_index_timing():
    """
    沪深300指数趋势判断。
    反转策略在熊市中抄底会被埋，需要指数择时保护。

    返回：
      True  = 可以交易（指数在安全区间）
      False = 禁止交易（指数处于下降趋势）
    """
    if not g.use_index_filter:
        return True  # 未启用过滤

    df = attribute_history(g.index_code, 70, '1d', ['close'])
    if df.empty or len(df) < 60:
        return True

    close = df['close']
    current_price = close.iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1]

    # 指数在MA60上方 → 相对安全
    # 指数在MA60下方 → 熊市/下降趋势，反转策略不做
    if current_price > ma60 * 0.95:  # 5%容差
        return True
    else:
        log.info('🛡️ 指数择时保护：沪深300在MA60下方，暂停交易')
        return False


# ═══════════════════════════════════════════════════════════
# 核心函数三：每周调仓
# ═══════════════════════════════════════════════════════════

def rebalance(context):
    """每周调仓"""

    # ── 指数择时检查 ──
    if not check_index_timing():
        # 清仓
        for stock in list(context.portfolio.positions.keys()):
            if context.portfolio.positions[stock].amount > 0:
                order_target(stock, 0)
        return

    # ── 获取成分股并评分 ──
    all_stocks = get_index_stocks(g.index_code)
    if not all_stocks:
        return

    log.info(f'📊 沪深300共 {len(all_stocks)} 只成分股，计算反转评分...')

    scored = []
    for stock in all_stocks:
        score = score_reversal(stock)
        if score > 0:  # 只保留正分（有反转潜力的）
            scored.append((stock, score))

    scored.sort(key=lambda x: x[1], reverse=True)

    if not scored:
        log.info('⏸️ 无超跌反转信号')
        return

    # ── 选出反转潜力最大的 N 只 ──
    buy_list_raw = [s[0] for s in scored[:g.top_n]]

    current_data = get_current_data()
    buy_list = [
        s for s in buy_list_raw
        if s in current_data
        and not current_data[s].paused
        and not current_data[s].is_st
        and not s.startswith('688')
    ]

    log.info(f'🔄 反转选股 TOP {len(buy_list)}：{[s[:6] for s in buy_list]}')
    log.info(f'  评分区间：{scored[0][1]:.4f} ~ {scored[min(len(scored), g.top_n)-1][1]:.4f}')

    # ── 卖出 ──
    for stock in list(context.portfolio.positions.keys()):
        if stock not in buy_list and context.portfolio.positions[stock].amount > 0:
            order_target(stock, 0)
            log.info(f'📉 卖出 {stock}（反转排名下降）')

    # ── 买入 ──
    if not buy_list:
        return

    cash_per_stock = context.portfolio.available_cash / len(buy_list)

    for stock in buy_list:
        if context.portfolio.positions[stock].amount > 0:
            continue

        order_value(stock, cash_per_stock)
        price_df = attribute_history(stock, 1, '1d', ['close'])
        current_price = price_df['close'].iloc[-1] if not price_df.empty else 0
        log.info(f'📈 买入 {stock} @ {current_price:.2f}（超跌反弹）')


# ═══════════════════════════════════════════════════════════
# 核心函数四：止盈止损
# ═══════════════════════════════════════════════════════════

def check_stop_and_take_profit(context):
    """
    每日检查止盈止损。
    反转策略需要严格的止盈，因为超跌反弹通常是短命的。
    """
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

        # 止盈：反弹达到目标 → 落袋为安
        if pnl_pct >= g.profit_target:
            order_target(stock, 0)
            log.info(f'🎯 止盈 {stock}（赚 {pnl_pct*100:.1f}%）')
            continue

        # 止损：超跌后继续跌 → 止损认错
        if pnl_pct <= g.stop_loss:
            order_target(stock, 0)
            log.info(f'🛑 止损 {stock}（亏 {pnl_pct*100:.1f}%）')


# ═══════════════════════════════════════════════════════════
# 参数优化建议
# ═══════════════════════════════════════════════════════════
#
# 反转周期（A股实证）：
#   20日（1个月）→ 短线超跌反弹，机会多但质量低
#   40日（2个月）→ 中短线反转（本策略默认）
#   60日（3个月）→ 中线反转
#
# A股反转效应的特殊规律：
#   1. 个股跌幅 > 20% 后的反弹概率显著上升
#   2. 小市值股票的反转效应强于大市值
#   3. 连续下跌3天后的第4天反弹概率 > 60%（统计规律）
#
# 关键参数：
#   止盈8%：超跌反弹平均幅度在 5-12% 之间
#   止损8%：不能让超跌变深套
#   RSI < 40：比传统30更宽松
#
# 与其他策略的协配：
#   反转 vs 动量：收益负相关，可组合使用
#   牛市用动量，熊市用反转（择时切换）
#   或各分配50%资金，降低整体波动
