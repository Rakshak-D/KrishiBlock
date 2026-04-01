from __future__ import annotations

import pytest

from app.services.session import load_session


@pytest.mark.asyncio
async def test_load_session_returns_default_state_when_missing():
    state = await load_session('+919999000099')

    assert state['phone'] == '+919999000099'
    assert state['is_registered'] is False
    assert state['flow_step'] == 0
    assert state['response']
