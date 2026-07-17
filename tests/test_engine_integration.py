"""
End-to-end tests: run the real engine binaries (through the actual sheval CLI,
exactly as `sheval test` does) against test_suites/recursive_shapes fixtures
and check the resulting error_type. These are what test_error_classification.py's
canned-stderr tests are trying to approximate; keeping both means a change to
an engine's actual output is caught here even if the unit tests still pass.

Each test is skipped if its engine's binary isn't available in this checkout,
so the suite still runs (minus those cases) on a machine without every engine
installed.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

_BINARIES = {
    "rudof": REPO_ROOT / "binaries/rudof/rudof",
    "jena_shacl": REPO_ROOT / "binaries/apache-jena-5.3.0/bin/shacl",
    "jena_shex": REPO_ROOT / "binaries/apache-jena-5.3.0/bin/shex",
    "shacl_s": REPO_ROOT / "binaries/shacl_s-0.1.87/bin/shacl_s",
    "shacl_tq": REPO_ROOT / "binaries/shacl-1.4.4/bin/shaclvalidate.sh",
    "shex_s": REPO_ROOT / "binaries/shexs-0.2.34/bin/shexs",
}

_PYSHACL_AVAILABLE = shutil.which("pyshacl") is not None


def _requires(technology):
    binary = _BINARIES[technology]
    return pytest.mark.skipif(not binary.exists(), reason=f"{binary} not present in this checkout")


def run_sheval(tmp_path, technology, engine, test_name):
    """Run `sheval test` for a single technology/test through the real CLI and
    return the stored result dict for that test."""
    results_dir = tmp_path / "results"
    temp_dir = tmp_path / "temp"
    results_dir.mkdir()
    temp_dir.mkdir()

    manifest_src = REPO_ROOT / "test_suites/recursive_shapes/manifest.yaml"
    manifest = yaml.safe_load(manifest_src.read_text())
    manifest["results_folder"] = str(results_dir)
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.dump(manifest))

    output = tmp_path / "out"
    subprocess.run(
        [
            sys.executable, "src/sheval.py", "test",
            "-s", "recursive_shapes",
            "-m", str(manifest_path),
            "--temp", str(temp_dir),
            "-t", technology,
            "-e", engine,
            "-n", test_name,
            "-f", "yaml",
            "-o", str(output),
            "-l", "warning",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    entries = yaml.safe_load((tmp_path / "out.yaml").read_text())
    assert len(entries) == 1, f"expected exactly one result, got {entries}"
    return entries[0]["result"]


# --- rudof: only engine observed to stop cleanly on detection ----------

@_requires("rudof")
def test_rudof_shacl_cycles_detected(tmp_path):
    result = run_sheval(tmp_path, "rudof", "shacl", "bsep1_shacl")
    assert result["conforms"] is None
    assert result["error_type"] == "CyclesDetected"


@_requires("rudof")
def test_rudof_shacl_non_stratified(tmp_path):
    result = run_sheval(tmp_path, "rudof", "shacl", "nstrat1_shacl")
    assert result["conforms"] is None
    assert result["error_type"] == "NonStratified"


@_requires("rudof")
def test_rudof_shacl_normal_run_is_not_an_error(tmp_path):
    # "fresh" has no recursion at all -- rudof handles it fine.
    result = run_sheval(tmp_path, "rudof", "shacl", "fresh_shacl")
    assert result["conforms"] is True
    assert "error_type" not in result


@_requires("rudof")
def test_rudof_shex_recursion_is_not_an_error(tmp_path):
    # Unlike its SHACL validator, rudof's ShEx validator handles this recursive
    # shape fine (no abort) -- must not be misclassified as an error.
    result = run_sheval(tmp_path, "rudof", "shex", "bsep1_shex")
    assert "error_type" not in result


# --- pyshacl: crashes on positive (non-negated) mutual recursion -------

@pytest.mark.skipif(not _PYSHACL_AVAILABLE, reason="pyshacl not installed in this environment")
def test_pyshacl_cycles_detected_crashed(tmp_path):
    result = run_sheval(tmp_path, "pyshacl", "shacl", "bsep3_shacl")
    assert result["conforms"] is None
    assert result["error_type"] == "CyclesDetectedCrashed"


@pytest.mark.skipif(not _PYSHACL_AVAILABLE, reason="pyshacl not installed in this environment")
def test_pyshacl_simple_recursion_backs_out_without_error(tmp_path):
    # bsep1 is recursive but not the mutually-recursive sh:and shape that
    # crashes pyshacl -- it warns internally and still produces a valid report.
    result = run_sheval(tmp_path, "pyshacl", "shacl", "bsep1_shacl")
    assert result["conforms"] is True
    assert "error_type" not in result


# --- jena_shacl: warns and continues, never observed to crash ----------

@_requires("jena_shacl")
def test_jena_shacl_cycle_warning_is_conformant(tmp_path):
    # jena_shacl never aborts on cycles (unlike rudof) or crashes on them
    # (unlike pyshacl on bsep3) -- it warns on stderr and still produces a
    # full report. bsep1 is a simple recursive shape and that report says
    # conforms=true, so it's flagged CyclesDetectedConformant rather than
    # trusted outright as a plain pass.
    result = run_sheval(tmp_path, "jena_shacl", "shacl", "bsep1_shacl")
    assert result["conforms"] is True
    assert result["error_type"] == "CyclesDetectedConformant"


@_requires("jena_shacl")
def test_jena_shacl_cycle_warning_is_conformant_on_mutual_recursion(tmp_path):
    # Same warn-but-continue behavior on bsep3's mutually-recursive sh:and
    # shapes -- the case that crashes pyshacl instead.
    result = run_sheval(tmp_path, "jena_shacl", "shacl", "bsep3_shacl")
    assert result["conforms"] is True
    assert result["error_type"] == "CyclesDetectedConformant"


# --- shacl_tq: degrades per-constraint, never observed to crash --------

@_requires("shacl_tq")
def test_shacl_tq_unsupported_recursion_is_not_an_error(tmp_path):
    result = run_sheval(tmp_path, "shacl_tq", "shacl", "bsep3_shacl")
    assert result["conforms"] in (True, False)
    assert "error_type" not in result


# --- shacl_s: hangs (no distinctive stderr) instead of crashing --------

@_requires("shacl_s")
def test_shacl_s_hang_is_classified_as_timeout(tmp_path):
    result = run_sheval(tmp_path, "shacl_s", "shacl", "bsep3_shacl")
    assert result["conforms"] is None
    assert result["error_type"] == "Timeout"


# --- jena_shex / shex_s: no crashes observed ----------------------------

@_requires("jena_shex")
def test_jena_shex_normal_run_is_not_an_error(tmp_path):
    result = run_sheval(tmp_path, "jena_shex", "shex", "bsep3_shex")
    assert "error_type" not in result


@_requires("shex_s")
def test_shex_s_normal_run_is_not_an_error(tmp_path):
    result = run_sheval(tmp_path, "shex_s", "shex", "bsep3_shex")
    assert "error_type" not in result
