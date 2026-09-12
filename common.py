"""common.py -- shared config-loading and logging bootstrap for every CLI entry point in
this repo. Imported via sys.path.insert(0, str(ROOT)); import common -- a plain script
import, not a package, so each subproject's independent .venv needs no new dependency.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# --- config loading -------------------------------------------------------------------

def load_config(config, program, layout, root, default_config_file, path=None,
                 derived_from_gx_root=None, derived_from_output_root=None) -> dict:
    """Populate `config` (a script's module-level CONFIG dict) from `path` (default:
    `default_config_file`), per the repo's derive-don't-configure convention.

    Precedence, lowest to highest: `layout` (script-specific fixed paths) < the config
    file's `common:` section < its `<program>:` section. Keys in
    `derived_from_gx_root`/`derived_from_output_root` are filled in via setdefault (so an
    explicit config value always wins) anchored on `gx_root_dir`/`output_root_dir`
    respectively, then resolved to absolute paths exactly like every `layout` key. CLI
    flags beat all of this, in the caller's own __main__.

    `config` is cleared and updated in place (never rebound) so other modules that hold a
    reference to it (e.g. end_to_end.py reading `gen.CONFIG["gx_root_dir"]`) see the update.
    """
    derived_from_gx_root = derived_from_gx_root or {}
    derived_from_output_root = derived_from_output_root or {}
    data = yaml.safe_load(
        Path(path or default_config_file).expanduser().read_text(encoding="utf-8")
    ) or {}
    merged = {k: str(v) for k, v in layout.items()}
    for section in ("common", program):
        merged.update(data.get(section) or {})
    for key in layout:                   # layout keys stay absolute even if overridden relatively
        merged[key] = str((root / Path(str(merged[key])).expanduser()).resolve())
    for key, sub in {**derived_from_gx_root, **derived_from_output_root}.items():
        anchor = "gx_root_dir" if key in derived_from_gx_root else "output_root_dir"
        merged.setdefault(key, str(Path(merged[anchor]) / sub))
        merged[key] = str((root / Path(str(merged[key])).expanduser()).resolve())
    config.clear()
    config.update(merged)
    return config


# --- logging ---------------------------------------------------------------------------

_LOG_FORMAT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_FILENAME_TS_FORMAT = "%Y%m%dT%H%M%S"
_VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")

_configured_program: Optional[str] = None   # idempotency guard: first caller wins


def configure(program, config, cli_log_level=None, suppress_gx=False) -> Path:
    """Configure the root logger once per process; return the log file path.

    `program` is the logger name AND log filename prefix -- pass a name unique per
    distinguishable program.

    `config` must contain config["log_dir"]; may contain config["log_level"].
    Precedence: cli_log_level > config.get("log_level") > "INFO".

    Second and later calls in the same process are no-ops (just a debug line) -- this
    is what lets end_to_end.py be the sole configurator while its stage modules' own
    (guarded, __main__-only) configure() calls never fire.
    """
    global _configured_program

    level_name = (cli_log_level or config.get("log_level") or "INFO").upper()
    if level_name not in _VALID_LEVELS:
        raise ValueError(f"log level must be one of {_VALID_LEVELS}, got {level_name!r}")
    level = getattr(logging, level_name)

    log_dir = Path(config["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(_FILENAME_TS_FORMAT)
    log_file = log_dir / f"{program}_{timestamp}.log"

    if _configured_program is not None:
        logging.getLogger(program).debug(
            "configure() called again for '%s'; already configured for '%s', ignoring.",
            program, _configured_program,
        )
        return log_file

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    if suppress_gx:
        logging.getLogger("great_expectations").setLevel(logging.ERROR)

    _configured_program = program
    logging.getLogger(program).info(
        "Starting %s (log_level=%s, log_file=%s)", program, level_name, log_file,
    )
    return log_file
