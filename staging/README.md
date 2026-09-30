# M6.1: Manufacturer-product ingestion staging

The template CSVs are **empty by design**. No Ghana-market products or nutrient values have been invented or represented as verified. Collect a manufacturer's market-specific current label, technical sheet, or official manufacturer webpage, recording its direct HTTPS URL, version/date and date accessed. Capture the exact product variant, country/market, formulation, serving basis and every documented nutrient and unit. Missing nutrients are unknown, not zero.

Create a separate staging folder using `template/` as the schema, then run:

```bash
python -m core.product_ingest staging/my_batch --nutrient-catalog data/metadata/nutrients.csv --json staging/report.json
```

The validator requires `PENDING_VERIFICATION` and `active=false`, checks identity, references, units, numeric amounts, source URLs and source metadata, and exits nonzero on errors. A passing staging report **does not** constitute source authenticity or clinical approval. A second qualified reviewer must compare every transcribed value and serving basis against the manufacturer document, confirm the current local-market formulation, document reviewer/date, and explicitly approve a controlled promotion to `VERIFIED_CURRENT`. Do not copy unreviewed staging files into `data/products` or make them selectable for patient calculations.

The current app retains demonstration-only data, with its existing warnings. A verified product import/promotion gate and verified Ghana-market product population require genuine source documents and independent clinical review.

## M6.2: Independent review and controlled export

**No real manufacturer products are bundled:** genuine market-specific source documents and an independent qualified reviewer are required before clinical use.

1. Collect genuine manufacturer documentation and fill staging CSVs; keep all records pending and inactive.
2. Validate: `python -m core.product_ingest staging/my_batch --nutrient-catalog data/metadata/nutrients.csv`.
3. Generate the exact input digest: `python -c "from core.product_review import batch_digest; print(batch_digest('staging/my_batch'))"`.
4. Copy `staging/review_attestation.template.json` to a separate review file. An independent qualified reviewer must personally compare **every supplied nutrient**, serving basis, exact formulation, market, source authenticity and authorization; enter the digest, names, date, notes, and change each check to `true` only after review. The tool cannot verify a document or professional credentials automatically.
5. Generate a **separate** reviewed candidate: `python -m core.product_review staging/my_batch staging/review.json staging/reviewed_batch --nutrient-catalog data/metadata/nutrients.csv`. The original pending CSVs remain unchanged. A digest mismatch or missing attestation fails closed.
6. Examine the exported CSVs and `review_manifest.json`, reconcile conflicts with existing product IDs and preparation IDs, and complete your institution's clinical release/deployment process. The app's bundled demonstration database is **not** automatically changed.

Do not claim a product is manufacturer-verified merely because the staging validator or export command succeeds; approval is a documented human attestation.
