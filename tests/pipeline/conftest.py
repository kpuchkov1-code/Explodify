# tests/pipeline/conftest.py
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def two_box_glb() -> Path:
    p = FIXTURES_DIR / "two_box_assembly.glb"
    assert p.exists(), f"Run: python {FIXTURES_DIR}/create_test_assembly.py"
    return p
