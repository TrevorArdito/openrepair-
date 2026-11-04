"""Contract future hardware adapters must implement. Nothing here talks to hardware yet.

The point of defining it now: any action that writes to a vehicle has to be
confirmed by the user first, and the base class enforces that."""

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class ConfirmationRequired(Exception):
    """Raised when a write is attempted without a valid, matching confirmation."""


@dataclass
class WriteRequest:
    action: str  # e.g. "clear_dtcs", "program_key"
    vehicle_id: int
    warnings: list[str] = field(default_factory=list)
    token: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    confirmed: bool = False


class WriteAction(ABC):
    """Two-step write: prepare() returns warnings + token; execute() needs the confirmed token."""

    def __init__(self) -> None:
        self._pending: dict[str, WriteRequest] = {}

    def prepare(self, action: str, vehicle_id: int) -> WriteRequest:
        req = WriteRequest(action=action, vehicle_id=vehicle_id, warnings=self.warnings(action))
        self._pending[req.token] = req
        return req

    def confirm(self, token: str) -> None:
        if token not in self._pending:
            raise ConfirmationRequired("unknown_token")
        self._pending[token].confirmed = True

    def execute(self, token: str) -> object:
        req = self._pending.pop(token, None)
        if req is None or not req.confirmed:
            raise ConfirmationRequired("not_confirmed")
        return self._do_write(req)

    @abstractmethod
    def warnings(self, action: str) -> list[str]: ...

    @abstractmethod
    def _do_write(self, req: WriteRequest) -> object: ...


class ReadAdapter(ABC):
    """Read-only access: live data, stored/pending codes, freeze frame."""

    @abstractmethod
    def read_dtcs(self) -> list[str]: ...

    @abstractmethod
    def read_pids(self, pids: list[str]) -> dict[str, float]: ...
