from __future__ import annotations


def compute_wacc_g_grid(
    result_inputs: dict[str, float], wacc_range: list[float], g_range: list[float]
) -> dict[str, float]:
    fcff_n1 = result_inputs["fcff_n1"]
    shares = result_inputs["shares"]
    net_debt = result_inputs["net_debt"]
    out: dict[str, float] = {}
    for w in wacc_range:
        for g in g_range:
            if w <= g:
                continue
            ev = fcff_n1 / (w - g)
            out[f"{w:.4f}|{g:.4f}"] = (ev - net_debt) / shares
    return out
