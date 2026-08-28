from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass

from .models import TargetProfile


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


class TransportError(RuntimeError):
    pass


class TargetTransport:
    def __init__(self, target: TargetProfile) -> None:
        self.target = target

    def run(self, command: list[str], timeout: int = 15, input_text: str | None = None) -> CommandResult:
        raise NotImplementedError


class LocalTransport(TargetTransport):
    def run(self, command: list[str], timeout: int = 15, input_text: str | None = None) -> CommandResult:
        try:
            completed = subprocess.run(command, text=True, input=input_text, capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TransportError(str(exc)) from exc
        return CommandResult(command, completed.returncode, completed.stdout.strip(), completed.stderr.strip())


class WslTransport(TargetTransport):
    def run(self, command: list[str], timeout: int = 15, input_text: str | None = None) -> CommandResult:
        distro = self.target.connection.wsl_distro
        if not distro:
            raise TransportError("WSL distro is not configured")
        invocation = ["wsl", "-d", distro, "--", "sh", "-lc", "exec " + shlex.join(command)]
        try:
            completed = subprocess.run(invocation, text=True, input=input_text, capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TransportError(str(exc)) from exc
        return CommandResult(command, completed.returncode, completed.stdout.strip(), completed.stderr.strip())


class SshTransport(TargetTransport):
    def run(self, command: list[str], timeout: int = 15, input_text: str | None = None) -> CommandResult:
        connection = self.target.connection
        if not connection.host:
            raise TransportError("SSH host is not configured")
        endpoint = f"{connection.user}@{connection.host}" if connection.user else connection.host
        invocation = ["ssh", "-p", str(connection.port)]
        if connection.identity_file:
            invocation.extend(("-i", connection.identity_file))
        invocation.extend((endpoint, "sh", "-lc", "exec " + shlex.join(command)))
        try:
            completed = subprocess.run(invocation, text=True, input=input_text, capture_output=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise TransportError(str(exc)) from exc
        return CommandResult(command, completed.returncode, completed.stdout.strip(), completed.stderr.strip())


def make_transport(target: TargetProfile) -> TargetTransport:
    if target.transport == "local":
        return LocalTransport(target)
    if target.transport == "wsl":
        return WslTransport(target)
    if target.transport == "ssh":
        return SshTransport(target)
    raise TransportError(f"unsupported transport: {target.transport}")
