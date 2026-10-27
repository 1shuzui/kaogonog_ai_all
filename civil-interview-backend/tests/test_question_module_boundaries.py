"""Guard the dependency boundaries and compatibility exports used by callers."""
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("module", [
    "app.services.question_labels",
    "app.services.question_filters",
    "app.services.targeted_catalog",
])
def test_pure_question_modules_import_without_runtime_services(module):
    script = """
import importlib
import importlib.abc
import sys

class RejectRuntimeServices(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == prefix or fullname.startswith(prefix + '.') for prefix in
               ('app.core', 'app.models', 'app.db', 'fastapi', 'sqlalchemy', 'openai')):
            raise AssertionError('Pure question module imported ' + fullname)

sys.meta_path.insert(0, RejectRuntimeServices())
importlib.import_module(sys.argv[1])
"""
    result = subprocess.run([sys.executable, "-c", script, module],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_legacy_question_exports_share_the_extracted_implementations():
    from app.core import ai
    from app.services import question_filters, question_labels, question_service

    assert ai.PROVINCE_NAMES is question_labels.PROVINCE_NAMES
    assert ai.DIMENSION_NAMES is question_labels.DIMENSION_NAMES
    assert ai.POSITION_NAMES is question_labels.POSITION_NAMES
    assert question_service._filter_bank_rows is question_filters.filter_bank_rows
    assert question_service._normalize_province is question_filters.normalize_province
    assert question_service._apply_target_filters is question_filters.apply_target_filters
    assert question_service.POSITION_ALIASES is question_filters.POSITION_ALIASES


def test_positions_endpoint_keeps_the_shared_catalog_contract():
    from app.api.v1.routes.targeted_routes import get_positions
    from app.services.targeted_catalog import POSITIONS, TARGETED_POSITION_TREE

    result = get_positions()
    assert result["tree"] is TARGETED_POSITION_TREE
    assert result["legacy"] is POSITIONS
