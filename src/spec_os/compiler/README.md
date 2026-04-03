# Shadow Compiler

This package is experimental and must not replace the importer path yet.

Rules:
- importer remains the stable path
- compiler writes only to temp/shadow outputs
- parity against the checked-in RC artifact pack is the first milestone
- no artifact overwrite of the source repo by default

Current entrypoint:

```bash
python -m spec_os.cli \
  --specos-repo /path/to/Modelling_Engine_SpecOS \
  --specos-repo-mode compiler \
  --data-dir /path/to/output
```

Current behavior:
- this mode is opt-in; `--specos-repo-mode importer` remains the default
- the compiler path returns `status: "compiled"`
- the compiler path returns `import_mode: "modelling_engine_specos_compiler"`
- the compiler path also includes `compiler_mode: "shadow_phase_spec_compiler"` in the CLI summary
- cutover has not happened; this mode exists for side-by-side validation
