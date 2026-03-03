"""Ensure azure.cosmos v4 API is available for tests.

The system venv may have azure-cosmos v3 (from azure-cli) which lacks
CosmosClient at the top-level import. This conftest installs a mock
module if the real one isn't usable.
"""
import sys
from unittest.mock import MagicMock


def _ensure_cosmos_mock():
    try:
        from azure.cosmos import CosmosClient  # noqa: F401
    except (ImportError, AttributeError):
        mock = MagicMock()
        # Provide the exception class tests reference
        mock.exceptions.CosmosResourceNotFoundError = type(
            "CosmosResourceNotFoundError", (Exception,), {}
        )
        sys.modules["azure.cosmos"] = mock
        sys.modules["azure.cosmos.exceptions"] = mock.exceptions


_ensure_cosmos_mock()
