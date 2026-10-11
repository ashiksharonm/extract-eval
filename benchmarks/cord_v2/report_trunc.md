# extract-eval report

- Documents: 100
- Micro P/R/F1: 0.870 / 0.623 / **0.726** 95% CI [0.644, 0.802]
- Macro F1: **0.710** 95% CI [0.624, 0.785]
- Docs passing (doc F1 >= 1.0): 44.0%
- Bootstrap: 1000 resamples over documents, seed 0

## Per-field

| field | P | R | F1 | F1 95% CI | TP | FP | FN | missing | extra | mismatch | format_only |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `menu.cnt` | 0.931 | 0.609 | 0.736 | [0.628, 0.848] | 134 | 10 | 86 | 85 | 9 | 1 | 0 |
| `menu.nm` | 0.833 | 0.558 | 0.668 | [0.565, 0.770] | 140 | 28 | 111 | 94 | 11 | 17 | 0 |
| `menu.price` | 0.838 | 0.569 | 0.678 | [0.571, 0.776] | 140 | 27 | 106 | 91 | 12 | 4 | 11 |
| `sub_total.discount_price` | 1.000 | 0.333 | 0.500 | [0.000, 0.860] | 2 | 0 | 4 | 4 | 0 | 0 | 0 |
| `sub_total.subtotal_price` | 0.875 | 0.646 | 0.743 | [0.631, 0.833] | 42 | 6 | 23 | 18 | 1 | 2 | 3 |
| `sub_total.tax_price` | 0.857 | 0.558 | 0.676 | [0.529, 0.800] | 24 | 4 | 19 | 15 | 0 | 1 | 3 |
| `total.cashprice` | 0.919 | 0.851 | 0.884 | [0.813, 0.945] | 57 | 5 | 10 | 6 | 1 | 2 | 2 |
| `total.changeprice` | 0.870 | 0.839 | 0.855 | [0.768, 0.932] | 47 | 7 | 9 | 4 | 2 | 0 | 5 |
| `total.creditcardprice` | 0.857 | 0.375 | 0.522 | [0.235, 0.750] | 6 | 1 | 10 | 9 | 0 | 1 | 0 |
| `total.menuqty_cnt` | 0.833 | 0.690 | 0.755 | [0.586, 0.885] | 20 | 4 | 9 | 7 | 2 | 2 | 0 |
| `total.total_price` | 0.873 | 0.726 | 0.793 | [0.721, 0.862] | 69 | 10 | 26 | 20 | 4 | 0 | 6 |

## Error buckets

| bucket | count |
|---|---|
| missing | 353 |
| extra | 42 |
| mismatch | 30 |
| format_only | 30 |

## Sample errors (first 15)

| doc | field | bucket | gold | pred |
|---|---|---|---|---|
| cord_test_000 | `total.creditcardprice` | missing | 60.000 | None |
| cord_test_000 | `sub_total.subtotal_price` | format_only | 60.000 | -60.000 |
| cord_test_000 | `sub_total.tax_price` | format_only | 5.455 | 5,455 |
| cord_test_000 | `sub_total.discount_price` | missing | -60.000 | None |
| cord_test_002 | `menu.nm` | mismatch | JASMINE MT ( L ) | GOSMINE MT ( ) |
| cord_test_002 | `menu.nm` | extra | None | COCONUT JELLY ( L ) |
| cord_test_002 | `menu.price` | extra | None | 4,000 |
| cord_test_004 | `total.total_price` | format_only | 174,600 | 174.600 |
| cord_test_004 | `menu.nm` | mismatch | CHIKEN KATSU FF | Ode CHIKEN KATSU FF |
| cord_test_005 | `total.menuqty_cnt` | missing | 1.00 | None |
| cord_test_006 | `menu.nm` | mismatch | CHOCO CUS ARD PASTRY | CHOCO CUSTARD PASTRY |
| cord_test_007 | `menu.nm` | extra | None | ADD CHICKEN BOX |
| cord_test_007 | `menu.price` | extra | None | 909 |
| cord_test_009 | `menu.cnt` | extra | None | 1 |
| cord_test_012 | `total.menuqty_cnt` | mismatch | (2 | 1 |
