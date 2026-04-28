from financial_reports.grading.engine import grade_report
from financial_reports.models.outputs import DCFResult


def test_grade_thresholds() -> None:
    dcf = DCFResult(
        enterprise_value=100,
        equity_value=90,
        intrinsic_value_per_share=30,
        wacc=0.1,
        terminal_growth=0.03,
        terminal_value=120,
        pv_terminal_value=70,
        projection=[],
    )
    config = {
        "grading": {
            "weights": {
                "valuation": 0.35,
                "balance_sheet": 0.2,
                "cash_flow": 0.15,
                "forecast_quality": 0.15,
                "risk_penalty": 0.15,
            },
            "letter_bands": {
                "A": [85, 100],
                "B": [70, 84.99],
                "C": [55, 69.99],
                "D": [40, 54.99],
                "F": [0, 39.99],
            },
        }
    }
    out = grade_report(dcf, [], [], config, market_price=20)
    assert out.letter_grade in {"A", "B"}
