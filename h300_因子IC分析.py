"""
沪深300成分股因子IC分析（信息系数）
====================================
分析 PE、PB、ROE、换手率 四个因子与未来20日收益的相关性强度。

IC（Information Coefficient）=  因子值 × 未来收益的秩相关性（Spearman）
  - 正值 IC：因子值越高 → 未来收益越高（正向选股因子）
  - 负值 IC：因子值越高 → 未来收益越低（反向选股因子）
  - |IC| 越大 → 该因子预测力越强
  - ICIR = 均值 IC / IC 标准差（稳定性指标）
  - IC 胜率 = IC > 0 的月份占比

使用方法：
1. 登录 joinquant.com → 研究平台 → 新建策略
2. 粘贴全部内容，点击「运行」
3. 等待约 30-60 秒，输出 IC 分析报告和图表

运行环境：JoinQuant 研究环境（Research Notebook）
⚠️ 不要在回测环境运行，因为使用了 matplotlib 绘图和多因子数据聚合
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from jqdata import *
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 配置参数（你可以在这里改）
# ============================================================
INDEX_CODE = '000300.XSHG'        # 沪深300
START_DATE = '2019-01-01'         # 分析开始日期
END_DATE = '2024-12-31'           # 分析结束日期
FORWARD_DAYS = 20                 # 未来收益天数（≈1个月）
TEST_INTERVAL = 'monthly'         # 测试频率：'monthly' 或 'weekly'
N_TOP_BOTTOM = 50                 # 多空组合测试的组数

# ============================================================
# 辅助函数
# ============================================================


def get_forward_return(stock, date, days=FORWARD_DAYS):
    """
    计算某只股票在指定日期后的 N 日收益。
    返回：收益率（小数），或 NaN（如果数据不足）
    """
    end_dt = date + timedelta(days=int(days * 1.5))
    df = get_price(stock, start_date=date, end_date=end_dt,
                   frequency='daily', fields=['close'], skip_paused=True)

    if df.empty or len(df) < 2:
        return np.nan

    if df.index[0].date() != date:
        return np.nan

    start_price = df['close'].iloc[0]

    if len(df) > days:
        end_price = df['close'].iloc[days]
    else:
        end_price = df['close'].iloc[-1]

    if start_price <= 0 or end_price <= 0:
        return np.nan

    return (end_price - start_price) / start_price


def compute_pe(stock, date):
    """获取 PE（市盈率）— 警惕极端值，截尾处理"""
    try:
        df = get_fundamentals(query(
            valuation.code, valuation.pe_ratio
        ).filter(
            valuation.code == stock
        ), date=date)
        if df.empty:
            return np.nan
        pe = df['pe_ratio'].iloc[0]
        # 过滤负值PE（亏损公司）和极端值
        if pe is None or pe <= 0 or pe > 200:
            return np.nan
        return pe
    except Exception:
        return np.nan


def compute_pb(stock, date):
    """获取 PB（市净率）— 过滤负值"""
    try:
        df = get_fundamentals(query(
            valuation.code, valuation.pb_ratio
        ).filter(
            valuation.code == stock
        ), date=date)
        if df.empty:
            return np.nan
        pb = df['pb_ratio'].iloc[0]
        if pb is None or pb <= 0 or pb > 50:
            return np.nan
        return pb
    except Exception:
        return np.nan


def compute_roe(stock, date):
    """获取 ROE（净资产收益率）— 越高越好"""
    try:
        df = get_fundamentals(query(
            valuation.code, indicator.roe
        ).filter(
            valuation.code == stock
        ), date=date)
        if df.empty:
            return np.nan
        roe = df['roe'].iloc[0]
        if roe is None:
            return np.nan
        return roe
    except Exception:
        return np.nan


def compute_turnover(stock, date, lookback=20):
    """
    计算换手率均值（过去20日平均换手率）
    get_price 获取的 turn 字段是当日换手率(%)
    """
    try:
        start_dt = date - timedelta(days=int(lookback * 2.5))
        df = get_price(stock, start_date=start_dt, end_date=date,
                       frequency='daily', fields=['turn'], skip_paused=False)
        
        if df.empty:
            return np.nan
        
        if len(df) < 3:
            return np.nan
        
        df['turn'] = df['turn'].fillna(method='ffill')
        valid_turn = df['turn'].dropna()
        
        if len(valid_turn) < 2:
            return np.nan
        
        avg_turn = valid_turn.mean()
        if avg_turn is None or np.isnan(avg_turn) or avg_turn <= 0:
            return np.nan
        return avg_turn
    except Exception:
        return np.nan


# ============================================================
# IC 计算主函数
# ============================================================


def compute_ic_at_date(date):
    """
    在指定日期计算各因子与未来20日收益的截面相关性。
    返回 dict: {factor_name: spearman_ic}
    """
    stocks = get_index_stocks(INDEX_CODE, date=date.strftime('%Y-%m-%d'))
    if not stocks:
        return None

    # 限制股票数量，避免运行太久
    if len(stocks) > 300:
        stocks = stocks[:300]

    data_rows = []
    stats = {'total': 0, 'fwd_ret_valid': 0, 'turnover_valid': 0, 'both_valid': 0}
    
    for stock in stocks:
        stats['total'] += 1
        pe = compute_pe(stock, date)
        pb = compute_pb(stock, date)
        roe = compute_roe(stock, date)
        turnover = compute_turnover(stock, date)
        fwd_ret = get_forward_return(stock, date)

        if not np.isnan(fwd_ret):
            stats['fwd_ret_valid'] += 1
        if not np.isnan(turnover):
            stats['turnover_valid'] += 1
        if not np.isnan(fwd_ret) and not np.isnan(turnover):
            stats['both_valid'] += 1

        if not np.isnan(fwd_ret):
            data_rows.append({
                'stock': stock,
                'pe': pe,
                'pb': pb,
                'roe': roe,
                'turnover': turnover,
                'fwd_return': fwd_ret
            })

    if len(data_rows) < 30:
        print(f"   ⚠️ {date}: 有效股票{len(data_rows)}/300，fwd_ret有效{stats['fwd_ret_valid']}，turnover有效{stats['turnover_valid']}")
        return None

    df = pd.DataFrame(data_rows)

    results = {}
    factors = {
        'PE': 'pe',
        'PB': 'pb',
        'ROE': 'roe',
        '换手率': 'turnover'
    }

    for label, col in factors.items():
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df['fwd_return'] = pd.to_numeric(df['fwd_return'], errors='coerce')
        valid = df[[col, 'fwd_return']].dropna()
        if len(valid) < 20:
            results[label] = np.nan
            continue

        from scipy.stats import spearmanr
        rho, p_value = spearmanr(valid[col], valid['fwd_return'])
        results[label] = rho

    return results


def generate_test_dates(start, end, freq=TEST_INTERVAL):
    """生成测试日期序列（每月或每周最后一个交易日）"""
    all_dates = get_trade_days(start_date=start, end_date=end)

    if freq == 'monthly':
        # 每月最后一个交易日
        df = pd.DataFrame({'date': all_dates})
        df['month'] = df['date'].apply(lambda x: x.month)
        df['year'] = df['date'].apply(lambda x: x.year)
        test_dates = df.groupby(['year', 'month']).last()['date'].tolist()
    else:
        # 每周最后一个交易日
        df = pd.DataFrame({'date': all_dates})
        df['week'] = df['date'].apply(lambda x: x.isocalendar()[1])
        df['year'] = df['date'].apply(lambda x: x.year)
        test_dates = df.groupby(['year', 'week']).last()['date'].tolist()

    return test_dates


# ============================================================
# 多空组合回测（模拟分层收益）
# ============================================================


def compute_factor_group_returns(date):
    """
    按因子值分组，计算各组未来20日平均收益。
    返回 dict: {factor_name: {group1_mean_ret, ..., group5_mean_ret}}
    """
    stocks = get_index_stocks(INDEX_CODE, date=date.strftime('%Y-%m-%d'))
    if not stocks:
        return None

    stocks = stocks[:300]

    data_rows = []
    for stock in stocks:
        pe = compute_pe(stock, date)
        pb = compute_pb(stock, date)
        roe = compute_roe(stock, date)
        turnover = compute_turnover(stock, date)
        fwd_ret = get_forward_return(stock, date)

        if not np.isnan(fwd_ret):
            data_rows.append({
                'stock': stock,
                'pe': pe,
                'pb': pb,
                'roe': roe,
                'turnover': turnover,
                'fwd_return': fwd_ret
            })

    if len(data_rows) < 30:
        return None

    df = pd.DataFrame(data_rows)
    result = {}

    for label, col in [('PE', 'pe'), ('PB', 'pb'), ('ROE', 'roe'), ('换手率', 'turnover')]:
        valid = df[[col, 'fwd_return']].dropna()
        if len(valid) < 20:
            result[label] = None
            continue

        # 分成5组
        valid['group'] = pd.qcut(valid[col], 5, labels=['G1(低)', 'G2', 'G3', 'G4', 'G5(高)'],
                                 duplicates='drop')
        group_means = valid.groupby('group')['fwd_return'].mean()
        result[label] = group_means.to_dict()

    return result


# ============================================================
# 主程序
# ============================================================

print("=" * 65)
print("  沪深300成分股因子 IC 分析")
print(f"  分析期: {START_DATE} 至 {END_DATE}")
print(f"  未来收益窗口: {FORWARD_DAYS} 个交易日")
print(f"  测试频率: {'每月' if TEST_INTERVAL == 'monthly' else '每周'}")
print(f"  因子: PE / PB / ROE / 换手率")
print("=" * 65)

# --- 生成测试日期 ---
print("\n⏳ 生成测试日期序列...")
test_dates = generate_test_dates(START_DATE, END_DATE)
print(f"   共 {len(test_dates)} 个测试时间点")

# --- 逐期计算 IC ---
print("\n⏳ 逐期计算 IC（这需要 30-60 秒，请等待）...")
ic_records = []

for i, date in enumerate(test_dates):
    # 每10%打印一次进度
    if (i + 1) % max(1, len(test_dates) // 10) == 0:
        pct = (i + 1) / len(test_dates) * 100
        print(f"   进度 {pct:.0f}% ({i+1}/{len(test_dates)})...")

    ic = compute_ic_at_date(date)
    if ic:
        ic['date'] = date
        ic_records.append(ic)

print(f"\n✅ IC 计算完成，有效样本 {len(ic_records)} 期")

if not ic_records:
    print("\n❌ 所有日期的IC计算均失败，无法进行后续分析")
    print("   可能原因：")
    print("   1. 日期范围太窄，没有足够的测试时间点")
    print("   2. 因子数据获取失败（如财务数据未更新）")
    print("   3. 股票数量不足（少于30只）")
    exit()

# --- IC 统计分析 ---
print("\n" + "=" * 65)
print("  📊 IC 分析报告")
print("=" * 65)

df_ic = pd.DataFrame(ic_records).set_index('date')
factor_names = ['PE', 'PB', 'ROE', '换手率']
for f in factor_names:
    df_ic[f] = pd.to_numeric(df_ic[f], errors='coerce')

for factor in factor_names:
    series = df_ic[factor].dropna()
    if len(series) < 3:
        print(f"\n  {factor}: 数据不足")
        continue

    mean_ic = series.mean()
    std_ic = series.std()
    icir = mean_ic / std_ic if std_ic > 0 else 0
    win_rate = (series > 0).sum() / len(series)
    max_ic = series.max()
    min_ic = series.min()

    # 解读
    direction = "正向" if mean_ic > 0 else "反向"
    strength = "强" if abs(mean_ic) > 0.05 else ("中" if abs(mean_ic) > 0.02 else "弱")

    print(f"\n  ┌─ {factor} {'─' * (16 - len(factor))}┐")
    print(f"  │ 平均 IC : {mean_ic:+.4f}  ({direction}, {strength})")
    print(f"  │ IC 标准差: {std_ic:.4f}")
    print(f"  │ ICIR    : {icir:+.4f}  {'✅ 稳定预测' if abs(icir) > 0.5 else '❌ 不稳定' if abs(icir) < 0.2 else '⚠️ 一般'}")
    print(f"  │ 胜率    : {win_rate:.1%}  ({'>50%' if win_rate > 0.5 else '<50%'} 方向一致)")
    print(f"  │ IC 区间 : [{min_ic:+.4f}, {max_ic:+.4f}]")
    print(f"  └{'─' * 22}┘")

# --- 因子 IC 时序折线图 ---
valid_factors_for_plot = [(f, c) for f, c in zip(factor_names, ['#E74C3C', '#3498DB', '#27AE60', '#F39C12']) 
                         if len(df_ic[f].dropna()) >= 3]

if valid_factors_for_plot:
    num_plots = len(valid_factors_for_plot)
    fig, axes = plt.subplots(num_plots, 1, figsize=(14, 4*num_plots), sharex=True)
    if num_plots == 1:
        axes = [axes]
    fig.suptitle(f'沪深300 因子 IC 时序 ({START_DATE} — {END_DATE})', fontsize=14)

    for idx, (factor, color) in enumerate(valid_factors_for_plot):
        ax = axes[idx]
        series = df_ic[factor].dropna()
        ax.plot(series.index, series.values, color=color, linewidth=0.8,
                marker='o', markersize=2, alpha=0.7)
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5)
        ax.axhline(y=series.mean(), color=color, linestyle='-',
                   linewidth=1.5, label=f'均值 {series.mean():+.4f}')
        ax.fill_between(series.index, series.values, 0,
                        where=(series.values > 0),
                        color='red', alpha=0.15)
        ax.fill_between(series.index, series.values, 0,
                        where=(series.values < 0),
                        color='green', alpha=0.15)
        ax.set_ylabel(f'{factor} IC')
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(-0.6, 0.6)

    axes[-1].set_xlabel('日期')
    plt.tight_layout()
    plt.show()
else:
    print("  ❌ 所有因子IC数据均不足，跳过时序折线图")

# --- 因子 IC 箱线图 ---
valid_factor_names = []
bp_data = []
for f in factor_names:
    values = df_ic[f].dropna().values
    if len(values) >= 3:
        valid_factor_names.append(f)
        bp_data.append(values)
    else:
        print(f"  ⚠️ {f} IC数据不足（{len(values)}条），跳过箱线图")

if bp_data:
    fig, ax = plt.subplots(figsize=(10, 6))
    bp = ax.boxplot(bp_data, labels=valid_factor_names, patch_artist=True,
                    widths=0.5, showmeans=True,
                    meanprops=dict(marker='D', markerfacecolor='red', markersize=8))

    colors_box = ['#E74C3C', '#3498DB', '#27AE60', '#F39C12']
    for patch, color in zip(bp['boxes'], colors_box[:len(bp_data)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1)
    ax.set_title('因子 IC 分布箱线图', fontsize=13)
    ax.set_ylabel('IC 值')
    ax.grid(True, alpha=0.2, axis='y')

    for i, factor in enumerate(valid_factor_names):
        mean_val = df_ic[factor].mean()
        if not np.isnan(mean_val):
            ax.annotate(f'{mean_val:+.3f}',
                        xy=(i + 1, mean_val),
                        xytext=(i + 1.3, mean_val + 0.02),
                        fontsize=9, color='darkred')

    plt.tight_layout()
    plt.show()
else:
    print("  ❌ 所有因子IC数据均不足，跳过箱线图")

# --- 分层收益回测（多空组合） ---
print("\n\n⏳ 计算分层收益（5组多空回测）...")

group_records = []
for i, date in enumerate(test_dates):
    if (i + 1) % max(1, len(test_dates) // 5) == 0:
        print(f"   分层进度 {(i+1)/len(test_dates)*100:.0f}%...")
    grp = compute_factor_group_returns(date)
    if grp:
        grp['date'] = date
        group_records.append(grp)

if not group_records:
    print("  ❌ 分层收益数据为空，跳过相关分析")
else:
    print(f"✅ 分层收益计算完成（{len(group_records)}期有效数据）")

# --- 分层收益分析 ---
if not group_records:
    pass
else:
    print("\n" + "=" * 65)
    print("  📊 分层收益分析（多空组合模拟）")
    print("=" * 65)

    for factor in factor_names:
        print(f"\n  ┌─ {factor} ─ 五组未来20日平均收益")
        all_g1 = []
        all_g5 = []
        for rec in group_records:
            if factor not in rec or rec[factor] is None:
                continue
            for g_label, g_val in rec[factor].items():
                if 'G1' in str(g_label):
                    all_g1.append(g_val)
                elif 'G5' in str(g_label):
                    all_g5.append(g_val)

        if all_g1 and all_g5:
            mean_g1 = np.mean(all_g1) * 100
            mean_g5 = np.mean(all_g5) * 100
            spread = mean_g1 - mean_g5
            print(f"  │ G1(低): {mean_g1:+.2f}%  |  G5(高): {mean_g5:+.2f}%")
            print(f"  │ 多空收益差 (G1-G5): {spread:+.2f}%")
            if abs(spread) > 1.0:
                print(f"  │ 解读: {'低值组跑赢' if spread > 0 else '高值组跑赢'}，约 {abs(spread):.1f}%/20日")
            else:
                print(f"  │ 解读: 区分度一般")
        else:
            print(f"  │ 数据不足")
        print(f"  └{'─' * 22}┘")


# --- 汇总排名 ---
print("\n" + "=" * 65)
print("  🏆 因子预测力排名（按 |平均IC| × ICIR 综合评分）")
print("=" * 65)

factor_stats = []
for factor in factor_names:
    series = df_ic[factor].dropna()
    if len(series) < 3:
        continue
    mean_ic = series.mean()
    std_ic = series.std()
    icir = mean_ic / std_ic if std_ic > 0 else 0
    # 综合评分：|IC| * ICIR（同时考虑强度和稳定性）
    composite = abs(mean_ic) * abs(icir)
    factor_stats.append({
        '因子': factor,
        '平均IC': mean_ic,
        'ICIR': icir,
        '胜率': (series > 0).sum() / len(series),
        '综合评分': composite,
        '方向': '正向选股' if mean_ic > 0 else '反向选股'
    })

factor_df = pd.DataFrame(factor_stats)
factor_df = factor_df.sort_values('综合评分', ascending=False)
factor_df['排名'] = range(1, len(factor_df) + 1)
factor_df = factor_df[['排名', '因子', '平均IC', 'ICIR', '胜率', '方向', '综合评分']]

print(f"\n  {factor_df.to_string(index=False)}")
print(f"\n  ICIR > 0.5  = 该因子具有稳定预测能力")
print(f"  |平均IC| > 0.03 = 该因子预测强度较高")
print(f"  综合评分 = |平均IC| × |ICIR|，越高越推荐使用")

# --- 结论 ---
print("\n" + "=" * 65)
print("  💡 策略建议")
print("=" * 65)

top_factor = factor_df.iloc[0] if len(factor_df) > 0 else None
if top_factor is not None:
    dir_word = "低估值" if top_factor['方向'] == '反向选股' else "高估值"
    print(f"\n  ✅ 最强因子: {top_factor['因子']} (综合评分 {top_factor['综合评分']:.4f})")
    print(f"     IC={top_factor['平均IC']:+.4f}, ICIR={top_factor['ICIR']:+.4f}")
    print(f"     建议: {'买入' + dir_word + '的股票' if top_factor['平均IC'] < 0 else '买入' + dir_word + '的股票'}")

    # 对比
    if len(factor_df) > 1:
        second = factor_df.iloc[1]
        print(f"\n  📌 第二强: {second['因子']} (综合评分 {second['综合评分']:.4f})")

    print(f"\n  📝 建议组合策略:")
    print(f"     1. 优先使用排名靠前的因子")
    print(f"     2. 组合 2-3 个低相关性的强因子提升稳定性")
    print(f"     3. 避免使用 ICIR < 0.2 的因子")
    print(f"     4. 定期（每半年）重跑本脚本验证因子有效性是否衰减")

print("\n✅ 分析完成！")


# =============================================
# 扩展练习
# =============================================
# 1. 把未来收益改成 5 日 / 60 日，看哪个因子的预测力在不同时间尺度上变化
# 2. 加入更多因子：市值、股息率、营收增速、毛利率
# 3. 分析不同市场环境（牛市/熊市/震荡市）下各因子IC的变化
#    可以用沪深300指数20日涨跌幅 > 5% 作为牛熊分界
# 4. 因子IC衰减分析：按年计算IC，看因子的预测力是否随年份衰减
# 5. 研究环境 vs 本地运行：如果要分析更长周期（10年），建议在本地用 jqdatasdk 运行
