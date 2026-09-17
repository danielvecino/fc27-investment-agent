# Historical-data policy

FC26 and FC25 are not imported as model training data unless the individual
price series can be retrieved and checked for timestamps, platform and enough
observations. FUT.GG exposes prior-season card databases, but sampled FC26
pages currently report `No price history available`; card metadata and a
season selector are not a price series.

When a verifiable source is found, store it separately with:

- source URL and retrieval timestamp;
- game edition, platform and card identifier;
- observation timestamp, price and currency;
- coverage start/end and missing-data rate.

Only then may it provide a low-weight segment prior. It must never be mixed
into FC27 snapshots or used to label current FC27 signals as known outcomes.
