from importlib import import_module

import pytest


@pytest.mark.parametrize(
    "module_name", ["src.rag", "src.agents", "src.api", "src.ui", "src.eval"]
)
def test_application_module_can_be_imported(module_name: str) -> None:
    import_module(module_name)
