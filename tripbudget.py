#!/usr/bin/env python3
"""tripbudget - a tiny travel expense tracker for multi-currency trips.

Log expenses in the local currency, convert them to a home currency with a
small editable rates file, and summarise spending by category and country
against a trip budget. Standard library only; data lives in a plain JSON file.

Usage:
    tripbudget add --date 2026-11-06 --country Peru --category food \\
        --amount 25 --currency PEN --note "lunch in Cusco"
    tripbudget summary [--file expenses.json] [--home JPY]
    tripbudget budget --daily 5000 --days 30 [--file expenses.json]
    tripbudget rates [--file rates.json]
    tripbudget set-rate --currency PEN --rate 41.2 [--file rates.json]
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

VERSION = "0.1.0"

DEFAULT_RATES = {
    # JPY per 1 unit of the currency (snapshot; edit rates.json to update).
    "JPY": 1.0,
    "USD": 152.0,
    "PEN": 41.2,   # Peruvian sol
    "BOB": 22.0,   # Bolivian boliviano
    "BRL": 28.5,   # Brazilian real
    "ARS": 0.11,   # Argentine peso
    "EUR": 165.0,
}

CATEGORIES = {"food", "stay", "transport", "activity", "shopping", "other"}


def load_json(path, default):
    if not Path(path).exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_rates(path):
    rates = dict(DEFAULT_RATES)
    rates.update(load_json(path, {}))
    return rates


def load_expenses(path):
    data = load_json(path, [])
    if not isinstance(data, list):
        raise ValueError(f"{path} does not contain a list of expenses")
    return data


def convert(amount, currency, rates, home="JPY"):
    """Convert amount in `currency` to the home currency."""
    currency = currency.upper()
    home = home.upper()
    if currency not in rates:
        raise ValueError(f"unknown currency: {currency} (add it with set-rate)")
    if home not in rates:
        raise ValueError(f"unknown home currency: {home}")
    return amount * rates[currency] / rates[home]


def add_expense(expenses, *, date_str, country, category, amount, currency, note=""):
    if category not in CATEGORIES:
        raise ValueError(f"unknown category: {category} (choose from {sorted(CATEGORIES)})")
    if amount <= 0:
        raise ValueError("amount must be positive")
    date.fromisoformat(date_str)  # validates YYYY-MM-DD
    entry = {
        "date": date_str,
        "country": country,
        "category": category,
        "amount": amount,
        "currency": currency.upper(),
        "note": note,
    }
    expenses.append(entry)
    return entry


def summarise(expenses, rates, home="JPY"):
    """Return totals per category and per country, in the home currency."""
    by_category = defaultdict(float)
    by_country = defaultdict(float)
    total = 0.0
    for e in expenses:
        jpy = convert(e["amount"], e["currency"], rates, home)
        by_category[e["category"]] += jpy
        by_country[e["country"]] += jpy
        total += jpy
    return {
        "home": home,
        "count": len(expenses),
        "total": round(total, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_category.items())},
        "by_country": {k: round(v, 2) for k, v in sorted(by_country.items())},
    }


def budget_status(expenses, rates, home, daily_budget, days):
    """Compare total spending with a daily budget x number of days."""
    summary = summarise(expenses, rates, home)
    budget = daily_budget * days
    spent = summary["total"]
    remaining = budget - spent
    return {
        "home": home,
        "budget": round(budget, 2),
        "spent": round(spent, 2),
        "remaining": round(remaining, 2),
        "days": days,
        "daily_budget": daily_budget,
        "over": remaining < 0,
        "daily_average": round(spent / days, 2) if days else 0.0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="tripbudget", description="Tiny multi-currency travel expense tracker."
    )
    parser.add_argument("--version", action="version", version=f"tripbudget {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="record one expense")
    p_add.add_argument("--date", default=date.today().isoformat())
    p_add.add_argument("--country", required=True)
    p_add.add_argument("--category", required=True, choices=sorted(CATEGORIES))
    p_add.add_argument("--amount", required=True, type=float)
    p_add.add_argument("--currency", required=True)
    p_add.add_argument("--note", default="")
    p_add.add_argument("--file", default="expenses.json")
    p_add.add_argument("--rates", default="rates.json")

    p_sum = sub.add_parser("summary", help="show totals by category and country")
    p_sum.add_argument("--file", default="expenses.json")
    p_sum.add_argument("--rates", default="rates.json")
    p_sum.add_argument("--home", default="JPY")

    p_bud = sub.add_parser("budget", help="compare spending with a daily budget")
    p_bud.add_argument("--daily", required=True, type=float)
    p_bud.add_argument("--days", required=True, type=int)
    p_bud.add_argument("--file", default="expenses.json")
    p_bud.add_argument("--rates", default="rates.json")
    p_bud.add_argument("--home", default="JPY")

    p_rates = sub.add_parser("rates", help="list the conversion rates in use")
    p_rates.add_argument("--file", default="rates.json")

    p_set = sub.add_parser("set-rate", help="set a conversion rate (JPY per unit)")
    p_set.add_argument("--currency", required=True)
    p_set.add_argument("--rate", required=True, type=float)
    p_set.add_argument("--file", default="rates.json")

    args = parser.parse_args(argv)

    try:
        if args.command == "add":
            rates = load_rates(args.rates)
            expenses = load_expenses(args.file)
            entry = add_expense(
                expenses,
                date_str=args.date,
                country=args.country,
                category=args.category,
                amount=args.amount,
                currency=args.currency,
                note=args.note,
            )
            save_json(args.file, expenses)
            home_amount = convert(entry["amount"], entry["currency"], rates)
            print(
                f"Added: {entry['date']} {entry['country']} {entry['category']} "
                f"{entry['amount']} {entry['currency']} "
                f"(~{home_amount:,.0f} JPY)"
            )
        elif args.command == "summary":
            rates = load_rates(args.rates)
            expenses = load_expenses(args.file)
            s = summarise(expenses, rates, args.home)
            print(f"Expenses: {s['count']} entries, total {s['total']:,.2f} {s['home']}")
            print("By category:")
            for k, v in s["by_category"].items():
                print(f"  {k:<10} {v:>12,.2f} {s['home']}")
            print("By country:")
            for k, v in s["by_country"].items():
                print(f"  {k:<10} {v:>12,.2f} {s['home']}")
        elif args.command == "budget":
            rates = load_rates(args.rates)
            expenses = load_expenses(args.file)
            b = budget_status(expenses, rates, args.home, args.daily, args.days)
            status = "OVER BUDGET" if b["over"] else "within budget"
            print(
                f"Budget: {b['budget']:,.0f} {b['home']} "
                f"({b['daily_budget']:,.0f} x {b['days']} days)"
            )
            print(f"Spent:  {b['spent']:,.0f} {b['home']} "
                  f"(avg {b['daily_average']:,.0f}/day)")
            print(f"Left:   {b['remaining']:,.0f} {b['home']} — {status}")
        elif args.command == "rates":
            rates = load_rates(args.file)
            for cur, rate in sorted(rates.items()):
                print(f"  {cur:<4} {rate}")
        elif args.command == "set-rate":
            if args.rate <= 0:
                raise ValueError("rate must be positive")
            rates = load_rates(args.file)
            rates[args.currency.upper()] = args.rate
            save_json(args.file, rates)
            print(f"Set {args.currency.upper()} = {args.rate} JPY")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
