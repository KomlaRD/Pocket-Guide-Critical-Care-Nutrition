"""Static Shiny Express UI contract checks used by CI.

These checks target compatibility regressions that can be detected without a
browser or an installed Shiny runtime. They are intentionally conservative and
only inspect literal IDs/call shapes used by this project.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UIContractIssue:
    code: str
    line: int
    message: str


EXPRESS_FORBIDDEN = {"output_ui", "download_button"}
INPUT_PREFIX = "input_"


def _literal_first_arg(call: ast.Call) -> str | None:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value
    return None


def audit_ui_contract(path: str | Path) -> list[UIContractIssue]:
    path = Path(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    issues: list[UIContractIssue] = []
    input_ids: dict[str, int] = {}
    download_functions: dict[str, int] = {}
    manual_download_ids: dict[str, int] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            name = node.func.attr
            if isinstance(owner, ast.Name) and owner.id == "ui":
                if name in EXPRESS_FORBIDDEN:
                    issues.append(UIContractIssue("EXPRESS_API", node.lineno, f"ui.{name} is not permitted in this app."))
                if name == "layout_columns" and node.args:
                    issues.append(UIContractIssue("LAYOUT_COLUMNS_POSITIONAL", node.lineno, "ui.layout_columns must be used as a context manager with keyword configuration, not UI children as positional arguments."))
                if name.startswith(INPUT_PREFIX):
                    ident = _literal_first_arg(node)
                    if ident:
                        if ident in input_ids:
                            issues.append(UIContractIssue("DUPLICATE_INPUT_ID", node.lineno, f"Input ID {ident!r} was already registered on line {input_ids[ident]}."))
                        else:
                            input_ids[ident] = node.lineno
            if isinstance(owner, ast.Name) and owner.id == "core_ui" and name == "download_button":
                ident = _literal_first_arg(node)
                if ident:
                    manual_download_ids[ident] = node.lineno

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                    if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "render" and decorator.func.attr == "download":
                        download_functions[node.name] = node.lineno

    for ident, line in manual_download_ids.items():
        if ident in download_functions:
            issues.append(UIContractIssue("DUPLICATE_DOWNLOAD_ID", line, f"Download ID {ident!r} is registered both manually and by @render.download."))
    return sorted(issues, key=lambda x: (x.line, x.code))


def require_ui_contract(path: str | Path) -> None:
    issues = audit_ui_contract(path)
    if issues:
        details = "\n".join(f"{i.code} line {i.line}: {i.message}" for i in issues)
        raise RuntimeError(f"Shiny UI contract failed:\n{details}")
