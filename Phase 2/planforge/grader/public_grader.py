from __future__ import annotations

try:
    from ._public_grader import main, grade_current_project, format_report  # type: ignore
except Exception as _import_error:
    _ERROR_TEXT = repr(_import_error)

    def grade_current_project():
        return {
            "grader": "PlanForge Public Self-Check",
            "note": "Compiled public grader binary could not be loaded on this Python/OS.",
            "required_score": 0.0,
            "required_max": 100.0,
            "optional_score": 0.0,
            "optional_max": 30.0,
            "total_score": 0.0,
            "total_max": 130.0,
            "rows": [],
            "error": _ERROR_TEXT,
        }

    def format_report(report):
        return (
            "PlanForge Public Self-Check\n"
            "===========================\n"
            "The compiled public grader binary is not available for this Python/OS.\n"
            f"Import error: {_ERROR_TEXT}\n\n"
            "Ask the TA/instructor for the matching compiled grader file, or use the private grader for official grading."
        )

    def main() -> None:
        print(format_report(grade_current_project()))
