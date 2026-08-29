from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


TransportKind = Literal["local", "wsl", "ssh"]
PluginRuntime = Literal["external-json", "builtin-python"]
ProfileKind = Literal["default", "offline-analysis", "onnx-host", "rknn-host", "rk3588-board", "generic-linux"]
FactStatus = Literal["ready", "warning", "blocked", "unknown"]


class TargetConnection(StrictModel):
    """Only connection references live here; secrets remain in SSH/OS credential stores."""

    wsl_distro: str | None = None
    host: str | None = None
    user: str | None = None
    port: int = Field(default=22, ge=1, le=65535)
    identity_file: str | None = None
    python: str | None = None
    conda_path: str | None = None
    conda_env: str | None = None


class VersionPolicy(StrictModel):
    python: str | None = None
    rknn_toolkit: str | None = None
    rknn_runtime: str | None = None


class TargetProfile(StrictModel):
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    profile: ProfileKind = "generic-linux"
    transport: TransportKind = "local"
    connection: TargetConnection = Field(default_factory=TargetConnection)
    plugin_ids: list[str] = Field(default_factory=list)
    version_policy: VersionPolicy = Field(default_factory=VersionPolicy)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_connection(self) -> "TargetProfile":
        if self.transport == "wsl" and not self.connection.wsl_distro:
            raise ValueError("WSL targets require connection.wsl_distro")
        if self.transport == "ssh" and not self.connection.host:
            raise ValueError("SSH targets require connection.host")
        return self


class TargetDocument(StrictModel):
    version: Literal[1] = 1
    targets: list[TargetProfile] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_names(self) -> "TargetDocument":
        names = [target.name for target in self.targets]
        if len(set(names)) != len(names):
            raise ValueError("target names must be unique")
        return self


class Fact(StrictModel):
    key: str
    status: FactStatus
    value: str | None = None
    evidence: str | None = None
    recommendation: str | None = None


class EnvironmentFacts(StrictModel):
    schema_version: Literal["tensorfence.environment-facts/v1"] = "tensorfence.environment-facts/v1"
    target: TargetProfile
    facts: list[Fact] = Field(default_factory=list)

    def overall_status(self) -> FactStatus:
        statuses = {fact.status for fact in self.facts}
        if "blocked" in statuses:
            return "blocked"
        if "warning" in statuses:
            return "warning"
        if "unknown" in statuses:
            return "unknown"
        return "ready"


class PluginAction(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    description: str
    command: list[str] = Field(default_factory=list)
    read_only: bool = True
    input_schema: dict[str, object] = Field(default_factory=dict)
    output_kind: str = "text"
    profiles: list[ProfileKind] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)


class PluginManifest(StrictModel):
    schema_version: Literal[1] = 1
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    name: str
    version: str
    profiles: list[ProfileKind] = Field(default_factory=list)
    actions: list[PluginAction] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    default_enabled: bool = True
    runtime: PluginRuntime = "external-json"
    entrypoint: str | None = None
    requires: list[str] = Field(default_factory=list)
    provides: list[str] = Field(default_factory=list)
    config: dict[str, object] = Field(default_factory=dict)
    installed: bool = True
    enabled: bool | None = None
