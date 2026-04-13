"""Query the webapp for trusted details about the current instance.

The container holds a per-instance key at ``/etc/key`` (root-readable only).
Requests signed with this key are verified by the webapp, which resolves all
response fields from its own database. The returned info is therefore
authoritative and cannot be spoofed from inside the container.
"""

import typing as ty
from dataclasses import dataclass
from pathlib import Path

import requests
from itsdangerous import TimedSerializer

from .error import RefUtilsError

KEY_PATH = Path("/etc/key")
INSTANCE_ID_PATH = Path("/etc/instance_id")
INSTANCE_INFO_URL = "http://ssh-reverse-proxy:8000/api/instance/info"


class InstanceInfoError(RefUtilsError):
    """Raised when instance info cannot be retrieved."""


@dataclass
class InstanceInfo:
    instance_id: int
    is_submission: bool
    user_full_name: str
    user_mat_num: ty.Optional[str]
    is_admin: bool
    is_grading_assistant: bool
    exercise_short_name: str
    exercise_version: int


def _sign_request(instance_id: int, key: bytes, payload: ty.Dict[str, ty.Any]) -> str:
    signer = TimedSerializer(key, salt="from-container-to-web")
    payload = dict(payload)
    payload["instance_id"] = instance_id
    return signer.dumps(payload)  # type: ignore[no-any-return]


def get_instance_info(timeout_s: float = 10.0) -> InstanceInfo:
    """Fetch trusted details about the current instance from the webapp.

    All fields originate from the webserver's database; the request is signed
    with the instance-specific key at ``/etc/key``, which is not accessible to
    the student user. Use this to branch test behavior on user role without
    trusting anything the student can tamper with.

    Raises:
        InstanceInfoError: if credentials are missing, the webapp is
            unreachable, or the response cannot be parsed.
    """
    try:
        key = KEY_PATH.read_bytes()
        instance_id = int(INSTANCE_ID_PATH.read_text().strip())
    except OSError as e:
        raise InstanceInfoError(f"Failed to read instance credentials: {e}") from e

    signed = _sign_request(instance_id, key, {})
    try:
        resp = requests.post(INSTANCE_INFO_URL, json=signed, timeout=timeout_s)
    except requests.RequestException as e:
        raise InstanceInfoError(f"Failed to reach webapp: {e}") from e

    try:
        data = resp.json()
    except ValueError as e:
        raise InstanceInfoError(f"Invalid JSON response (status={resp.status_code}): {e}") from e

    if resp.status_code != 200:
        detail = data.get("error", data) if isinstance(data, dict) else data
        raise InstanceInfoError(f"Info request failed (status={resp.status_code}): {detail}")

    if not isinstance(data, dict):
        raise InstanceInfoError(f"Unexpected response body: {data!r}")

    try:
        return InstanceInfo(**data)
    except TypeError as e:
        raise InstanceInfoError(f"Response missing or extra fields: {e}") from e
