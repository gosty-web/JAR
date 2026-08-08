import pytest
import os
from unittest.mock import patch, MagicMock
from core.memory.long_term import LongTermMemoryClient

@pytest.fixture
def mock_supabase():
    with patch("core.memory.long_term.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        yield mock_client

@pytest.fixture
def ltm_client(mock_supabase):
    # Pass dummy url/key to ensure it initializes
    return LongTermMemoryClient(url="http://mock", key="mock")

@pytest.mark.asyncio
async def test_store_memory(ltm_client, mock_supabase):
    mock_supabase.table().insert().execute.return_value.data = [{"id": "123"}]
    success = await ltm_client.store_memory("test_cat", "test content")
    assert success is True
    mock_supabase.table.assert_called_with("long_term_memory")
    mock_supabase.table().insert.assert_called_once()

@pytest.mark.asyncio
async def test_save_skill(ltm_client, mock_supabase):
    mock_supabase.table().upsert().execute.return_value.data = [{"id": "456"}]
    success = await ltm_client.save_skill("test_skill", "desc", "print('hello')", 1)
    assert success is True
    mock_supabase.table.assert_called_with("skills")
