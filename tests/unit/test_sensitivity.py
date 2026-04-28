from financial_reports.valuation.sensitivity import compute_wacc_g_grid


def test_sensitivity_grid() -> None:
    grid = compute_wacc_g_grid({"fcff_n1": 10, "shares": 5, "net_debt": 0}, [0.1], [0.02])
    assert "0.1000|0.0200" in grid
