import pytest
from core.skills.sandbox import SkillSandbox
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_skill_sandbox_execution():
    mock_ltm = AsyncMock()
    # Mock a skill that just returns a success dict
    mock_ltm.get_skill.return_value = {
        "script_content": "result = {'success': True, 'msg': 'hello ' + args.get('name')}",
        "version": 1
    }
    
    sandbox = SkillSandbox(ltm_client=mock_ltm)
    result = await sandbox.execute_skill("hello_skill", {"name": "world"})
    
    assert result["status"] == "success"
    assert result["result"]["msg"] == "hello world"

@pytest.mark.asyncio
async def test_skill_sandbox_imports_blocked():
    mock_ltm = AsyncMock()
    # This should fail because 'os' is not in globals and __builtins__ import is restricted
    mock_ltm.get_skill.return_value = {
        "script_content": "import os\nresult = {'success': True}",
        "version": 1
    }
    
    sandbox = SkillSandbox(ltm_client=mock_ltm)
    result = await sandbox.execute_skill("bad_skill")
    
    assert result["status"] == "error"
    assert "import" in result["message"] or "os" in result["message"] or "not found" in result["message"] or "import of os halted" in result["message"] or "__import__ not found" in str(result)
