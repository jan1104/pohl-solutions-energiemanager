"""Project-scoped shared read-only connections; no setup/import side effects."""

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from ipaddress import ip_address

from .transports.modbus_tcp import ReadOnlyModbusTCP
from .transports.rtu_over_tcp import ReadOnlyRTUOverTCP


class UnsupportedTransportError(ValueError):
    """A configured transport has no implemented reader; never fall back."""


@dataclass(frozen=True, slots=True)
class ConnectionReader:
    """A profile-facing reference with no permission to close a shared client."""

    _manager: "ReadOnlyConnectionManager"
    connection_id: str

    async def read_registers(self, *, unit_id, address, count, function_code=3):
        return await self._manager.read_registers(self.connection_id, unit_id=unit_id,
                                                  address=address, count=count,
                                                  function_code=function_code)


def _host_key(host):
    try:
        return str(ip_address(host))
    except ValueError:
        return host.lower().removesuffix(".")


class ReadOnlyConnectionManager:
    """One owner per project runtime, many device references, explicit reads.

    TCP and TCP-to-RTU gateways both use native MBAP frames. They share a client
    for identical normalized host/port, including alias configuration IDs.
    Transparent RTU tunnels share their own raw-frame client. Mixing MBAP and
    raw RTU on one configured endpoint is rejected before traffic.
    DNS/IP aliases and USB identities are not resolved or probed here.
    """

    def __init__(self, connections, *, timeout=3.0):
        # Project validation belongs to the configuration layer. The generic
        # transport layer still checks IDs and all connection parameters it uses.
        self._connections = {}
        for connection in deepcopy(connections):
            key = connection.get("id")
            if not isinstance(key, str) or not key or key in self._connections:
                raise ValueError("Connection IDs must be unique nonempty strings")
            self._connections[key] = connection
        # Validate the common transport timeout without opening a connection.
        ReadOnlyModbusTCP("localhost", timeout=timeout)
        self._timeout = timeout
        self._clients = {}
        self._closed = False
        self._close_task = None

    def for_connection(self, connection_id):
        """Create a reference for a profile. No traffic or client creation."""
        if self._closed:
            raise RuntimeError("Connection manager is closed")
        if connection_id not in self._connections:
            raise ValueError(f"Unknown connection: {connection_id}")
        return ConnectionReader(self, connection_id)

    def _client(self, connection_id):
        if self._closed:
            raise RuntimeError("Connection manager is closed")
        if connection_id not in self._connections:
            raise ValueError(f"Unknown connection: {connection_id}")
        connection = self._connections[connection_id]
        if connection.get("kind") not in ("modbus_tcp", "modbus_tcp_rtu_gateway", "rtu_over_tcp"):
            raise UnsupportedTransportError(f"Transport not implemented: {connection.get('kind')}")
        host = connection.get("host")
        if not isinstance(host, str) or not host:
            raise ValueError("Configure an explicit host before reading")
        port = connection.get("port")
        raw_rtu = connection["kind"] == "rtu_over_tcp"
        if raw_rtu and port is None:
            raise ValueError("Configure an explicit TCP tunnel port before reading")
        port = 502 if port is None else port
        if type(port) is float and port.is_integer():
            port = int(port)
        # Validate BEFORE normalization so whitespace/URL-like input is never
        # silently repaired. Construction alone does not connect or resolve DNS.
        reader_type = ReadOnlyRTUOverTCP if raw_rtu else ReadOnlyModbusTCP
        candidate = reader_type(host, port, timeout=self._timeout)
        key = (_host_key(host), port)
        # Reject contradictory configured aliases before the first request,
        # even if the other connection has never been used. Drafts stay inert.
        for other in self._connections.values():
            other_kind = other.get("kind")
            if other_kind not in ("modbus_tcp", "modbus_tcp_rtu_gateway", "rtu_over_tcp"):
                continue
            other_host, other_port = other.get("host"), other.get("port")
            other_raw = other_kind == "rtu_over_tcp"
            if not isinstance(other_host, str) or not other_host or (other_raw and other_port is None):
                continue
            other_port = 502 if other_port is None else other_port
            if (_host_key(other_host), other_port) == key and other_raw != raw_rtu:
                raise ValueError("Conflicting MBAP and raw RTU framing for the same endpoint")
        if key in self._clients and type(self._clients[key]) is not reader_type:
            raise ValueError("Conflicting MBAP and raw RTU framing for the same endpoint")
        if key not in self._clients:
            self._clients[key] = candidate
        return self._clients[key]

    async def read_registers(self, connection_id, *, unit_id, address, count, function_code=3):
        """Use an existing connection reference; FC03/04 only, explicit target."""
        client = self._client(connection_id)
        return await client.read_registers(unit_id=unit_id, address=address, count=count,
                                           function_code=function_code)

    async def async_close(self):
        """Block new reads, drain current requests, then close all shared clients.

        Cancelling a caller does not interrupt cleanup of shared transports.
        Repeated close calls await the same cleanup, never reopen the manager.
        """
        if self._close_task is None:
            self._closed = True
            self._close_task = asyncio.create_task(self._close_clients())
        await asyncio.shield(self._close_task)

    async def _close_clients(self):
        results = await asyncio.gather(*(c.async_close() for c in self._clients.values()),
                                       return_exceptions=True)
        self._clients.clear()
        errors = [r for r in results if isinstance(r, BaseException)]
        if errors:
            raise RuntimeError("Could not close all shared transports") from errors[0]
