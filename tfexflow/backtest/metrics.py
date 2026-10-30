import numpy as np
import pandas as pd


def summarize(daily: pd.DataFrame, trades: pd.DataFrame, capital: float, days_per_year: int = 245) -> dict:
    pnl = daily["pnl_net"]
    eq = capital + pnl.cumsum()
    peak = eq.cummax()
    dd = eq - peak
    ret = pnl / capital
    sharpe = float(ret.mean() / ret.std() * np.sqrt(days_per_year)) if ret.std() > 0 else 0.0
    wins = trades.loc[trades["pnl_net"] > 0, "pnl_net"].sum() if len(trades) else 0.0
    losses = -trades.loc[trades["pnl_net"] < 0, "pnl_net"].sum() if len(trades) else 0.0
    return {
        "days": int(len(daily)),
        "trades": int(len(trades)),
        "total_pnl_thb": float(pnl.sum()),
        "total_cost_thb": float(daily["cost"].sum()),
        "return_pct": float(pnl.sum() / capital * 100),
        "sharpe": sharpe,
        "max_drawdown_thb": float(-dd.min()),
        "max_drawdown_pct": float(-dd.min() / capital * 100),
        "profit_factor": float(wins / losses) if losses > 0 else float("inf") if wins > 0 else 0.0,
        "win_rate": float((trades["pnl_net"] > 0).mean()) if len(trades) else 0.0,
        "avg_trade_thb": float(trades["pnl_net"].mean()) if len(trades) else 0.0,
        "avg_hold_days": float(trades["hold_days"].mean()) if len(trades) else 0.0,
        "exposure_pct": float((daily["contracts"] != 0).mean() * 100),
        "kill_switch_triggers": int(daily["killed"].sum()),
    }
