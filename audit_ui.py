from pathlib import Path
from core.ui_contract import audit_ui_contract

path = Path(__file__).parent / "app.py"
issues = audit_ui_contract(path)
if issues:
    for issue in issues:
        print(f"ERROR {issue.code} line {issue.line}: {issue.message}")
    raise SystemExit(1)
print("UI contract: PASS (0 issues)")
