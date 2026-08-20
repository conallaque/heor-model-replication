"""
No genomic data in this repository — asserted, not assumed
==========================================================

This project is health *economics*. It shares an author with a genomics tool, and
that tool reads real personal genome files, so the possibility of one drifting
into the wrong repository is not hypothetical — it is the sort of thing that
happens once, silently, and cannot be undone after a push.

A `.gitignore` is the wrong place to rely on for this. It fails quietly: a file
that slips past it is committed with no complaint, and a file it catches is
invisible rather than reported. So the guarantee is a test instead. It fails
loudly, it runs in CI on every push, and it scans what is actually tracked rather
than what someone intended to track.

The signatures below detect *data*, not discussion, and none of them is a personal identifier: naming
a real sample ID in a file that may go public would itself be a small leak, and
the extension rules in `.gitignore` plus these content checks catch a raw export
whatever it is called. Prose that mentions genomics —
this docstring, the README's reference to the sibling project, a strategy named
``genomic_guided`` — must not trip them, or the test would be noise and end up
disabled. Each pattern therefore matches the shape of a genotype record, not the
vocabulary of the field.

If this test ever fails, treat it as an incident: the offending file must be
removed from history, not just from the tree, and any push already made must be
assumed public.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: Each entry is (label, compiled pattern). Patterns target the structure of
#: genomic records so that writing *about* genomics stays safe.
SIGNATURES = [
    # A dbSNP reference-SNP id. Bare "rs" plus 3+ digits does not occur in prose.
    ("dbSNP rsID", re.compile(r"\brs\d{3,}\b")),
    # VCF: either the mandatory version line or the column header row.
    ("VCF header", re.compile(r"##fileformat=VCF|^#CHROM\t", re.M)),
    # The header of a 23andMe / AncestryDNA / TellMeGen raw export.
    ("consumer genotype export header",
     re.compile(r"rsid\W+chromosome\W+position\W+genotype", re.I)),
    # A genotype call row: rsID, chromosome, position, then a 1-2 base call.
    ("genotype call row",
     re.compile(r"^\s*rs\d+[\t,]\w+[\t,]\d+[\t,][ACGT\-]{1,2}\s*$", re.M)),
    # Long uninterrupted base runs — FASTA/FASTQ sequence, not English.
    ("raw sequence run (40+ bases)", re.compile(r"\b[ACGTN]{40,}\b")),
]

#: Extensions that should never appear, whatever their contents.
FORBIDDEN_SUFFIXES = {
    ".vcf", ".gvcf", ".bam", ".bai", ".cram", ".fastq", ".fq",
    ".23andme", ".ped", ".bed", ".bim", ".fam",
}

#: The only data files this project legitimately tracks. Anything else with a
#: tabular extension is a finding, not an exception to be added here lightly.
ALLOWED_DATA_FILES = {"data/LifeTable_USA_Mx_2015.csv"}

#: The one file whose job is to *name* these patterns, and which therefore
#: contains them by necessity. Exempting anything else would hollow out the
#: check, so the list is pinned by ``test_self_exemption_has_not_grown`` below.
SELF_EXEMPT = {"tests/test_no_genomic_data.py"}


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.split("\n") if line]


def _read(path: str) -> str:
    try:
        return (REPO / path).read_text(encoding="utf-8")
    except (UnicodeDecodeError, FileNotFoundError):
        return ""


@pytest.fixture(scope="module")
def tracked():
    files = _tracked_files()
    assert files, "git ls-files returned nothing — is this a git repository?"
    return files


@pytest.mark.parametrize("label,pattern", SIGNATURES,
                         ids=[s[0] for s in SIGNATURES])
def test_no_genomic_signature_in_tracked_files(tracked, label, pattern):
    """No tracked file contains anything shaped like a genotype record."""
    offenders = [f for f in tracked
                 if f not in SELF_EXEMPT and pattern.search(_read(f))]
    assert not offenders, (
        f"{label} found in tracked file(s): {offenders}. "
        f"Remove from git history, not just the working tree.")


def test_self_exemption_has_not_grown():
    """Only this file may be exempt from the content scan.

    Without this, the natural fix for a future failure is to add the offending
    file to ``SELF_EXEMPT`` and move on — which would turn the check into
    decoration. Widening the exemption now has to be a deliberate, reviewed edit
    to two places rather than one.
    """
    assert SELF_EXEMPT == {"tests/test_no_genomic_data.py"}, (
        "SELF_EXEMPT changed. Exempting a file from the genomic-data scan is not "
        "a fix for that scan failing — remove the data instead.")


def test_no_genomic_file_formats_are_tracked(tracked):
    offenders = [f for f in tracked if Path(f).suffix.lower() in FORBIDDEN_SUFFIXES]
    assert not offenders, f"genomic file format(s) tracked: {offenders}"


def test_only_expected_tabular_data_files_are_tracked(tracked):
    """Raw genotype exports are plain .csv/.tsv/.txt, so every tracked file with
    one of those extensions has to be on the allow-list by name."""
    tabular = {f for f in tracked
               if Path(f).suffix.lower() in {".csv", ".tsv"}}
    unexpected = tabular - ALLOWED_DATA_FILES
    assert not unexpected, (
        f"unexpected tabular data file(s): {sorted(unexpected)}. If legitimate, "
        f"add to ALLOWED_DATA_FILES with a note in data/PROVENANCE.md.")


def test_the_one_data_file_is_a_population_life_table():
    """Positive check on the allowed file: aggregate rates by year/age/sex, with
    no per-person column. Confirms what it is, rather than only what it isn't."""
    import csv

    with (REPO / "data/LifeTable_USA_Mx_2015.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert set(rows[0]) == {"Year", "Age", "Female", "Male", "Total"}
    assert all(0.0 < float(r["Total"]) <= 1.0 for r in rows), "not rates"
    assert len({r["Year"] for r in rows}) == 1, "single-year table expected"


def test_gitignore_still_guards_against_genomic_data():
    """The belt to the test's braces. If someone trims .gitignore, say so here
    rather than discovering it when a genome file stages cleanly."""
    ignored = (REPO / ".gitignore").read_text()
    for rule in ("*.vcf", "*.fastq", "*.csv", "*.tsv", "*.txt"):
        assert rule in ignored, f".gitignore no longer contains {rule!r}"
    # ...and the whitelist that keeps the legitimate files tracked.
    for allow in ("!requirements.txt", "!data/LifeTable_USA_Mx_2015.csv"):
        assert allow in ignored, f".gitignore no longer whitelists {allow!r}"
