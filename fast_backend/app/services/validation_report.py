"""
Structured validation report schema and helper utilities.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    """Single validation issue entry."""

    code: str
    message: str
    severity: str
    category: str
    evidence: Optional[str] = None


class ValidationReport(BaseModel):
    """Structured validation report."""

    success: bool = True
    summary: str = ""
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)
    layout_risks: List[ValidationIssue] = Field(default_factory=list)


class ValidationReportBuilder:
    """Helper to build a consistent validation response payload."""

    def __init__(self) -> None:
        self._errors: List[ValidationIssue] = []
        self._warnings: List[ValidationIssue] = []
        self._layout_risks: List[ValidationIssue] = []

    def add_error(self, code: str, message: str, evidence: Optional[str] = None) -> None:
        self._errors.append(
            ValidationIssue(
                code=code,
                message=message,
                severity="error",
                category="compilation",
                evidence=evidence,
            )
        )

    def add_warning(self, code: str, message: str, evidence: Optional[str] = None) -> None:
        self._warnings.append(
            ValidationIssue(
                code=code,
                message=message,
                severity="warning",
                category="quality",
                evidence=evidence,
            )
        )

    def add_layout_risk(self, code: str, message: str, evidence: Optional[str] = None) -> None:
        self._layout_risks.append(
            ValidationIssue(
                code=code,
                message=message,
                severity="warning",
                category="layout",
                evidence=evidence,
            )
        )

    def build(self) -> ValidationReport:
        success = len(self._errors) == 0
        summary = (
            f"errors={len(self._errors)}, "
            f"warnings={len(self._warnings)}, "
            f"layout_risks={len(self._layout_risks)}"
        )
        return ValidationReport(
            success=success,
            summary=summary,
            errors=self._errors,
            warnings=self._warnings,
            layout_risks=self._layout_risks,
        )

    def to_result(self) -> Dict[str, Any]:
        """Return legacy-compatible response with structured report included."""
        report = self.build()
        first_error = report.errors[0].message if report.errors else None
        return {
            "success": report.success,
            "error": first_error,
            "report": report.dict(),
        }
