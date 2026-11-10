"""OwnerPrivilegeAnalyzer and static detector tests."""

from __future__ import annotations

from app.analyzers.owner_analyzer import OwnerPrivilegeAnalyzer
from app.analyzers.static.detectors import run_detectors


def test_mint_selector_flagged():
    result = OwnerPrivilegeAnalyzer().analyze({"mint(address,uint256)": True})
    assert any(f.category.value == "minting" for f in result.findings)


def test_no_privileges_yields_no_findings():
    result = OwnerPrivilegeAnalyzer().analyze({})
    assert result.findings == []


def test_source_confirms_privilege():
    src = "function blacklist(address a, bool b) external onlyOwner { ... }"
    result = OwnerPrivilegeAnalyzer(src).analyze({})
    assert any(f.category.value == "blacklist" for f in result.findings)


def test_owner_analysis_warns_without_source():
    result = OwnerPrivilegeAnalyzer().analyze({"mint(address,uint256)": True})
    assert result.warnings


def test_detectors_skip_without_source():
    assert run_detectors(None, {}) == []


def test_arbitrary_mint_detector():
    src = "contract T { function mint(address to, uint256 a) external onlyOwner { _mint(to, a); } }"
    findings = run_detectors(src, {})
    assert any(f.id == "static.arbitrary_mint" for f in findings)


def test_unrestricted_admin_detector():
    src = "contract T { function setTaxes(uint256 a) external { buyTax = a; } }"
    findings = run_detectors(src, {})
    assert any(f.id == "static.unrestricted_admin" for f in findings)


def test_delegatecall_detector():
    src = "contract T { function f(address a) external { a.delegatecall(''); } }"
    findings = run_detectors(src, {})
    assert any(f.id == "static.delegatecall" for f in findings)


def test_blacklist_detector():
    src = "contract T { mapping(address=>bool) blacklist; }"
    findings = run_detectors(src, {})
    assert any(f.id == "static.blacklist" for f in findings)
