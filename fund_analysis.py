import os
import warnings
from datetime import timedelta

import pandas as pd
import matplotlib.pyplot as plt
import finpy_tse as fp
from persiantools.jdatetime import JalaliDate
import arabic_reshaper
from bidi.algorithm import get_display

warnings.filterwarnings("ignore")


# =========================================================
# تنظیمات اصلی
# =========================================================

END_DATE = "1405-02-13"
START_DATE = "1404-01-01"
CHARTS_DIR = "charts"
TARGET_FUND = "خاتم"

FUNDS = [
    "آکام", "نشان", "یاقوت", "افران", "خورشید", "بلوط", "آرامش", "کارآمد", "اصیل", "ماهور",
    "فیروزا", "ارکیده", "همای", "کامیاب", "کارین", "آسود", "سپر", "خاتم", "طلوع", "آلا",
    "درین", "اونیکس", "ثبات", "نخل", "آکورد", "آوند", "نیلی", "ارمغان", "سپنتارود", "لبخند",
    "سیناد", "کارما", "رابین", "کمند", "بازده", "اعتبار", "آفاق", "ستاره", "تداوم", "کاج",
    "دامون", "پاداش", "صایند", "یارا", "امین یکم", "گنجینه", "آتیه ملت", "رشد",
    "ترنج ثابت", "هامرز", "بمان", "صنهال", "کیان", "پایا", "سام", "فاخر", "توسکا", "زمرد کوروش",
    "گنجین", "اوصتا", "سخند", "مانی", "پاسارگاد", "دارا", "ساحل", "شمیم", "خزانه ملت", "فردا",
    "آسان", "اعتماد", "پارند", "دیبا", "داریک", "کارا"
]


# =========================================================
# توابع تاریخ
# =========================================================

def subtract_jalali_months(date_str: str, months: int) -> str:
    y, m, d = map(int, date_str.split("-"))
    for _ in range(months):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return f"{y:04d}-{m:02d}-{d:02d}"


def subtract_jalali_days(date_str: str, days: int) -> str:
    date_str = date_str.replace("/", "-")
    y, m, d = map(int, date_str.split("-"))
    jalali_date = JalaliDate(y, m, d)
    gregorian_date = jalali_date.to_gregorian() - timedelta(days=days)
    new_jalali_date = JalaliDate.to_jalali(gregorian_date)
    return f"{new_jalali_date.year:04d}-{new_jalali_date.month:02d}-{new_jalali_date.day:02d}"


PERIODS = {
    "2 هفته‌ای": subtract_jalali_days(END_DATE, 13),
    "1 ماهه": subtract_jalali_months(END_DATE, 1),
    "2 ماهه": subtract_jalali_months(END_DATE, 2),
    "6 ماهه": subtract_jalali_months(END_DATE, 6),
    "12 ماهه": subtract_jalali_months(END_DATE, 12),
}


# =========================================================
# توابع فارسی‌سازی
# =========================================================

def reshape_fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(str(text)))


def to_persian_digits(value) -> str:
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    mapping = {str(i): persian_digits[i] for i in range(10)}
    return "".join(mapping.get(ch, ch) for ch in str(value))


def format_persian_percent(value: float) -> str:
    return reshape_fa(to_persian_digits(f"{value * 100:.2f}") + "٪")


def format_persian_date(date_str: str) -> str:
    y, m, d = date_str.split("-")
    return f"{to_persian_digits(d)}-{to_persian_digits(m)}-{to_persian_digits(y)}"


# =========================================================
# داده
# =========================================================

def fetch_nav_data(
    funds: list[str] = FUNDS,
    start_date: str = START_DATE,
    end_date: str = END_DATE
) -> pd.DataFrame:
    nav_prices = pd.DataFrame()

    for fund in funds:
        try:
            history = fp.Get_Price_History(
                stock=fund,
                start_date=start_date,
                end_date=end_date,
                ignore_date=False,
                adjust_price=True,
                show_weekday=True,
                double_date=False
            )

            if history is not None and not history.empty and "Adj Close" in history.columns:
                nav_prices[fund] = history["Adj Close"]
                print(f"Collected: {fund}")

        except Exception:
            print(f"Failed: {fund}")

    nav_prices = nav_prices.sort_index().ffill()
    return nav_prices


def compute_return(nav_prices: pd.DataFrame, start_date: str, end_date: str) -> pd.Series:
    period_data = nav_prices.loc[start_date:end_date]

    if period_data.empty:
        print(f"⚠️ داده‌ای بین {start_date} تا {end_date} پیدا نشد.")
        return pd.Series(dtype=float)

    actual_start = period_data.index.min()
    actual_end = period_data.index.max()
    print(f"بازه استفاده‌شده: {actual_start} → {actual_end}")

    returns = (period_data.iloc[-1] / period_data.iloc[0] - 1).sort_values(ascending=False)
    return returns


# =========================================================
# تنظیمات نمودار
# =========================================================

def setup_plot_style():
    os.makedirs(CHARTS_DIR, exist_ok=True)
    plt.style.use("dark_background")
    plt.rcParams["font.family"] = "DejaVu Sans"


# =========================================================
# نمودار 50 صندوق برتر
# =========================================================

def plot_top_funds(nav_prices: pd.DataFrame, top_n: int = 50):
    setup_plot_style()

    for period_name, start_date in PERIODS.items():
        returns = compute_return(nav_prices, start_date, END_DATE)
        if returns.empty:
            continue

        top_funds = returns.head(top_n)
        labels = [reshape_fa(f"{i + 1}. {name}") for i, name in enumerate(top_funds.index)]
        colors = ["#9B266A" if name == TARGET_FUND else "#4A90E2" for name in top_funds.index]

        fig, ax = plt.subplots(figsize=(16, 10))
        fig.patch.set_facecolor("#040414")
        ax.set_facecolor("#0b0b1a")

        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.bar(labels, top_funds.values, color=colors)

        for i, value in enumerate(top_funds.values):
            ax.text(
                i,
                value + (abs(value) * 0.0015 + 0.000001),
                " " + format_persian_percent(value) + " ",
                ha="center",
                va="bottom",
                fontsize=10,
                rotation=90,
                color="white"
            )

        ax.yaxis.grid(True, linestyle="--", color="#555577", alpha=0.3)
        ax.xaxis.grid(False)

        yticks = ax.get_yticks()
        ax.set_yticklabels([reshape_fa(to_persian_digits(round(y * 100)) + "٪") for y in yticks])

        ax.set_title(
            reshape_fa(
                f"{top_n} صندوق برتر درآمد ثابت — بازدهی {period_name} منتهی به {format_persian_date(END_DATE)}"
            ),
            fontsize=18,
            pad=30
        )
        ax.set_ylabel(reshape_fa("بازدهی"), fontsize=14)

        plt.xticks(rotation=75, ha="right", fontsize=9)
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, f"top_{period_name}.png"), dpi=300, bbox_inches="tight")
        plt.close()


# =========================================================
# نمودار مقایسه خاتم
# =========================================================

def plot_target_fund_comparison(nav_prices: pd.DataFrame, target_fund: str = TARGET_FUND):
    setup_plot_style()

    for period_name, start_date in PERIODS.items():
        returns = compute_return(nav_prices, start_date, END_DATE)
        if returns.empty or target_fund not in returns.index:
            continue

        target_return = returns[target_fund]
        mean_all = returns.mean()
        higher_returns = returns[returns > target_return]
        count_higher = len(higher_returns)
        mean_higher = higher_returns.mean() if not higher_returns.empty else 0
        gap_vs_higher_mean = mean_higher - target_return

        values = [mean_all, target_return, mean_higher]
        labels = [
            reshape_fa("میانگین کل صندوق‌ها"),
            reshape_fa(target_fund),
            reshape_fa("میانگین بالاتر از خاتم")
        ]
        colors = ["#4A90E2", "#9B266A", "#00C897"]

        fig, ax = plt.subplots(figsize=(7, 6))
        fig.patch.set_facecolor("#040414")
        ax.set_facecolor("#0b0b1a")

        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.bar(labels, values, color=colors)

        for i, value in enumerate(values):
            ax.text(
                i,
                value + (abs(value) * 0.02 + 0.0001),
                " " + format_persian_percent(value) + " ",
                ha="center",
                va="bottom",
                fontsize=12,
                color="white"
            )

        ax.yaxis.grid(True, linestyle="--", color="#555577", alpha=0.3)
        ax.xaxis.grid(False)

        yticks = ax.get_yticks()
        ax.set_yticklabels([reshape_fa(to_persian_digits(round(y * 100)) + "٪") for y in yticks])

        ax.set_title(
            reshape_fa(
                f"مقایسه عملکرد {target_fund} — بازدهی {period_name} منتهی به {format_persian_date(END_DATE)}"
            ),
            fontsize=16,
            pad=25
        )
        ax.set_ylabel(reshape_fa("بازدهی"), fontsize=14)

        legend_text = (
            f"{to_persian_digits(count_higher)} {reshape_fa('صندوق بالاتر از خاتم')} | "
            f"{reshape_fa('شکاف با میانگین بالاتر:')} "
            f"{to_persian_digits(f'{gap_vs_higher_mean * 100:.2f}')}٪"
        )

        ax.legend(
            [legend_text],
            loc="upper center",
            bbox_to_anchor=(0.5, -0.12),
            fontsize=11,
            facecolor="#111122",
            labelcolor="white",
            frameon=True,
            edgecolor="#333355"
        )

        plt.xticks(fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(CHARTS_DIR, f"{target_fund}_{period_name}.png"), dpi=300, bbox_inches="tight")
        plt.close()


# =========================================================
# اجرای اصلی
# =========================================================

def main():
    nav_prices = fetch_nav_data()
    print("داده‌ها با موفقیت دریافت شدند.")

    plot_top_funds(nav_prices)
    plot_target_fund_comparison(nav_prices)

    print("نمودارها با موفقیت ذخیره شدند.")


if __name__ == "__main__":
    main()
