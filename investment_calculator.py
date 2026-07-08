"""
Investment Future Value Calculator
-----------------------------------
A desktop app (CustomTkinter) that estimates the future value of an
investment given an initial lump sum, a monthly contribution, an
expected annual return, and an investment duration. Includes a chart
of portfolio growth over time.

Requirements:
    pip install customtkinter matplotlib

Run:
    python investment_calculator.py
"""

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def format_inr(amount: float) -> str:
    """Format a number using the Indian numbering system with 2 decimals,
    e.g. 1234567.891 -> '12,34,567.89'."""
    amount = round(amount, 2)
    negative = amount < 0
    amount = abs(amount)

    whole = int(amount)
    frac = f"{amount:.2f}".split(".")[1]

    whole_str = str(whole)
    if len(whole_str) <= 3:
        grouped = whole_str
    else:
        last_three = whole_str[-3:]
        remaining = whole_str[:-3]
        parts = []
        while len(remaining) > 2:
            parts.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            parts.insert(0, remaining)
        grouped = ",".join(parts) + "," + last_three

    result = f"₹{grouped}.{frac}"
    return f"-{result}" if negative else result


def format_inr_short(amount: float) -> str:
    """Compact form for axis labels, e.g. 2630425 -> '₹26.3L'."""
    amount = abs(amount)
    if amount >= 1_00_00_000:  # 1 crore
        return f"₹{amount / 1_00_00_000:.1f}Cr"
    if amount >= 1_00_000:  # 1 lakh
        return f"₹{amount / 1_00_000:.1f}L"
    if amount >= 1_000:
        return f"₹{amount / 1_000:.0f}K"
    return f"₹{amount:.0f}"


def calculate_future_value(initial: float, monthly: float, annual_rate_pct: float, years: float):
    """
    Compounds monthly. Each month:
        balance = balance * (1 + monthly_rate) + monthly_contribution
    Contribution is added at the END of each month (ordinary annuity),
    which is the common convention for SIP-style calculators.
    """
    months = int(round(years * 12))
    monthly_rate = (annual_rate_pct / 100) / 12

    balance = initial
    total_invested = initial

    for _ in range(months):
        balance = balance * (1 + monthly_rate) + monthly
        total_invested += monthly

    final_value = balance
    interest_earned = final_value - total_invested

    return total_invested, interest_earned, final_value


def yearly_breakdown(initial: float, monthly: float, annual_rate_pct: float, years: float):
    """
    Returns three lists (year_labels, invested_by_year, value_by_year)
    with one snapshot at the end of each year (year 0 = starting point).
    Used to plot growth over time.
    """
    months = int(round(years * 12))
    monthly_rate = (annual_rate_pct / 100) / 12

    balance = initial
    total_invested = initial

    year_labels = [0]
    invested_by_year = [initial]
    value_by_year = [initial]

    for m in range(1, months + 1):
        balance = balance * (1 + monthly_rate) + monthly
        total_invested += monthly

        if m % 12 == 0:
            year_labels.append(m // 12)
            invested_by_year.append(total_invested)
            value_by_year.append(balance)

    # capture a partial final year if duration isn't a whole number of years
    if months % 12 != 0:
        year_labels.append(round(years, 2))
        invested_by_year.append(total_invested)
        value_by_year.append(balance)

    return year_labels, invested_by_year, value_by_year


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------

class InvestmentCalculatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Investment Future Value Calculator")
        self.geometry("980x700")
        self.minsize(860, 620)

        self.appearance_mode = "Dark"
        ctk.set_appearance_mode(self.appearance_mode)
        ctk.set_default_color_theme("blue")

        self.chart_canvas = None
        self.chart_fig = None

        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self):
        # Two-column layout: left = controls/results, right = chart
        self.grid_columnconfigure(0, weight=0, minsize=380)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left_col = ctk.CTkFrame(self, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)

        right_col = ctk.CTkFrame(self, corner_radius=12)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=20)
        self.right_col = right_col

        # ---- Header ----
        header_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text="Investment Growth Calculator",
            font=ctk.CTkFont(size=18, weight="bold"),
            wraplength=340,
            justify="left",
        )
        title_label.pack(side="left")

        self.mode_switch = ctk.CTkSwitch(
            header_frame,
            text="Dark",
            command=self._toggle_appearance,
        )
        self.mode_switch.select()
        self.mode_switch.pack(side="right")

        # ---- Input card ----
        input_frame = ctk.CTkFrame(left_col, corner_radius=12)
        input_frame.pack(fill="x", pady=10)

        self.entries = {}
        fields = [
            ("initial", "Initial Investment (₹)", "e.g. 100000"),
            ("monthly", "Monthly Investment (₹)", "e.g. 10000"),
            ("rate", "Expected Annual Return (%)", "e.g. 12"),
            ("years", "Investment Duration (Years)", "e.g. 10"),
        ]

        for key, label_text, placeholder in fields:
            lbl = ctk.CTkLabel(input_frame, text=label_text, anchor="w",
                                font=ctk.CTkFont(size=13))
            lbl.pack(fill="x", padx=16, pady=(12, 2))

            entry = ctk.CTkEntry(input_frame, placeholder_text=placeholder, height=36)
            entry.pack(fill="x", padx=16, pady=(0, 4))
            self.entries[key] = entry

        self.error_label = ctk.CTkLabel(
            input_frame, text="", text_color="#e05555", anchor="w",
            font=ctk.CTkFont(size=12), wraplength=340, justify="left"
        )
        self.error_label.pack(fill="x", padx=16, pady=(0, 10))

        # ---- Buttons ----
        btn_frame = ctk.CTkFrame(left_col, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10))

        self.calc_btn = ctk.CTkButton(
            btn_frame, text="Calculate", height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_calculate,
        )
        self.calc_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.reset_btn = ctk.CTkButton(
            btn_frame, text="Clear / Reset", height=40,
            fg_color="transparent", border_width=1,
            command=self._on_reset,
        )
        self.reset_btn.pack(side="left", expand=True, fill="x", padx=(8, 0))

        # ---- Results ----
        results_frame = ctk.CTkFrame(left_col, corner_radius=12)
        results_frame.pack(fill="both", expand=True, pady=10)

        results_title = ctk.CTkLabel(
            results_frame, text="Results", font=ctk.CTkFont(size=16, weight="bold")
        )
        results_title.pack(anchor="w", padx=16, pady=(14, 8))

        self.result_rows = {}
        result_fields = [
            ("invested", "Total Amount Invested"),
            ("interest", "Total Interest Earned"),
            ("final", "Final Portfolio Value"),
        ]

        for key, label_text in result_fields:
            row = ctk.CTkFrame(results_frame, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=8)

            lbl = ctk.CTkLabel(row, text=label_text, anchor="w",
                                font=ctk.CTkFont(size=13))
            lbl.pack(side="left")

            value_lbl = ctk.CTkLabel(
                row, text="₹0.00", anchor="e",
                font=ctk.CTkFont(size=15, weight="bold")
            )
            value_lbl.pack(side="right")
            self.result_rows[key] = value_lbl

        self.result_rows["final"].configure(text_color="#3aa757")
        self.result_rows["interest"].configure(text_color="#4a9eff")

        # ---- Chart panel (right column) ----
        chart_title = ctk.CTkLabel(
            right_col, text="Growth Over Time",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        chart_title.pack(anchor="w", padx=16, pady=(14, 4))

        self.chart_placeholder = ctk.CTkLabel(
            right_col,
            text="Enter your details and click Calculate\nto see the growth chart.",
            font=ctk.CTkFont(size=13),
            text_color="gray60",
        )
        self.chart_placeholder.pack(expand=True)

        self.chart_container = ctk.CTkFrame(right_col, fg_color="transparent")
        # not packed yet — packed once a chart is drawn

    # ------------------------------------------------------------------
    def _toggle_appearance(self):
        if self.mode_switch.get():
            ctk.set_appearance_mode("Dark")
            self.mode_switch.configure(text="Dark")
        else:
            ctk.set_appearance_mode("Light")
            self.mode_switch.configure(text="Light")

        # Redraw chart with theme-appropriate colors if it already exists
        if self.chart_fig is not None:
            self._draw_chart(self._last_years, self._last_invested, self._last_values)

    # ------------------------------------------------------------------
    def _on_reset(self):
        for entry in self.entries.values():
            entry.delete(0, "end")
        self.error_label.configure(text="")
        for key in self.result_rows:
            self.result_rows[key].configure(text="₹0.00")

        if self.chart_canvas is not None:
            self.chart_container.pack_forget()
            self.chart_placeholder.pack(expand=True)
            self.chart_canvas = None
            self.chart_fig = None

    # ------------------------------------------------------------------
    def _on_calculate(self):
        self.error_label.configure(text="")

        raw_values = {}
        for key, entry in self.entries.items():
            raw_values[key] = entry.get().strip()

        try:
            initial = float(raw_values["initial"]) if raw_values["initial"] else 0.0
            monthly = float(raw_values["monthly"]) if raw_values["monthly"] else 0.0
            rate = float(raw_values["rate"]) if raw_values["rate"] else 0.0
            years = float(raw_values["years"]) if raw_values["years"] else 0.0
        except ValueError:
            self.error_label.configure(text="Please enter valid numbers in all fields.")
            return

        errors = []
        if initial < 0:
            errors.append("Initial Investment cannot be negative.")
        if monthly < 0:
            errors.append("Monthly Investment cannot be negative.")
        if rate < 0:
            errors.append("Expected Annual Return cannot be negative.")
        if years <= 0:
            errors.append("Investment Duration must be greater than 0.")

        if errors:
            self.error_label.configure(text=" ".join(errors))
            return

        total_invested, interest_earned, final_value = calculate_future_value(
            initial, monthly, rate, years
        )

        self.result_rows["invested"].configure(text=format_inr(total_invested))
        self.result_rows["interest"].configure(text=format_inr(interest_earned))
        self.result_rows["final"].configure(text=format_inr(final_value))

        year_labels, invested_series, value_series = yearly_breakdown(
            initial, monthly, rate, years
        )
        self._last_years = year_labels
        self._last_invested = invested_series
        self._last_values = value_series

        self._draw_chart(year_labels, invested_series, value_series)

    # ------------------------------------------------------------------
    def _draw_chart(self, year_labels, invested_series, value_series):
        dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#242424" if dark else "#f2f2f2"
        text_color = "#e0e0e0" if dark else "#1a1a1a"
        grid_color = "#3a3a3a" if dark else "#d0d0d0"
        invested_color = "#8a8a8a" if dark else "#666666"
        value_color = "#3aa757"

        if self.chart_canvas is not None:
            self.chart_canvas.get_tk_widget().destroy()
            plt.close(self.chart_fig)

        self.chart_placeholder.pack_forget()
        self.chart_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        fig = plt.Figure(figsize=(5, 4.2), dpi=100)
        fig.patch.set_facecolor(bg_color)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg_color)

        ax.plot(year_labels, invested_series, label="Total Invested",
                color=invested_color, linewidth=2, linestyle="--")
        ax.plot(year_labels, value_series, label="Portfolio Value",
                color=value_color, linewidth=2.5)
        ax.fill_between(year_labels, value_series, invested_series,
                         where=[v >= i for v, i in zip(value_series, invested_series)],
                         color=value_color, alpha=0.12, interpolate=True)

        ax.set_xlabel("Years", color=text_color, fontsize=10)
        ax.set_ylabel("Amount", color=text_color, fontsize=10)
        ax.tick_params(colors=text_color, labelsize=9)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: format_inr_short(v)))

        for spine in ax.spines.values():
            spine.set_color(grid_color)
        ax.grid(True, color=grid_color, linewidth=0.5, alpha=0.6)

        legend = ax.legend(loc="upper left", fontsize=9, frameon=False)
        for text in legend.get_texts():
            text.set_color(text_color)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        self.chart_fig = fig
        self.chart_canvas = canvas


# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = InvestmentCalculatorApp()
    app.mainloop()
