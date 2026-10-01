# Abbott Ghana reference catalogue — M11.2

The user has confirmed that the Abbott product formulations are sufficiently similar to products encountered in Ghana to use as the application's reference catalogue. Exact Abbott formulation names and source bases remain visible because different forms may appear on the Ghanaian market.

## Included
- Ensure Original Shake
- Ensure Plus Nutrition Shake
- PediaSure Enteral Formula 1.0 Cal — used as the standard PediaSure formula
- All Glucerna entries in this Abbott guide:
  Glucerna 1.0 Cal; 1.2 Cal; 1.5 Cal; 30g Protein Shake; Hunger Smart Meal Size Shake; Hunger Smart Powder; Hunger Smart Shake; Mini Treats Bars; Shake; Snack Bars; Snack Shake; Therapeutic Nutrition Shake.

## Calculation safety
Liquid enteral/oral formulas, oral-only liquids, powders and solid snacks remain distinct product classes.
`product_use_policy.csv` prevents dry powder and bars from being treated as liquid formula volume/rate inputs. Oral shakes retain their source route restrictions; they are not silently converted into tube-feeding products.

The exact manufacturer serving/preparation basis is preserved. Flavor-specific values are not averaged. Where the guide reports variant flavor values, the recorded reference flavor is identified by the source product/preparation; additional flavor records can be added later if clinically useful.

All records remain in the review pipeline (`PENDING_VERIFICATION`, inactive) until the existing promotion step is deliberately run. This status means the database has not completed its independent review workflow; it does not negate the user's decision that these Abbott formulations are appropriate Ghana reference products.

Future Ghanaian/local formulas should be added as independent products/preparations with their own provenance and evidence, never by overwriting Abbott records.
