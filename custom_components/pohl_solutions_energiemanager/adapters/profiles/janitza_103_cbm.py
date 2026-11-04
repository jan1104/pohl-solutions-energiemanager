"""UMG 103-CBM firmware >=2.0, explicit Big Endian power registers in W.

Source: Janitza Modbus address list 2.057.005.1.e (01/2023), address table.
https://www.janitza.com/files/download/manuals/current/UMG103-CBM/janitza-mal-umg103cbm-en.pdf
Not a UMG 103 without CBM, not the UMG 604-PRO's own register profile.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from ..transports.base import RegisterReader
from ..transports.modbus_tcp import decode_registers


@dataclass(frozen=True, slots=True)
class JanitzaPowerSnapshot:
    """Acquisition time is not a device-originated timestamp or freshness proof."""

    unit_id: int
    acquired_at: datetime
    l1_kw: float
    l2_kw: float
    l3_kw: float
    total_kw: float


async def read_power(client: RegisterReader, *, unit_id: int,
                     power_sign: int = 1) -> JanitzaPowerSnapshot:
    """Explicit read only; configured CT ratios already apply to float values.

    Caller must verify firmware, addressing, meter role and CT direction. The
    profile preserves native signs unless the supplied direction is inverted.
    """
    if type(power_sign) is not int or power_sign not in (-1, 1):
        raise ValueError("power_sign must be 1 or -1")
    registers = await client.read_registers(unit_id=unit_id, address=19020, count=8)
    values = [decode_registers(registers[i:i + 2], "float32", scale=power_sign / 1000)
              for i in range(0, 8, 2)]
    return JanitzaPowerSnapshot(unit_id, datetime.now(timezone.utc), *values)
