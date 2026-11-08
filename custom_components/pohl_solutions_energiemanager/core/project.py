"""Strict, offline-only project format v1. No Home Assistant or device imports."""

from copy import deepcopy
import json
from math import isfinite
import re

MAX_BYTES = 2 * 1024 * 1024
COLLECTIONS = ("grids", "areas", "nodes", "connections", "devices", "channels", "measurements")
FORBIDDEN = {"password", "passwd", "token", "access_token", "refresh_token", "api_key",
             "secret", "credentials", "enabled_control", "actuator_enabled"}
WR_KINDS = {"hybrid_inverter", "storage_inverter"}


def _fail(path, message):
    raise ValueError(f"{path}: {message}")


def _json_tree(value, path="$", depth=0):
    if depth > 24:
        _fail(path, "JSON-Tiefe überschreitet 24")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                _fail(path, "Objektschlüssel müssen Texte sein")
            if key.casefold() in FORBIDDEN:
                _fail(f"{path}.{key}", "Zugangsdaten oder Steuerfreigaben sind nicht erlaubt")
            _json_tree(child, f"{path}.{key}", depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _json_tree(child, f"{path}[{index}]", depth + 1)
    elif isinstance(value, float):
        if not isfinite(value):
            _fail(path, "Zahl muss endlich sein")
    elif value is not None and type(value) not in (str, int, bool):
        _fail(path, "Wert ist kein JSON-Datentyp")


def _fields(obj, required, optional, path):
    if not isinstance(obj, dict):
        _fail(path, "Objekt erwartet")
    missing = set(required) - obj.keys()
    extra = obj.keys() - set(required) - set(optional)
    if missing:
        _fail(path, f"Pflichtfelder fehlen: {', '.join(sorted(missing))}")
    if extra:
        _fail(path, f"Unbekannte Felder: {', '.join(sorted(extra))}")


def _text(value, path, limit=160):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        _fail(path, f"Nichtleerer Text mit höchstens {limit} Zeichen erwartet")


def _id(value, path):
    if not isinstance(value, str) or re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", value) is None:
        _fail(path, "Ungültige stabile ASCII-Kennung")


def _choice(value, choices, path):
    if not isinstance(value, str) or value not in choices:
        _fail(path, f"Erlaubt: {', '.join(sorted(choices))}")


def _number(value, path, *, low=None, high=None, integer=False, positive=False):
    if type(value) not in (int, float) or (isinstance(value, float) and not isfinite(value)):
        _fail(path, "Endliche Zahl erwartet")
    if integer and value != int(value):
        _fail(path, "Ganzzahl erwartet")
    if (positive and value <= 0) or (low is not None and value < low) or (high is not None and value > high):
        _fail(path, "Zahl außerhalb des zulässigen Bereichs")


def _ref(value, mapping, path):
    _id(value, path)
    if value not in mapping:
        _fail(path, "Verweis auf unbekanntes Objekt")


def _acyclic(mapping, field, path):
    done = set()
    for ident in mapping:
        chain = set()
        cursor = ident
        while cursor is not None and cursor not in done:
            if cursor in chain:
                _fail(f"{path}.{ident}.{field}", "Zyklischer Verweis")
            chain.add(cursor)
            cursor = mapping[cursor].get(field)
        done.update(chain)


def validate_project(data):
    """Validate complete v1 data and return an independent deep copy."""
    return _validate_project_v1(data)


def _validate_project_v1(data, *, require_grid_measurement=True):
    """Shared structural checks; only the separate v2 draft permits no meter."""
    try:
        _json_tree(data)
        encoded = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (RecursionError, UnicodeError, OverflowError) as err:
        raise ValueError("$: Ungültige oder zu tiefe JSON-Struktur") from err
    if len(encoded) > MAX_BYTES:
        _fail("$", "Projekt überschreitet 2 MiB")
    _fields(data, ("format", "schema_version", "id", "name", "mode", *COLLECTIONS, "settings"), (), "$")
    if data["format"] != "pohl-energy-project":
        _fail("$.format", "Unbekanntes Projektformat")
    if type(data["schema_version"]) not in (int, float) or data["schema_version"] != 1:
        _fail("$.schema_version", "Nur Version 1 wird unterstützt")
    if data["mode"] != "planning_only":
        _fail("$.mode", "Nur planning_only ist erlaubt")
    _id(data["id"], "$.id")
    _text(data["name"], "$.name")
    if not isinstance(data["settings"], dict):
        _fail("$.settings", "Objekt erwartet")
    maps = {}
    total = 0
    for collection in COLLECTIONS:
        rows = data[collection]
        if not isinstance(rows, list) or len(rows) > 500:
            _fail(f"$.{collection}", "Liste mit höchstens 500 Objekten erwartet")
        total += len(rows)
        mapping = maps[collection] = {}
        for index, row in enumerate(rows):
            path = f"$.{collection}[{index}]"
            if not isinstance(row, dict):
                _fail(path, "Objekt erwartet")
            _id(row.get("id"), path + ".id")
            _text(row.get("name"), path + ".name")
            if row["id"] in mapping:
                _fail(path + ".id", "Doppelte Kennung in Sammlung")
            mapping[row["id"]] = row
    if total > 2000:
        _fail("$", "Höchstens 2000 Objekte insgesamt erlaubt")
    grids, areas, nodes, connections, devices, channels, measurements = (maps[c] for c in COLLECTIONS)
    for row in grids.values():
        _fields(row, ("id", "name"), (), f"$.grids.{row['id']}")
    for row in areas.values():
        path = f"$.areas.{row['id']}"
        _fields(row, ("id", "name", "grid_id"), (), path)
        _ref(row["grid_id"], grids, path + ".grid_id")
    for row in nodes.values():
        path = f"$.nodes.{row['id']}"
        _fields(row, ("id", "name", "grid_id", "parent_id"), (), path)
        _ref(row["grid_id"], grids, path + ".grid_id")
        if row["parent_id"] is not None:
            _ref(row["parent_id"], nodes, path + ".parent_id")
            if nodes[row["parent_id"]].get("grid_id") != row["grid_id"]:
                _fail(path + ".parent_id", "Elternknoten gehört zu anderem Netzanschluss")
    _acyclic(nodes, "parent_id", "$.nodes")
    for grid in grids:
        if sum(n["grid_id"] == grid and n["parent_id"] is None for n in nodes.values()) != 1:
            _fail(f"$.grids.{grid}", "Genau ein elektrischer Wurzelknoten erforderlich")
    for row in connections.values():
        path = f"$.connections.{row['id']}"
        _fields(row, ("id", "name", "kind"), ("host", "port", "serial_port", "baudrate", "parity", "stopbits"), path)
        _choice(row["kind"], {"modbus_tcp", "modbus_rtu_usb", "modbus_tcp_rtu_gateway", "rtu_over_tcp", "mqtt", "solarman", "ha"}, path + ".kind")
        for key in ("host", "serial_port"):
            if row.get(key) is not None:
                _text(row[key], path + "." + key, 512)
        for key, upper in (("port", 65535), ("baudrate", None)):
            if row.get(key) is not None:
                _number(row[key], path + "." + key, low=1, high=upper, integer=True)
        if row.get("parity") is not None:
            _choice(row["parity"], {"N", "E", "O"}, path + ".parity")
        if row.get("stopbits") is not None:
            _number(row["stopbits"], path + ".stopbits")
            if row["stopbits"] not in (1, 2):
                _fail(path + ".stopbits", "Erlaubt: 1 oder 2")
    for row in devices.values():
        path = f"$.devices.{row['id']}"
        _fields(row, ("id", "name", "kind", "area_id", "node_id"), ("connection_id", "via_device_id", "unit_id", "parent_id", "model", "phases", "capacity_kwh", "max_power_kw", "capabilities"), path)
        _choice(row["kind"], {"gateway", "meter", "pv_inverter", "hybrid_inverter", "storage_inverter", "battery", "ev_charger", "heater"}, path + ".kind")
        _ref(row["area_id"], areas, path + ".area_id")
        _ref(row["node_id"], nodes, path + ".node_id")
        grid = nodes[row["node_id"]]["grid_id"]
        if areas[row["area_id"]]["grid_id"] != grid:
            _fail(path, "Bereich und elektrischer Knoten gehören zu verschiedenen Netzanschlüssen")
        if row.get("connection_id") is not None:
            _ref(row["connection_id"], connections, path + ".connection_id")
        if row.get("parent_id") is not None:
            _ref(row["parent_id"], devices, path + ".parent_id")
        if row["kind"] == "battery":
            _ref(row.get("parent_id"), devices, path + ".parent_id")
            parent = devices[row["parent_id"]]
            if parent.get("kind") not in WR_KINDS or parent.get("node_id") not in nodes or nodes[parent["node_id"]]["grid_id"] != grid:
                _fail(path + ".parent_id", "Batterie benötigt Speicher-/Hybrid-WR am selben Netzanschluss")
        elif row.get("parent_id") is not None:
            _fail(path + ".parent_id", "Nur Batterien dürfen parent_id verwenden")
        if row.get("via_device_id") is not None:
            _ref(row["via_device_id"], devices, path + ".via_device_id")
            via = devices[row["via_device_id"]]
            if via.get("kind") not in WR_KINDS | {"gateway", "pv_inverter"}:
                _fail(path + ".via_device_id", "Gateway oder Wechselrichter erforderlich")
            if row.get("connection_id") is not None and via.get("connection_id") is not None and row["connection_id"] != via["connection_id"]:
                _fail(path + ".connection_id", "Gateway und Ziel müssen dieselbe Verbindung nutzen")
        if row.get("unit_id") is not None:
            _number(row["unit_id"], path + ".unit_id", low=1, high=247, integer=True)
        if row.get("phases") is not None:
            _number(row["phases"], path + ".phases", integer=True)
            if row["phases"] not in (1, 3):
                _fail(path + ".phases", "Erlaubt: 1 oder 3")
        for key in ("capacity_kwh", "max_power_kw"):
            if row.get(key) is not None:
                _number(row[key], path + "." + key, positive=True)
        if row.get("model") is not None:
            _text(row["model"], path + ".model")
        if row.get("capabilities") is not None:
            caps = row["capabilities"]
            if not isinstance(caps, list):
                _fail(path + ".capabilities", "Liste erwartet")
            for cap in caps:
                _choice(cap, {"measure", "switch", "set_power"}, path + ".capabilities")
            if len(set(caps)) != len(caps):
                _fail(path + ".capabilities", "Doppelte Fähigkeit")
    _acyclic(devices, "via_device_id", "$.devices")
    for row in channels.values():
        path = f"$.channels.{row['id']}"
        _fields(row, ("id", "name", "device_id", "quantity", "unit", "source"), ("phase",), path)
        _ref(row["device_id"], devices, path + ".device_id")
        units = {"active_power": {"W", "kW"}, "soc": {"%"}, "voltage": {"V"}, "current": {"A"}, "energy": {"Wh", "kWh"}, "temperature": {"°C"}, "state": {"bool"}}
        _choice(row["quantity"], units, path + ".quantity")
        _choice(row["unit"], units[row["quantity"]], path + ".unit")
        if row.get("phase") is not None:
            _choice(row["phase"], {"L1", "L2", "L3", "total"}, path + ".phase")
        source = row["source"]
        _fields(source, ("kind",), ("address", "function_code", "data_type", "scale", "topic", "json_path", "entity_id"), path + ".source")
        _choice(source["kind"], {"unconfigured", "modbus", "mqtt", "ha"}, path + ".source.kind")
        permitted = {"modbus": {"address", "function_code", "data_type", "scale"},
                     "mqtt": {"topic", "json_path"}, "ha": {"entity_id"},
                     "unconfigured": set()}[source["kind"]]
        for key in source.keys() - {"kind"}:
            if source[key] is not None and key not in permitted:
                _fail(path + ".source." + key, "Feld gehört nicht zur gewählten Quelle")
        if source.get("address") is not None:
            _number(source["address"], path + ".source.address", low=0, high=65535, integer=True)
        if source.get("function_code") is not None:
            _number(source["function_code"], path + ".source.function_code", integer=True)
            if source["function_code"] not in (3, 4):
                _fail(path + ".source.function_code", "Nur lesende FC03/04 erlaubt")
        if source.get("data_type") is not None:
            _choice(source["data_type"], {"u16", "s16", "u32", "s32", "float32"}, path + ".source.data_type")
        if source.get("scale") is not None:
            _number(source["scale"], path + ".source.scale")
            if source["scale"] == 0:
                _fail(path + ".source.scale", "Skalierung darf nicht null sein")
        for key in ("topic", "json_path", "entity_id"):
            if source.get(key) is not None:
                _text(source[key], path + ".source." + key, 512)
        required = {"modbus": ("address", "function_code", "data_type"), "mqtt": ("topic",), "ha": ("entity_id",), "unconfigured": ()}[source["kind"]]
        for key in required:
            if source.get(key) is None:
                _fail(path + ".source." + key, "Für diese Quelle erforderlich")
    used_channels = set()
    used_roles = set()
    grid_measurements = {grid: 0 for grid in grids}
    for row in measurements.values():
        path = f"$.measurements.{row['id']}"
        _fields(row, ("id", "name", "role", "node_id", "channel_id", "includes_device_ids"), (), path)
        _choice(row["role"], {"grid", "branch", "pv_generation", "battery_power", "consumer", "load"}, path + ".role")
        _ref(row["node_id"], nodes, path + ".node_id")
        _ref(row["channel_id"], channels, path + ".channel_id")
        if channels[row["channel_id"]]["quantity"] != "active_power":
            _fail(path + ".channel_id", "Wirkleistungskanal erforderlich")
        if row["channel_id"] in used_channels or (row["node_id"], row["role"]) in used_roles:
            _fail(path, "Kanal oder primäre Messrolle bereits zugeordnet")
        used_channels.add(row["channel_id"])
        used_roles.add((row["node_id"], row["role"]))
        grid = nodes[row["node_id"]]["grid_id"]
        meter = devices[channels[row["channel_id"]]["device_id"]]
        if nodes[meter["node_id"]]["grid_id"] != grid:
            _fail(path + ".channel_id", "Messgerät und Messknoten gehören zu verschiedenen Netzanschlüssen")
        if row["role"] == "grid":
            if nodes[row["node_id"]]["parent_id"] is not None:
                _fail(path + ".node_id", "Netzmessung muss am Wurzelknoten liegen")
            grid_measurements[grid] += 1
        included = row["includes_device_ids"]
        if not isinstance(included, list):
            _fail(path + ".includes_device_ids", "Liste erwartet")
        seen = set()
        for device in included:
            _ref(device, devices, path + ".includes_device_ids")
            if device in seen or nodes[devices[device]["node_id"]]["grid_id"] != grid:
                _fail(path + ".includes_device_ids", "Doppeltes Gerät oder fremder Netzanschluss")
            cursor = devices[device]["node_id"]
            while cursor is not None and cursor != row["node_id"]:
                cursor = nodes[cursor]["parent_id"]
            if cursor is None:
                _fail(path + ".includes_device_ids", "Gerät liegt außerhalb des gemessenen Teilbaums")
            seen.add(device)
    for grid, count in grid_measurements.items():
        if require_grid_measurement and count != 1:
            _fail(f"$.grids.{grid}", "Genau eine primäre Netzmessung erforderlich")
    return deepcopy(data)


def _parse_project_json(text):
    """Parse bounded strict JSON; duplicate keys and non-finite constants fail."""
    if not isinstance(text, str):
        _fail("$", "JSON-Text erwartet")
    try:
        if len(text.encode("utf-8")) > MAX_BYTES:
            _fail("$", "Datei überschreitet 2 MiB")

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    _fail("$", f"Doppelter JSON-Schlüssel: {key}")
                result[key] = value
            return result

        def constant(_value):
            _fail("$", "NaN/Infinity sind nicht erlaubt")

        data = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (json.JSONDecodeError, RecursionError, UnicodeError) as err:
        raise ValueError("$: Ungültiger JSON-Text") from err
    return data


def load_project_json(text):
    return validate_project(_parse_project_json(text))


def export_project_json(data):
    """Validate before exporting, preserving all valid data without secrets."""
    return json.dumps(validate_project(data), ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def project_summary(data):
    """Summarize a validated project without creating values or connections."""
    return _project_summary(validate_project(data), COLLECTIONS)


def _project_summary(project, collections):
    warnings = []
    for connection in project["connections"]:
        endpoint = "serial_port" if connection["kind"] == "modbus_rtu_usb" else "host"
        if connection["kind"] != "ha" and not connection.get(endpoint):
            warnings.append(f"connections.{connection['id']}.{endpoint}: Verbindung noch nicht eingerichtet")
    for channel in project["channels"]:
        if channel["source"]["kind"] == "unconfigured":
            warnings.append(f"channels.{channel['id']}.source: Messquelle noch nicht eingerichtet")
    return {"id": project["id"], "name": project["name"], "mode": project["mode"],
            "counts": {key: len(project[key]) for key in collections}, "warnings": warnings}
