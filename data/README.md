# Public dataset

Source used in the COMPX527 proposal: [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) (CC BY 4.0).

- Transactions: 01 Dec 2010 – 09 Dec 2011, UK gift retailer
- About 541,909 rows
- Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`

The full files live in `data/uci/` (gitignored; too large for GitHub):

```bash
mkdir -p data/uci
curl -fL -o data/uci/online-retail.zip \
  "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
unzip -o data/uci/online-retail.zip -d data/uci
```

A tiny schema sample is committed at `data/samples/transactions_sample.csv`.
The API also ships a copy at `backend/data/samples/transactions_sample.csv` for Docker when S3 is unavailable.
The live template is the same file in S3 (`S3_TRANSACTIONS_SAMPLE_KEY`, default `public/transactions_sample.csv`), served by `GET /uploads/transactions-sample`.
Pytest writes its own tiny CSV in a temp directory; it does not depend on these files.
