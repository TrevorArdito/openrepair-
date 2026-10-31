"""The hardware module isn't built yet, but its safety contract is: writes need confirmation."""

import pytest

from app.modules.hardware.interface import ConfirmationRequired, WriteAction


class FakeClearCodes(WriteAction):
    def __init__(self):
        super().__init__()
        self.writes = 0

    def warnings(self, action):
        return ["Clearing codes erases freeze-frame data."]

    def _do_write(self, req):
        self.writes += 1
        return "ok"


def test_write_without_confirmation_is_refused():
    action = FakeClearCodes()
    req = action.prepare("clear_dtcs", vehicle_id=1)
    assert req.warnings
    with pytest.raises(ConfirmationRequired):
        action.execute(req.token)
    assert action.writes == 0


def test_confirmed_write_runs_once():
    action = FakeClearCodes()
    req = action.prepare("clear_dtcs", vehicle_id=1)
    action.confirm(req.token)
    assert action.execute(req.token) == "ok"
    with pytest.raises(ConfirmationRequired):
        action.execute(req.token)  # token can't be reused
    assert action.writes == 1
