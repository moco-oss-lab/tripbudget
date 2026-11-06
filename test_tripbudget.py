import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import tripbudget


def run_cli(*args, cwd):
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "tripbudget.py"), *args],
        cwd=cwd, capture_output=True, text=True,
    )
    return result


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


def test_add_and_summary_roundtrip(tmp):
    assert run_cli("add", "--date", "2026-11-06", "--country", "Peru",
                   "--category", "food", "--amount", "25", "--currency", "PEN",
                   cwd=tmp).returncode == 0
    assert run_cli("add", "--date", "2026-11-06", "--country", "Peru",
                   "--category", "stay", "--amount", "60", "--currency", "PEN",
                   cwd=tmp).returncode == 0
    result = run_cli("summary", cwd=tmp)
    assert result.returncode == 0
    # 25 + 60 PEN at 41.2 JPY/PEN = 3502 JPY
    assert "3,502.00" in result.stdout
    assert "food" in result.stdout and "stay" in result.stdout
    assert "Peru" in result.stdout


def test_summary_empty_file(tmp):
    result = run_cli("summary", cwd=tmp)
    assert result.returncode == 0
    assert "0 entries" in result.stdout


def test_convert_uses_rates_file(tmp):
    rates = {"JPY": 1.0, "PEN": 50.0}
    (tmp / "rates.json").write_text(json.dumps(rates), encoding="utf-8")
    expenses = tripbudget.load_expenses(str(tmp / "expenses.json"))
    tripbudget.add_expense(expenses, date_str="2026-11-06", country="Peru",
                           category="food", amount=10, currency="PEN")
    summary = tripbudget.summarise(expenses, tripbudget.load_rates(str(tmp / "rates.json")))
    assert summary["total"] == 500.0


def test_unknown_currency_errors(tmp):
    expenses = []
    with pytest.raises(ValueError, match="unknown currency"):
        tripbudget.convert(10, "XXX", tripbudget.load_rates(str(tmp / "rates.json")))


def test_bad_category_rejected(tmp):
    with pytest.raises(ValueError, match="unknown category"):
        tripbudget.add_expense([], date_str="2026-11-06", country="Peru",
                               category="party", amount=10, currency="PEN")


def test_bad_date_rejected(tmp):
    with pytest.raises(ValueError):
        tripbudget.add_expense([], date_str="2026-13-40", country="Peru",
                               category="food", amount=10, currency="PEN")


def test_negative_amount_rejected(tmp):
    with pytest.raises(ValueError, match="positive"):
        tripbudget.add_expense([], date_str="2026-11-06", country="Peru",
                               category="food", amount=-5, currency="PEN")


def test_budget_within_and_over(tmp):
    rates = tripbudget.load_rates(str(tmp / "rates.json"))
    expenses = []
    tripbudget.add_expense(expenses, date_str="2026-11-06", country="Peru",
                           category="food", amount=100, currency="PEN")
    within = tripbudget.budget_status(expenses, rates, "JPY", daily_budget=5000, days=30)
    assert within["spent"] == 4120.0
    assert within["over"] is False
    assert within["remaining"] == 145880.0
    over = tripbudget.budget_status(expenses, rates, "JPY", daily_budget=100, days=30)
    assert over["over"] is True


def test_set_rate_and_rates_listing(tmp):
    assert run_cli("set-rate", "--currency", "PEN", "--rate", "45.0",
                   cwd=tmp).returncode == 0
    result = run_cli("rates", cwd=tmp)
    assert result.returncode == 0
    assert "PEN" in result.stdout and "45.0" in result.stdout
    stored = json.loads((tmp / "rates.json").read_text(encoding="utf-8"))
    assert stored["PEN"] == 45.0


def test_cli_add_invalid_category_fails(tmp):
    result = run_cli("add", "--country", "Peru", "--category", "party",
                     "--amount", "10", "--currency", "PEN", cwd=tmp)
    assert result.returncode != 0
