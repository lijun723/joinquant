"""
沪深300成分股多因子评分选股策略
================================
核心逻辑：每月从沪深300成分股中，综合基本面因子（PE、ROE、利润增速）
和技术面因子（动量、波动率、换手率）进行打分，选 TOP 8 买入。

评分权重：
- 基本面 50%: PE百分位(15%) + ROE(20%) + 净利润增速(15%)
- 技术面 50%: 60日动量(20%) + 低波动率(15%) + 成交量变化(15%)

使用方法：
1. 登录 joinquant.com → 研究平台 → 新建策略
2. 粘贴全部内容
3. 回测设置：2020-01-01 至 2024-12-31，初始资金 1,000,000
4. 点击「运行回测」

JoinQuant 新版引擎 (jqboson) 注意事项：
- 不要调用 set_commission / set_slippage
- 不要使用 get_current_data()[stock].close
- 回调函数签名：def func(context): 只传 context
"""

import numpy as np
import pandas as pd


def initialize(context):
    """策略初始化"""
    # ---------- 参数 ----------
    g.index_code = '000300.XSHG'     # 沪深300
    g.top_n = 8                      # 持仓数
    g.momentum_days = 60             # 动量周期
    g.rebalance_day = 1              # 每月1号调仓
    g.stop_loss = -0.10              # 止损

    # 每月调仓
    run_monthly(rebalance, monthday=g.rebalance_day, time='before_open')

    # 每日止损
    run_daily(stop_loss_check, time='open')

    log.info(f"🚀 沪深300多因子评分选股策略初始化完成")
    log.info(f"   选股数: {g.top_n}, 调仓频率: 月频")


def get_fundamental_factors(stocks):
    """
    批量获取基本面因子。
    返回 dict: {stock: {pe_pctile, roe_score, profit_growth}}
    """
    result = {}

    # 获取市盈率估值数据
    df_val = get_fundamentals(query(
        valuation.code,
        valuation.pe_ratio,
        valuation.market_cap,
        valuation.pb_ratio
    ).filter(
        valuation.code.in_(stocks)
    ))

    # 获取盈利能力
    df_ind = get_fundamentals(query(
        valuation.code,
        indicator.roe,                              # ROE
        indicator.roic,                             # 投入资本回报率
        indicator.inc_net_profit_annual,            # 年净利润增速
        indicator.gross_profit_margin               # 毛利率
    ).filter(
        valuation.code.in_(stocks)
    ))

    if df_val.empty or df_ind.empty:
        return {}

    # 合并数据
    merged = df_val.merge(df_ind, on='code', how='inner')

    if merged.empty:
        return {}

    # 计算PE百分位（越低分越高）
    if 'pe_ratio' in merged.columns:
        pe = merged['pe_ratio'].replace([np.inf, -np.inf], np.nan)
        # 计算排名，PE越低排名越高（逆向因子）
        merged['pe_score'] = pe.rank(ascending=True, pct=True)
        merged['pe_score'] = merged['pe_score'].fillna(0.5)
    else:
        merged['pe_score'] = 0.5

    # ROE归一化
    if 'roe' in merged.columns:
        roe = merged['roe'].fillna(0)
        merged['roe_score'] = roe.rank(ascending=True, pct=True)
    else:
        merged['roe_score'] = 0.5

    # 利润增速归一化
    if 'inc_net_profit_annual' in merged.columns:
        growth = merged['inc_net_profit_annual'].fillna(0)
        merged['growth_score'] = growth.rank(ascending=True, pct=True)
    else:
        merged['growth_score'] = 0.5

    # 综合基本面分
    merged['fundamental_score'] = (
        merged['pe_score'] * 0.15 +
        merged['roe_score'] * 0.20 +
        merged['growth_score'] * 0.15
    )

    # 写入结果
    for _, row in merged.iterrows():
        result[row['code']] = {
            'fundamental_score': row['fundamental_score'],
            'pe_score': row['pe_score'],
            'roe_score': row['roe_score'],
            'growth_score': row['growth_score']
        }

    return result


def get_technical_factors(stock):
    """
    计算单只股票的技术面因子。
    返回: {'momentum': float, 'volatility_score': float, 'volume_score': float}
    """
    df = attribute_history(stock, g.momentum_days + 20, '1d',
                           ['close', 'volume', 'high', 'low'])
    if df.empty or len(df) < g.momentum_days:
        return None

    close = df['close']

    # 1. 60日动量
    momentum = (close.iloc[-1] - close.iloc[-g.momentum_days]) / close.iloc[-g.momentum_days]

    # 2. 波动率（越低越好，低波动异象）
    daily_returns = close.pct_change().dropna()
    volatility = daily_returns.std() * np.sqrt(252)  # 年化波动率
    # 波动率评分：年化波动率越低分越高（<20%给高分）
    volatility_score = max(0, 1 - volatility / 0.4) if volatility > 0 else 0.5

    # 3. 成交量变化（近期放量=趋势确认）
    recent_vol = df['volume'].iloc[-20:].mean()
    hist_vol = df['volume'].iloc[-60:-20].mean() if len(df) >= 60 else recent_vol
    volume_ratio = recent_vol / hist_vol if hist_vol > 0 else 1.0
    volume_score = min(volume_ratio / 3, 1.0)  # 最高1分

    # ATR（平均真实波幅，风控用）
    high_low = df['high'] - df['low']
    atr = high_low.rolling(14).mean().iloc[-1]

    return {
        'momentum': momentum,
        'volatility_score': volatility_score,
        'volume_score': volume_score,
        'atr_ratio': atr / close.iloc[-1] if close.iloc[-1] > 0 else 0
    }


def rebalance(context):
    """每月调仓"""
    all_stocks = get_index_stocks(g.index_code)
    if not all_stocks:
        return

    log.info(f"📊 沪深300共 {len(all_stocks)} 只成分股")

    # 第1步：获取基本面因子
    fund_factors = get_fundamental_factors(all_stocks)
    log.info(f"   基本面数据获取完成: {len(fund_factors)} 只")

    # 第2步：获取技术面因子并综合打分
    scored = []
    for stock in all_stocks:
        # 基本面分
        fund = fund_factors.get(stock, {})
        fund_score = fund.get('fundamental_score', 0.4)

        # 技术面分
        tech = get_technical_factors(stock)
        if tech is None:
            continue

        tech_score = (tech['momentum'] * 0.20 +
                      tech['volatility_score'] * 0.15 +
                      tech['volume_score'] * 0.15)

        # 技术面中的动量先归一化到 [0,1]
        # 等所有数据收集完后统一归一化
        scored.append((stock, fund_score, tech['momentum'],
                       tech['volatility_score'], tech['volume_score'], tech['atr_ratio']))

    if not scored:
        log.warn("⚠️ 无有效评分数据")
        return

    # 第3步：对动量因子做横截面归一化
    momentum_values = [s[2] for s in scored]
    min_mom, max_mom = min(momentum_values), max(momentum_values)
    mom_range = max_mom - min_mom if max_mom > min_mom else 1.0

    # 第4步：计算综合评分
    final_scores = []
    for item in scored:
        stock, fund_score, momentum, vol_score, volu_score, atr = item
        # 动量归一化
        mom_normalized = (momentum - min_mom) / mom_range
        # 技术面综合
        tech_total = mom_normalized * 0.20 + vol_score * 0.15 + volu_score * 0.15
        # 总分 = 基本面50% + 技术面50%
        total = fund_score * 0.50 + tech_total * 0.50
        final_scores.append((stock, total, atr))

    # 排序选股
    final_scores.sort(key=lambda x: x[1], reverse=True)
    selected = [s[0] for s in final_scores[:g.top_n]]

    current_data = get_current_data()
    current_positions = list(context.portfolio.positions.keys())

    # 过滤停牌ST
    selected = [
        s for s in selected
        if s in current_data and not current_data[s].paused and not current_data[s].is_st
    ]
    selected = [s for s in selected if not s.startswith('688')]

    log.info(f"🏆 选股TOP {len(selected)}: {[s[:6] for s in selected]}")

    # --- 卖出 ---
    for stock in current_positions:
        if stock not in selected:
            if context.portfolio.positions[stock].amount > 0:
                order_target(stock, 0)
                log.info(f"📉 卖出 {stock} (评分下降)")

    # --- 买入 ---
    if not selected:
        return

    cash_per_stock = context.portfolio.available_cash / len(selected)
    for stock in selected:
        if context.portfolio.positions[stock].amount > 0:
            continue
        order_value(stock, cash_per_stock)
        price_df = attribute_history(stock, 1, '1d', ['close'])
        log.info(f"📈 买入 {stock} @ {price_df['close'].iloc[-1]:.2f}")


def stop_loss_check(context):
    """每日止损"""
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
            log.info(f"🛑 止损 {stock} ({pnl*100:.1f}%)")


# =============================================
# 课后练习
# =============================================
# 1. 调整因子权重：试试基本面70%+技术面30%，或者反过来
# 2. 在基本面中加入「股息率」因子 (valuation.dividend_yield)
# 3. 在技术面中加入「RSI」指标（RSI < 30 加分，RSI > 70 减分）
# 4. 把调仓周期改成每周 (run_weekly)，交易次数和收益的关系
# 5. 把这个结果和单纯的动量策略对比：多因子是否跑赢了单因子？
