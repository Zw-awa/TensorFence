from __future__ import annotations

import os
import platform
import re

from .models import EnvironmentFacts, Fact, TargetProfile
from .transports import TargetTransport, TransportError, make_transport


def _fact_from_command(key: str, transport: TargetTransport, command: list[str], missing: str) -> Fact:
    try:
        result = transport.run(command)
    except TransportError as exc:
        return Fact(key=key, status="unknown", evidence=str(exc), recommendation="Verify target connection settings.")
    if result.returncode == 0 and result.stdout:
        return Fact(key=key, status="ready", value=result.stdout, evidence=" ".join(command))
    evidence = result.stderr or result.stdout or missing
    return Fact(key=key, status="warning", evidence=evidence, recommendation=missing)


def _python_command(target: TargetProfile) -> list[str]:
    connection = target.connection
    if connection.conda_path and connection.conda_env:
        return [connection.conda_path, "run", "-n", connection.conda_env, connection.python or "python"]
    return [connection.python or ("python" if target.transport == "local" and os.name == "nt" else "python3")]


def _optional_conda_fact(target: TargetProfile, transport: TargetTransport) -> Fact:
    command = [target.connection.conda_path or "conda", "--version"]
    result_fact = _fact_from_command(
        "conda", transport, command, "Conda is optional; configure it only when the target uses a Conda environment."
    )
    if target.connection.conda_path or target.connection.conda_env:
        return result_fact
    if result_fact.status != "ready":
        return Fact(key="conda", status="ready", value="not installed (optional)", evidence=result_fact.evidence)
    return result_fact


def discover_target(target: TargetProfile, transport: TargetTransport | None = None) -> EnvironmentFacts:
    transport = transport or make_transport(target)
    facts = [Fact(key="transport", status="ready", value=target.transport, evidence="target profile")]
    if target.transport == "local":
        facts.extend(
            [
                Fact(key="os", status="ready", value=platform.system(), evidence="local host"),
                Fact(key="architecture", status="ready", value=platform.machine(), evidence="local host"),
            ]
        )
    else:
        facts.extend(
            [
                _fact_from_command("os", transport, ["uname", "-s"], "Target does not expose a POSIX uname command."),
                _fact_from_command("architecture", transport, ["uname", "-m"], "Target architecture could not be identified."),
            ]
        )
    python = _python_command(target)
    facts.append(_fact_from_command("python", transport, [*python, "--version"], "Configure a Python 3.10+ executable or Conda environment."))
    facts.append(_optional_conda_fact(target, transport))
    if target.profile in {"rknn-host", "rk3588-board"}:
        facts.append(
            _fact_from_command(
                "rknn_toolkit",
                transport,
                [*python, "-c", "from importlib.metadata import version; print(version('rknn-toolkit2'))"],
                "Install RKNN Toolkit2 in the selected Python environment.",
            )
        )
    if target.profile == "rk3588-board":
        facts.extend(
            [
                _fact_from_command("board_compatible", transport, ["cat", "/proc/device-tree/compatible"], "Verify this is a Rockchip board and that device-tree access is available."),
                _fact_from_command("npu_device", transport, ["sh", "-lc", "ls /dev/rknpu* 2>/dev/null | head -n 1"], "NPU device is not visible; verify the NPU driver and permissions."),
                _fact_from_command("npu_driver", transport, ["sh", "-lc", "cat /sys/kernel/debug/rknpu/version 2>/dev/null"], "NPU driver version is unavailable; verify debugfs access or record it manually."),
                _fact_from_command("rknn_runtime", transport, ["sh", "-lc", "ldconfig -p 2>/dev/null | grep -m1 librknnrt"], "RKNN runtime library is not discoverable through ldconfig."),
                _fact_from_command("rknn_lite", transport, [*python, "-c", "from rknnlite.api import RKNNLite; print('installed')"], "Install a compatible RKNN Lite/runtime package for board-local Python use."),
            ]
        )
    return EnvironmentFacts(target=target, facts=facts)


def _version_matches(value: str | None, requirement: str) -> bool | None:
    if not value:
        return None
    numbers = tuple(int(item) for item in re.findall(r"\d+", value)[:3])
    if not numbers:
        return None
    for clause in requirement.split(","):
        match = re.fullmatch(r"\s*(>=|<=|==|>|<)?\s*(\d+(?:\.\d+){0,2})\s*", clause)
        if not match:
            return None
        operator = match.group(1) or "=="
        required = tuple(int(item) for item in match.group(2).split("."))
        padded_numbers = numbers + (0,) * (len(required) - len(numbers))
        padded_required = required + (0,) * (len(numbers) - len(required))
        if not {">=": padded_numbers >= padded_required, "<=": padded_numbers <= padded_required, "==": padded_numbers == padded_required, ">": padded_numbers > padded_required, "<": padded_numbers < padded_required}[operator]:
            return False
    return True


def evaluate_compatibility(facts: EnvironmentFacts) -> EnvironmentFacts:
    """Apply conservative profile policy without changing any target state."""
    updated = list(facts.facts)
    policy = facts.target.version_policy
    if policy.python:
        python_fact = next((fact for fact in updated if fact.key == "python"), None)
        version_ok = _version_matches(python_fact.value if python_fact else None, policy.python)
        if version_ok is False:
            updated.append(Fact(key="policy.python", status="blocked", evidence=python_fact.value if python_fact else None, recommendation=f"Use Python {policy.python} or newer as declared by this target profile."))
        elif version_ok is None:
            updated.append(Fact(key="policy.python", status="unknown", recommendation="Python version policy could not be evaluated."))
    if policy.rknn_toolkit:
        toolkit_fact = next((fact for fact in updated if fact.key == "rknn_toolkit"), None)
        version_ok = _version_matches(toolkit_fact.value if toolkit_fact else None, policy.rknn_toolkit)
        if version_ok is False:
            updated.append(Fact(key="policy.rknn_toolkit", status="blocked", evidence=toolkit_fact.value if toolkit_fact else None, recommendation=f"Use RKNN Toolkit {policy.rknn_toolkit} or newer as declared by this target profile."))
        elif version_ok is None:
            updated.append(Fact(key="policy.rknn_toolkit", status="unknown", recommendation="RKNN Toolkit policy could not be evaluated."))
    return facts.model_copy(update={"facts": updated})
