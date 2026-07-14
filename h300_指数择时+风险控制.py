"""
沪深300指数择时 + 个股风险控制策略
===================================
核心逻辑：两层架构
  Layer 1 — 指数择时：根据沪深300指数本身的 MA20/MA60 决定仓位系数
  Layer 2 — 个股轮动：在允许仓位内，持有动量最强的沪深300成分股
  Layer 3 — 个股止损：单票亏损超限强制清仓

仓位系数：
  - 指数在 MA60 上方且 MA20 > MA60（多头排列）→ 满仓 100%
  - 指数在 MA60 上方但 MA20 < MA60（震荡偏多）→ 半仓 50%
  - 指数在 MA60 下方且 MA20 < MA60（空头排列）→ 空仓 0%
  - 指数在 MA60 下方但 MA20 > MA60（震荡偏空）→ 30% 仓位

使用方法：
1. 登录 joinquant.com → 研究平台 → 新建策略
2. 粘贴全部内容
3. 回测设置：2018-01-01 至 2024-12-31，初始资金 1,000,000
4. 点击「运行回测」

JoinQuant 新版引擎 (jqboson) 注意事项：
- 不要调用 set_commission / set_slippage（使用默认值）
- 不要使用 get_current_data()[stock].close
- 回调函数签名：def func(context): 只传 context
"""

import numpy as np
import pandas as pd


def initialize(context):
    """策略初始化"""
    # ---------- 参数 ----------
    g.index_code = '000300.XSHG'     # 沪深300指数
    g.stock_pool = '000300.XSHG'     # 选股池（也是沪深300成分股）
    g.top_n = 5                      # 持仓数量
    g.momentum_days = 40             # 个股动量周期
    g.ma_short = 20                  # 指数短期均线
    g.ma_long = 60                   # 指数长期均线
    g.rebalance_weekday = 1          # 每周一调仓
    g.stop_loss = -0.08              # 个股止损
    g.trailing_stop = -0.12          # 移动止损（从持仓最高点回撤）

    # 每周调仓
    run_weekly(rebalance, weekday=g.rebalance_weekday, time='before_open')

    # 每日止损 + 更新移动止损
    run_daily(risk_management, time='open')

    log.info(f"🚀 沪深300指数择时+风控策略初始化完成")
    log.info(f"   择时: MA{g.ma_short}/MA{g.ma_long}, 选股: TOP {g.top_n}")
    log.info(f"   止损: {g.stop_loss*100:.0f}%, 移动止损: {g.trailing_stop*100:.0f}%")


def get_index_timing(context):
    """
    沪深300指数择时判断。
    返回: position_ratio — 仓位系数 [0.0, 1.0]
    """
    df = attribute_history(g.index_code, g.ma_long + 10, '1d', ['close'])
    if df.empty or len(df) < g.ma_long:
        return 1.0  # 数据不足时默认满仓

    close = df['close']
    current_price = close.iloc[-1]

    ma_short = close.rolling(g.ma_short).mean().iloc[-1]
    ma_long = close.rolling(g.ma_long).mean().iloc[-1]

    above_ma60 = current_price > ma_long
    short_above_long = ma_short > ma_long

    # 四象限仓位判断
    if above_ma60 and short_above_long:
        # 多头排列：指数在MA60上，且MA20>MA60 → 满仓
        ratio = 1.0
        signal = "📗 多头排列 — 满仓"
    elif above_ma60 and not short_above_long:
        # 震荡偏多：指数在MA60上，但MA20<MA60 → 半仓
        ratio = 0.5
        signal = "🟡 震荡偏多 — 半仓"
    elif not above_ma60 and not short_above_long:
        # 空头排列：指数在MA60下，且MA20<MA60 → 空仓
        ratio = 0.0
        signal = "📕 空头排列 — 空仓"
    else:
        # 震荡偏空：指数在MA60下，但MA20>MA60 → 30%仓位
        ratio = 0.3
        signal = "🟠 震荡偏空 — 轻仓"

    log.info(f"📊 指数择时: {signal} (沪深300@ {current_price:.0f}, MA{g.ma_short}={ma_short:.0f}, MA{g.ma_long}={ma_long:.0f})")
    return ratio


def select_top_momentum_stocks(stocks, n):
    """从股票池中选动量最强的 N 只"""
    scored = []
    for stock in stocks:
        df = attribute_history(stock, g.momentum_days + 5, '1d', ['close', 'volume'])
        if df.empty or len(df) < g.momentum_days:
            continue

        close = df['close']
        # 过去40日收益率
        momentum = (close.iloc[-1] - close.iloc[-g.momentum_days]) / close.iloc[-g.momentum_days]
        # 量比辅助
        vol_ratio = df['volume'].iloc[-10:].mean() / df['volume'].iloc[-40:-10].mean() if len(df) >= 40 else 1.0
        vol_score = min(vol_ratio, 2.0) / 2.0

        # 综合得分（动量为主）
        score = momentum * 0.7 + vol_score * 0.3
        scored.append((stock, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:n]]


def rebalance(context):
    """每周调仓——指数择时 + 个股轮动"""
    # ---- Layer 1: 指数择时 ----
    position_ratio = get_index_timing(context)

    total_value = context.portfolio.total_value
    target_cash = total_value * (1 - position_ratio)

    # 计算当前现金是否匹配目标仓位
    current_cash = context.portfolio.available_cash

    if position_ratio == 0.0:
        # 空仓信号：清仓所有股票
        for stock in list(context.portfolio.positions.keys()):
            if context.portfolio.positions[stock].amount > 0:
                order_target(stock, 0)
        log.info("⏸️ 指数择时空仓，全部卖出")
        return

    # ---- Layer 2: 个股轮动 ----
    all_stocks = get_index_stocks(g.stock_pool)
    if not all_stocks:
        return

    top_stocks = select_top_momentum_stocks(all_stocks, g.top_n * 2)

    # 过滤
    current_data = get_current_data()
    top_stocks = [
        s for s in top_stocks
        if s in current_data and not current_data[s].paused
        and not current_data[s].is_st and not s.startswith('688')
    ]
    top_stocks = top_stocks[:g.top_n]

    if not top_stocks:
        return

    current_positions = list(context.portfolio.positions.keys())

    # --- 卖出（不在TOP列表中的持仓）---
    for stock in current_positions:
        if stock not in top_stocks:
            if context.portfolio.positions[stock].amount > 0:
                order_target(stock, 0)
                log.info(f"📉 卖出 {stock} (动量轮出)")

    # --- 买入 ---
    available_for_stocks = context.portfolio.available_cash
    if available_for_stocks <= 0:
        return

    cash_per_stock = available_for_stocks / len(top_stocks)

    for stock in top_stocks:
        if context.portfolio.positions[stock].amount > 0:
            continue

        # 如果指数择时是半仓，每只股票只分配 target_cash 的份额
        actual_buy = cash_per_stock * position_ratio

        order_value(stock, actual_buy)
        price_df = attribute_history(stock, 1, '1d', ['close'])
        log.info(f"📈 买入 {stock} @ {price_df['close'].iloc[-1]:.2f} (仓位系数 {position_ratio:.0%})")

    log.info(f"✅ 调仓完成 — 持仓 {len(top_stocks)} 只, 仓位系数 {position_ratio:.0%}")


def risk_management(context):
    """每日风控：固定止损 + 移动止损"""
    for stock in list(context.portfolio.positions.keys()):
        position = context.portfolio.positions[stock]
        if position.amount == 0:
            continue

        cost = position.avg_cost
        if cost <= 0:
            continue

        df = attribute_history(stock, 5, '1d', ['close', 'high'])
        if df.empty:
            continue

        current_price = df['close'].iloc[-1]
        pnl_pct = (current_price - cost) / cost

        # 条件1：固定止损（从成本价计算）
        if pnl_pct <= g.stop_loss:
            order_target(stock, 0)
            log.info(f"🛑 固定止损 {stock} (亏损 {pnl_pct*100:.1f}%)")
            continue

        # 条件2：移动止损（从持仓期间最高价计算）
        # 记录持仓期间最高价
        high_since_entry = df['high'].max()
        drawdown_from_peak = (current_price - high_since_entry) / high_since_entry

        if drawdown_from_peak <= g.trailing_stop:
            order_target(stock, 0)
            profit_pct = (current_price - cost) / cost * 100
            log.info(f"🎯 移动止损 {stock} (从最高 {high_since_entry:.2f} 回撤 {abs(drawdown_from_peak)*100:.1f}%, 盈亏 {profit_pct:.1f}%)")


# =============================================
# 课后练习
# =============================================
# 1. 试试不同的择时参数：MA10/MA30 和 MA30/MA90——哪个在市场大跌时保护更好？
# 2. 把个股轮动改成持有沪深300 ETF（510300）而非选股，对比收益
# 3. 移动止损的 trailing_stop 改成 -8% 和 -15%，哪个平衡点最好？
# 4. 加入一个「加息环境」判断：当10年期国债收益率 > 3.5%时强制半仓
#    提示：get_bond_info() 或手动宏观判断
# 5. 把这个策略的择时部分单独提取成研究环境脚本，画图看每次调仓点的位置
#    代码参考研究环境模板
