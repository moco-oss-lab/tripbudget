# tripbudget

Tiny multi-currency travel expense tracker — a CLI for trips that cross
several currencies, like a South America crossing (Peru → Bolivia → Brazil).

Log each expense in the local currency, convert everything to a home
currency with a small editable rates file, and see totals by category and
country, plus whether you are still inside a daily budget.

Standard library only. Data lives in plain JSON files you can read and edit.

## Install

```sh
git clone https://github.com/moco-oss-lab/tripbudget.git
cd tripbudget
python3 tripbudget.py --help
```

No dependencies to install. Python 3.9+.

## Usage

Record an expense (defaults: today's date, `expenses.json` in the current
directory):

```sh
python3 tripbudget.py add --date 2026-11-06 --country Peru \
  --category food --amount 25 --currency PEN --note "lunch in Cusco"
# Added: 2026-11-06 Peru food 25 PEN (~1,030 JPY)
```

Categories: `food`, `stay`, `transport`, `activity`, `shopping`, `other`.

Summarise spending, converted to the home currency (default JPY):

```sh
python3 tripbudget.py summary
# Expenses: 2 entries, total 3,502.00 JPY
# By category:
#   food         1,030.00 JPY
#   stay         2,472.00 JPY
# By country:
#   Peru         3,502.00 JPY
```

Check a daily budget over the whole trip:

```sh
python3 tripbudget.py budget --daily 5000 --days 30
# Budget: 150,000 JPY (5,000 x 30 days)
# Spent:  3,502 JPY (avg 117/day)
# Left:   146,498 JPY — within budget
```

Exchange rates live in `rates.json` (JPY per unit). Built-in defaults cover
PEN, BOB, BRL, ARS, USD and EUR; update them as you go:

```sh
python3 tripbudget.py set-rate --currency PEN --rate 41.2
python3 tripbudget.py rates
```

Use `--file` / `--rates` / `--home` on any command to point at different
data files or a different home currency.

## Data format

`expenses.json` is a list of entries:

```json
[
  {"date": "2026-11-06", "country": "Peru", "category": "food",
   "amount": 25, "currency": "PEN", "note": "lunch in Cusco"}
]
```

## Tests

```sh
python3 -m pytest test_tripbudget.py -q
```

## License

MIT — see [LICENSE](LICENSE).
