"""
Integration / regression contract tests.

These represent the 'existing behaviour' that other parts of the business depend
on. They PASS against the starter code and MUST STILL PASS after you fix bugs and
add your automation. Do not change the public interface or output structure to make
your work easier — integrate without breaking what already works.
"""
import pandas as pd
from src import pipeline as p


def test_run_returns_dataframe():
    result = p.run()
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


def test_output_contract_columns():
    """Downstream reporting relies on these exact columns existing."""
    result = p.run()
    required = {"location", "month", "revenue", "monthly_revenue_target_LKR", "pct_of_target"}
    assert required.issubset(set(result.columns)), (
        f"Missing columns: {required - set(result.columns)}"
    )


def test_public_interface_preserved():
    """The entry points other code calls must keep their names."""
    for fn in ("load_sales", "clean", "add_revenue",
               "monthly_revenue_by_location", "compare_to_targets", "run"):
        assert hasattr(p, fn), f"Public function '{fn}' was removed/renamed"
