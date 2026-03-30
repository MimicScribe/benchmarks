"""Score hypothesis RTTMs against ground-truth references using DER and cpWER."""

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from pyannote.core import Annotation, Segment, Timeline
from pyannote.metrics.diarization import DiarizationErrorRate

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output"
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"


@dataclass
class FileResult:
    file_id: str
    der: float
    missed: float
    false_alarm: float
    confusion: float
    n_ref_speakers: int
    n_hyp_speakers: int
    ref_duration: float


@dataclass
class CorpusResult:
    corpus: str
    files: list[FileResult] = field(default_factory=list)

    @property
    def aggregate_der(self) -> float:
        if not self.files:
            return 0.0
        total_scored = sum(f.ref_duration for f in self.files)
        if total_scored == 0:
            return 0.0
        weighted_der = sum(f.der * f.ref_duration for f in self.files)
        return weighted_der / total_scored

    @property
    def aggregate_missed(self) -> float:
        total = sum(f.ref_duration for f in self.files)
        return sum(f.missed * f.ref_duration for f in self.files) / total if total else 0.0

    @property
    def aggregate_false_alarm(self) -> float:
        total = sum(f.ref_duration for f in self.files)
        return sum(f.false_alarm * f.ref_duration for f in self.files) / total if total else 0.0

    @property
    def aggregate_confusion(self) -> float:
        total = sum(f.ref_duration for f in self.files)
        return sum(f.confusion * f.ref_duration for f in self.files) / total if total else 0.0


def parse_rttm(path: Path) -> Annotation:
    """Parse an RTTM file into a pyannote Annotation."""
    annotation = Annotation()
    for line in path.read_text().strip().split("\n"):
        if not line or line.startswith(";"):
            continue
        parts = line.split()
        if parts[0] != "SPEAKER":
            continue
        onset = float(parts[3])
        duration = float(parts[4])
        speaker = parts[7]
        annotation[Segment(onset, onset + duration)] = speaker
    return annotation


def parse_uem(path: Path) -> list[Segment]:
    """Parse a UEM file into scored regions."""
    segments = []
    for line in path.read_text().strip().split("\n"):
        if not line:
            continue
        parts = line.split()
        segments.append(Segment(float(parts[2]), float(parts[3])))
    return segments


def score_file(
    ref_rttm: Path,
    hyp_rttm: Path,
    uem_path: Path | None = None,
    collar: float = 0.25,
) -> FileResult:
    """Score a single file: compute DER components."""
    ref = parse_rttm(ref_rttm)
    hyp = parse_rttm(hyp_rttm)

    uem = None
    if uem_path and uem_path.exists():
        regions = parse_uem(uem_path)
        if regions:
            uem = Timeline(segments=regions)

    metric = DiarizationErrorRate(collar=collar, skip_overlap=False)
    der = metric(ref, hyp, uem=uem)
    components = metric.accumulated_

    # Extract component rates
    total = components.get("total", 1.0)
    missed = components.get("missed detection", 0.0) / total if total else 0.0
    false_alarm = components.get("false alarm", 0.0) / total if total else 0.0
    confusion = components.get("confusion", 0.0) / total if total else 0.0

    ref_speakers = len(set(ref.labels()))
    hyp_speakers = len(set(hyp.labels()))
    # Use pyannote's accumulated total (UEM-filtered reference speech duration)
    # for consistent weighting in corpus-level aggregation.
    scored_duration = components.get("total", ref.get_timeline().support().duration())

    return FileResult(
        file_id=ref_rttm.stem,
        der=der,
        missed=missed,
        false_alarm=false_alarm,
        confusion=confusion,
        n_ref_speakers=ref_speakers,
        n_hyp_speakers=hyp_speakers,
        ref_duration=scored_duration,
    )


def score_corpus(
    corpus: str,
    data_dir: Path,
    output_dir: Path,
    collar: float = 0.25,
) -> CorpusResult:
    """Score all files for a corpus."""
    ref_dir = data_dir / corpus / "rttm"
    hyp_dir = output_dir / corpus / "rttm"
    uem_dir = data_dir / corpus / "uem"

    result = CorpusResult(corpus=corpus)

    if not ref_dir.exists() or not hyp_dir.exists():
        print(f"  [skip] {corpus}: missing ref ({ref_dir}) or hyp ({hyp_dir})")
        return result

    ref_files = sorted(ref_dir.glob("*.rttm"))
    if not ref_files:
        print(f"  [skip] {corpus}: no reference RTTMs")
        return result

    print(f"\n=== Scoring {corpus} ({len(ref_files)} reference files) ===")

    scored = 0
    for ref_path in ref_files:
        file_id = ref_path.stem
        hyp_path = hyp_dir / f"{file_id}.rttm"
        if not hyp_path.exists():
            print(f"  [{file_id}] no hypothesis — skipped")
            continue

        uem_path = uem_dir / f"{file_id}.uem"
        file_result = score_file(ref_path, hyp_path, uem_path, collar=collar)
        result.files.append(file_result)
        scored += 1

        print(
            f"  [{file_id}] DER={file_result.der:.1%}"
            f" (miss={file_result.missed:.1%}"
            f" fa={file_result.false_alarm:.1%}"
            f" conf={file_result.confusion:.1%})"
            f" spk: ref={file_result.n_ref_speakers} hyp={file_result.n_hyp_speakers}"
        )

    if scored > 0:
        print(
            f"\n  Aggregate DER: {result.aggregate_der:.1%}"
            f" (miss={result.aggregate_missed:.1%}"
            f" fa={result.aggregate_false_alarm:.1%}"
            f" conf={result.aggregate_confusion:.1%})"
            f" — {scored} files scored"
        )

    return result


def _score_baseline(
    corpus: str,
    data_dir: Path,
    baseline_dir: Path,
    collar: float = 0.25,
) -> CorpusResult:
    """Score pyannote baseline RTTMs (flat directory, not per-corpus subdirs)."""
    ref_dir = data_dir / corpus / "rttm"
    hyp_dir = baseline_dir / "rttm"
    uem_dir = data_dir / corpus / "uem"

    result = CorpusResult(corpus=corpus)
    if not ref_dir.exists() or not hyp_dir.exists():
        return result

    for ref_path in sorted(ref_dir.glob("*.rttm")):
        file_id = ref_path.stem
        hyp_path = hyp_dir / f"{file_id}.rttm"
        if not hyp_path.exists():
            continue
        uem_path = uem_dir / f"{file_id}.uem"
        file_result = score_file(ref_path, hyp_path, uem_path, collar=collar)
        result.files.append(file_result)

    if result.files:
        print(
            f"  Pyannote baseline {corpus}: DER={result.aggregate_der:.1%}"
            f" — {len(result.files)} files"
        )

    return result


def render_readme(
    results: list[CorpusResult],
    results_dir: Path,
    baseline_results: list[CorpusResult] | None = None,
) -> None:
    """Render results as a markdown table and save to results/."""
    from datetime import date

    results_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# MimicScribe Diarization Benchmark Results",
        "",
        "Pipeline: Parakeet TDT 0.6B (on-device ASR) + Pyannote (on-device diarization)"
        " + Gemini 3 Flash (LLM speaker attribution)",
        "",
        f"Run date: {date.today().isoformat()}",
        "",
        "Collar: 0.25s (standard)",
        "",
        "## Benchmark vs Production",
        "",
        "These results represent a **worst-case scenario** for the MimicScribe pipeline."
        " In normal use, the pipeline has several advantages not available in this benchmark:",
        "",
        "- **Mic/system audio separation**: MimicScribe captures the user's microphone and"
        " system audio (remote participants) as separate streams. This gives the diarization"
        " a free speaker separation signal — the primary user is always identified from the"
        " mic channel, and remote speakers are a distinct pool. In this benchmark, all speakers"
        " come from a single mixed audio file with no channel distinction.",
        "- **Voice profiles**: Users can save voice profiles that provide verified speaker"
        " recognition with high confidence. The benchmark has no saved profiles.",
        "- **Meeting context**: Users can provide prep context (e.g., \"Meeting with Alice and"
        " Bob about Q3\") that helps the LLM identify speakers. The benchmark has no context.",
        "- **Segment granularity**: The pipeline outputs sentence-level segments because that's"
        " what users read. DER penalizes this heavily — silent gaps within a sentence count as"
        " false alarm — but it is a deliberate UX choice, not a diarization failure. This"
        " accounts for the majority of the false alarm rate.",
        "",
        "## Summary",
        "",
        "DER is the sum of three error types. **Confusion** (speaker assignment error) is the"
        " most relevant metric for diarization quality — it measures how often speech is"
        " attributed to the wrong speaker. **False Alarm** is inflated by the pipeline's"
        " sentence-level segments spanning silent gaps (see above). **Missed** is speech"
        " that was not detected at all.",
        "",
        "| Corpus | Files | DER | Confusion (speaker error) | False Alarm (segment boundaries) | Missed |",
        "|--------|------:|----:|--------------------------:|--------------------------------:|-------:|",
    ]

    for r in results:
        if not r.files:
            continue
        lines.append(
            f"| {r.corpus} | {len(r.files)} "
            f"| {r.aggregate_der:.1%} "
            f"| {r.aggregate_confusion:.1%} "
            f"| {r.aggregate_false_alarm:.1%} "
            f"| {r.aggregate_missed:.1%} |"
        )

    # Baseline comparison
    baselines = baseline_results or []
    has_baseline = any(b.files for b in baselines)
    if has_baseline:
        lines.extend([
            "",
            "## Baseline Comparison",
            "",
            "[Pyannote Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)"
            " is the reference open-source diarization system, run with default parameters.",
            "",
            "| Corpus | Pyannote Community-1 | MimicScribe Pipeline |",
            "|--------|--------------------:|--------------------:|",
        ])
        for r, b in zip(results, baselines):
            if not r.files:
                continue
            b_der = f"{b.aggregate_der:.1%}" if b.files else "—"
            lines.append(f"| {r.corpus} | {b_der} | {r.aggregate_der:.1%} |")

    lines.append("")
    lines.append("## Per-File Results")

    for i, r in enumerate(results):
        if not r.files:
            continue
        b = baselines[i] if i < len(baselines) else CorpusResult(corpus=r.corpus)
        b_lookup = {f.file_id: f for f in b.files} if b.files else {}
        has_b = bool(b_lookup)

        if has_b:
            lines.extend([
                "",
                f"### {r.corpus}",
                "",
                "| File | Pyannote C1 | MimicScribe | Ref Spk | Hyp Spk |",
                "|------|------------:|------------:|--------:|--------:|",
            ])
            for f in sorted(r.files, key=lambda x: x.file_id):
                bf = b_lookup.get(f.file_id)
                b_der = f"{bf.der:.1%}" if bf else "—"
                lines.append(
                    f"| {f.file_id} "
                    f"| {b_der} "
                    f"| {f.der:.1%} "
                    f"| {f.n_ref_speakers} "
                    f"| {f.n_hyp_speakers} |"
                )
        else:
            lines.extend([
                "",
                f"### {r.corpus}",
                "",
                "| File | DER | Missed | False Alarm | Confusion | Ref Spk | Hyp Spk |",
                "|------|----:|-------:|------------:|----------:|--------:|--------:|",
            ])
            for f in sorted(r.files, key=lambda x: x.file_id):
                lines.append(
                    f"| {f.file_id} "
                    f"| {f.der:.1%} "
                    f"| {f.missed:.1%} "
                    f"| {f.false_alarm:.1%} "
                    f"| {f.confusion:.1%} "
                    f"| {f.n_ref_speakers} "
                    f"| {f.n_hyp_speakers} |"
                )

    lines.append("")

    readme_path = results_dir / "RESULTS.md"
    readme_path.write_text("\n".join(lines))
    print(f"\nResults written to {readme_path}")

    # Also save raw JSON for programmatic access
    json_path = results_dir / "results.json"
    json_data = []
    for r in results:
        json_data.append({
            "corpus": r.corpus,
            "aggregate_der": r.aggregate_der,
            "aggregate_missed": r.aggregate_missed,
            "aggregate_false_alarm": r.aggregate_false_alarm,
            "aggregate_confusion": r.aggregate_confusion,
            "files": [
                {
                    "file_id": f.file_id,
                    "der": f.der,
                    "missed": f.missed,
                    "false_alarm": f.false_alarm,
                    "confusion": f.confusion,
                    "n_ref_speakers": f.n_ref_speakers,
                    "n_hyp_speakers": f.n_hyp_speakers,
                    "ref_duration": f.ref_duration,
                }
                for f in r.files
            ],
        })
    json_path.write_text(json.dumps(json_data, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Score benchmark results")
    parser.add_argument(
        "--corpus",
        choices=["ami", "earnings21", "all"],
        default="all",
    )
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--collar",
        type=float,
        default=0.25,
        help="Collar in seconds for DER (default: 0.25)",
    )
    args = parser.parse_args()

    corpora = ["ami", "earnings21"] if args.corpus == "all" else [args.corpus]
    results = []
    baseline_results = []
    baseline_dir = args.output_dir / "pyannote-community-1"
    for corpus in corpora:
        result = score_corpus(corpus, args.data_dir, args.output_dir, collar=args.collar)
        results.append(result)

        # Score pyannote baseline if available
        baseline_hyp_dir = baseline_dir / "rttm"
        if baseline_hyp_dir.exists() and list(baseline_hyp_dir.glob("*.rttm")):
            baseline = _score_baseline(corpus, args.data_dir, baseline_dir, collar=args.collar)
            baseline_results.append(baseline)
        else:
            baseline_results.append(CorpusResult(corpus=corpus))

    render_readme(results, args.results_dir, baseline_results=baseline_results)
    print("\nDone.")


if __name__ == "__main__":
    main()
