"""Reusable read contract for device profiles, independent of wire framing."""

from typing import Protocol


class RegisterReader(Protocol):
    async def read_registers(self, *, unit_id: int, address: int, count: int,
                             function_code: int = 3) -> tuple[int, ...]:
        """Read FC03/04 registers; implementations own framing and serialization."""
        ...
