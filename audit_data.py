from pathlib import Path
from core.data_quality import audit_data
r=audit_data(Path(__file__).parent/'data')
print(f'Data audit: {"PASS" if r.passed else "FAIL"} | errors={len(r.errors)} warnings={len(r.warnings)}')
for x in r.issues: print(f'[{x.severity}] {x.dataset}: {x.message}')
raise SystemExit(0 if r.passed else 1)
