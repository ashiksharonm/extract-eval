# Run comparison: report_trunc vs report_full

100 paired documents. Delta = report_full - report_trunc; CI is a paired bootstrap over documents.

| metric | report_trunc | report_full | delta |
|---|---|---|---|
| micro F1 | 0.726 | 0.876 | +0.151 [0.078, 0.234] |
| macro F1 | 0.710 | 0.859 | +0.149 [0.080, 0.229] |
| pass rate | 0.440 | 0.470 | +0.030  |
| `menu.cnt` F1 | 0.736 | 0.943 | +0.206  |
| `menu.nm` F1 | 0.668 | 0.832 | +0.164  |
| `menu.price` F1 | 0.678 | 0.863 | +0.185  |
| `sub_total.discount_price` F1 | 0.500 | 0.800 | +0.300  |
| `sub_total.subtotal_price` F1 | 0.743 | 0.892 | +0.149  |
| `sub_total.tax_price` F1 | 0.676 | 0.861 | +0.184  |
| `total.cashprice` F1 | 0.884 | 0.895 | +0.012  |
| `total.changeprice` F1 | 0.855 | 0.887 | +0.033  |
| `total.creditcardprice` F1 | 0.522 | 0.828 | +0.306  |
| `total.menuqty_cnt` F1 | 0.755 | 0.737 | -0.018  |
| `total.total_price` F1 | 0.793 | 0.906 | +0.113  |

Pass to fail: 0 docs; fail to pass: 3 docs.
- fail to pass: cord_test_029, cord_test_061, cord_test_075
