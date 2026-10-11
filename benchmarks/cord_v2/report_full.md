# extract-eval report

- Documents: 100
- Micro P/R/F1: 0.869 / 0.884 / **0.876** 95% CI [0.842, 0.908]
- Macro F1: **0.859** 95% CI [0.798, 0.900]
- Docs passing (doc F1 >= 1.0): 47.0%
- Bootstrap: 1000 resamples over documents, seed 0

## Per-field

| field | P | R | F1 | F1 95% CI | TP | FP | FN | missing | extra | mismatch | format_only |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `menu.cnt` | 0.949 | 0.936 | 0.943 | [0.906, 0.970] | 206 | 11 | 14 | 13 | 10 | 1 | 0 |
| `menu.nm` | 0.816 | 0.849 | 0.832 | [0.764, 0.895] | 213 | 48 | 38 | 12 | 22 | 26 | 0 |
| `menu.price` | 0.842 | 0.886 | 0.863 | [0.802, 0.917] | 218 | 41 | 28 | 9 | 22 | 6 | 13 |
| `sub_total.discount_price` | 1.000 | 0.667 | 0.800 | [0.400, 1.000] | 4 | 0 | 2 | 2 | 0 | 0 | 0 |
| `sub_total.subtotal_price` | 0.892 | 0.892 | 0.892 | [0.814, 0.958] | 58 | 7 | 7 | 1 | 1 | 3 | 3 |
| `sub_total.tax_price` | 0.861 | 0.861 | 0.861 | [0.752, 0.950] | 37 | 6 | 6 | 1 | 1 | 2 | 3 |
| `total.cashprice` | 0.895 | 0.895 | 0.895 | [0.820, 0.955] | 60 | 7 | 7 | 1 | 1 | 4 | 2 |
| `total.changeprice` | 0.864 | 0.911 | 0.887 | [0.803, 0.955] | 51 | 8 | 5 | 0 | 3 | 0 | 5 |
| `total.creditcardprice` | 0.923 | 0.750 | 0.828 | [0.615, 0.970] | 12 | 1 | 4 | 3 | 0 | 1 | 0 |
| `total.menuqty_cnt` | 0.750 | 0.724 | 0.737 | [0.560, 0.877] | 21 | 7 | 8 | 3 | 2 | 5 | 0 |
| `total.total_price` | 0.897 | 0.916 | 0.906 | [0.851, 0.953] | 87 | 10 | 8 | 2 | 4 | 0 | 6 |

## Error buckets

| bucket | count |
|---|---|
| missing | 47 |
| extra | 66 |
| mismatch | 48 |
| format_only | 32 |

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
