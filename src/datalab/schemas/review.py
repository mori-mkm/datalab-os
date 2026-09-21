from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReviewCheck(BaseModel):
    name: str
    passed: bool
    detail: str


class ReviewResult(BaseModel):
    verdict: Literal["APPROVED", "REJECTED"]
    checks: list[ReviewCheck]

    @classmethod
    def from_checks(cls, checks: list[ReviewCheck]) -> ReviewResult:
        return cls(verdict="APPROVED" if all(c.passed for c in checks) else "REJECTED", checks=checks)
