# TensorFence Plugin Protocol v1

TensorFence is a host. Model-specific and vendor-specific behavior is provided by
plugins. A plugin is discovered from a built-in package, the user configuration
directory, or `<project>/.tensorfence/plugins/`.

First-party plugins may use `runtime: builtin-python` and register an
`ExecutionContext` handler with the host. Third-party plugins normally use the
default `runtime: external-json` and can be implemented in any language.
Hosts expose `start()`, `stop()`, and `dispose()` lifecycle hooks so a future
plugin can own a device session or other resources without changing the CLI.

## Manifest

```yaml
schema_version: 1
id: acme.example
name: Example diagnostics
version: 1.0.0
capabilities: [probe]
profiles: [generic-linux]
default_enabled: true
actions:
  - id: inspect
    description: Inspect an input
    command: ["python", "plugin.py", "{input:model}"]
    input_schema:
      model: {type: string, required: true}
    output_kind: artifact
    read_only: true
```

Action placeholders are `{python}` and `{input:<name>}`. The host validates
required inputs, target profile support, plugin enablement, and side-effect
confirmation before starting a process.

## Process I/O

The host writes one JSON request to stdin:

```json
{"target":"local","plugin":"acme.example","action":"inspect","inputs":{"model":"model.onnx"}}
```

The plugin may write a JSON object to stdout. The host preserves it in the
`result` field and always returns a stable envelope containing `status`, target,
plugin/action metadata, `facts`, `artifacts`, `recommendations`, and provenance.
Plain stdout is retained as text for legacy tools.

## Enablement

Plugin state is layered as CLI override, project `.tensorfence/plugins.yaml`,
global user `plugins.yaml`, then manifest `default_enabled`. Use:

```text
tensorfence plugins set tensorfence.rknn --disable
tensorfence plugins set tensorfence.rknn --enable --project-root .
```

The host never stores credentials in plugin manifests. Installation, conversion,
firmware updates, and other side effects must be declared and explicitly
authorized with `--allow-side-effects`.
