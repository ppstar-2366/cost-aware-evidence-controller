from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "caec-matplotlib-cache")
)
os.environ.setdefault(
    "XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "caec-xdg-cache")
)

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


BLUE = "#0072B2"
VERMILLION = "#D55E00"
GREEN = "#009E73"
PURPLE = "#CC79A7"
BLACK = "#000000"
GREY = "#666666"
LIGHT_GREY = "#D9D9D9"

METHOD_LABELS = {
    "ControllerV3": "ControllerV3",
    "ControllerV3_no_section": "No section expansion",
    "BM25_top7": "BM25 top-7",
    "BM25_top8": "BM25 top-8",
    "GenericCountMatched": "Generic count-matched",
    "GenericTokenMatched": "Generic token-matched",
    "AbstractOnly": "Abstract only",
    "ReadAll": "Read all",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create provisional publication-ready thesis result figures."
    )
    parser.add_argument("--output-dir", default="outputs/figures")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def float_value(row: dict[str, str], key: str) -> float:
    return float(row[key])


def indexed_ci(
    rows: list[dict[str, str]], threshold: float = 0.5
) -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row["method"], row["metric"]): row
        for row in rows
        if abs(float(row.get("threshold", threshold)) - threshold) < 1e-9
    }


def matched_row(
    rows: list[dict[str, str]],
    first: str,
    second: str,
    metric: str,
    threshold: float | None = None,
) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row["first_method"] == first
        and row["second_method"] == second
        and row["metric"] == metric
        and (
            threshold is None
            or abs(float(row.get("threshold", threshold)) - threshold) < 1e-9
        )
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one row for {first} - {second}, {metric}; found {len(matches)}"
        )
    return matches[0]


def style() -> dict[str, Any]:
    return {
        "font.family": "DejaVu Sans",
        "font.size": 8.5,
        "axes.titlesize": 9.5,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7.5,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.4,
        "lines.markersize": 5.5,
        "grid.color": "#E6E6E6",
        "grid.linewidth": 0.6,
        "grid.alpha": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "figure.facecolor": "white",
    }


def export(
    fig: mpl.figure.Figure,
    output_dir: Path,
    stem: str,
    overwrite: bool,
) -> list[Path]:
    paths = [output_dir / f"{stem}.pdf", output_dir / f"{stem}.png"]
    if not overwrite:
        existing = [str(path) for path in paths if path.exists()]
        if existing:
            raise FileExistsError(
                f"Refusing to overwrite existing figure(s): {existing}. Use --overwrite."
            )
    fig.savefig(paths[0], format="pdf", dpi=400, metadata={"Creator": "make_thesis_figures.py"})
    fig.savefig(paths[1], format="png", dpi=400, pil_kwargs={"compress_level": 6})
    with Image.open(paths[1]) as png:
        if png.mode != "RGB":
            png.convert("RGB").save(paths[1], dpi=(400, 400), compress_level=6)
    plt.close(fig)
    return paths


def retrieval_quality_cost(output_dir: Path, overwrite: bool) -> dict[str, Any]:
    summary_path = Path("outputs/test416/test416_method_comparison_threshold05.csv")
    ci_path = Path("outputs/test416/test416_bootstrap_method_cis.csv")
    supplementary_path = Path(
        "outputs/supplementary/test416_supplementary_retrieval_summary.csv"
    )
    supplementary_ci_path = Path(
        "outputs/supplementary/test416_supplementary_bootstrap_method_cis.csv"
    )
    summary = {row["method"]: row for row in read_csv(summary_path)}
    ci = indexed_ci(read_csv(ci_path))
    supplementary = {row["method"]: row for row in read_csv(supplementary_path)}
    supplementary_ci = indexed_ci(read_csv(supplementary_ci_path))

    with mpl.rc_context(style()):
        fig, ax = plt.subplots(
            figsize=(160 / 25.4, 96 / 25.4), layout="constrained"
        )
        bm25_names = [
            "BM25_top1",
            "BM25_top3",
            "BM25_top5",
            "BM25_top7",
            "BM25_top8",
            "BM25_top10",
            "BM25_top20",
        ]
        x = [float_value(ci[(name, "avg_estimated_tokens")], "point_estimate") for name in bm25_names]
        y = [float_value(ci[(name, "evidence_recall")], "point_estimate") for name in bm25_names]
        ax.plot(x, y, color=BLUE, marker="o", linestyle="-", label="BM25 fixed top-k")
        for name, x_value, y_value in zip(bm25_names, x, y):
            token_ci = ci[(name, "avg_estimated_tokens")]
            recall_ci = ci[(name, "evidence_recall")]
            ax.errorbar(
                x_value,
                y_value,
                xerr=[
                    [x_value - float_value(token_ci, "ci_lower")],
                    [float_value(token_ci, "ci_upper") - x_value],
                ],
                yerr=[
                    [y_value - float_value(recall_ci, "ci_lower")],
                    [float_value(recall_ci, "ci_upper") - y_value],
                ],
                color=BLUE,
                linewidth=0.8,
                capsize=1.8,
                alpha=0.8,
            )
            ax.annotate(
                name.replace("BM25_top", "k="),
                (x_value, y_value),
                xytext=(4, -8 if name in {"BM25_top7", "BM25_top8"} else 4),
                textcoords="offset points",
                color=BLUE,
                fontsize=7,
            )

        special = [
            ("ControllerV3", VERMILLION, "s", ci),
            ("ControllerV3_no_section", GREEN, "D", ci),
            ("GenericCountMatched", PURPLE, "^", supplementary_ci),
        ]
        for name, color, marker, source_ci in special:
            token_ci = source_ci[(name, "avg_estimated_tokens")]
            recall_ci = source_ci[(name, "evidence_recall")]
            x_value = float_value(token_ci, "point_estimate")
            y_value = float_value(recall_ci, "point_estimate")
            ax.errorbar(
                x_value,
                y_value,
                xerr=[
                    [x_value - float_value(token_ci, "ci_lower")],
                    [float_value(token_ci, "ci_upper") - x_value],
                ],
                yerr=[
                    [y_value - float_value(recall_ci, "ci_lower")],
                    [float_value(recall_ci, "ci_upper") - y_value],
                ],
                color=color,
                marker=marker,
                linestyle="none",
                markeredgecolor=BLACK,
                markeredgewidth=0.5,
                capsize=2,
                label=METHOD_LABELS[name],
            )

        for name, marker in (("AbstractOnly", "v"), ("ReadAll", "X")):
            row = supplementary[name]
            ax.scatter(
                float(row["avg_estimated_tokens"]),
                float(row["evidence_recall"]),
                marker=marker,
                facecolors="white",
                edgecolors=GREY,
                linewidths=1.0,
                label=METHOD_LABELS[name],
                zorder=3,
            )

        ax.set(
            xlabel="Average estimated input tokens (words × 1.3)",
            ylabel="Evidence Recall at overlap ≥ 0.5",
            xlim=(0, 5500),
            ylim=(0, 1.04),
            title="Held-out retrieval quality–cost trade-off",
        )
        ax.grid(True, axis="both")
        ax.legend(loc="lower right", frameon=False, ncol=2)
        ax.text(
            0.01,
            0.99,
            "Points: 416 papers; bars: 95% paper-cluster bootstrap CI",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.2,
            color=GREY,
        )
        paths = export(fig, output_dir, "fig_retrieval_quality_cost", overwrite)

    return {
        "stem": "fig_retrieval_quality_cost",
        "files": [str(path) for path in paths],
        "source_data": [str(summary_path), str(ci_path), str(supplementary_path), str(supplementary_ci_path)],
        "transformations": "Direct plotting of reported point estimates and 95% paper-cluster bootstrap intervals; no smoothing.",
        "alt_text": "Scatter-line plot of Evidence Recall against estimated tokens. BM25 recall rises with k and cost. ControllerV3 lies almost on BM25 top-7; the budget-matched generic control is adjacent. Read-all has near-complete recall at much higher cost.",
    }


def paired_retrieval_effects(output_dir: Path, overwrite: bool) -> dict[str, Any]:
    primary_path = Path("outputs/test416/test416_bootstrap_paired_differences.csv")
    supplementary_path = Path(
        "outputs/supplementary/test416_supplementary_bootstrap_paired_differences.csv"
    )
    primary = read_csv(primary_path)
    supplementary = read_csv(supplementary_path)
    contrasts = [
        ("ControllerV3", "BM25_top7", "Controller − BM25 top-7", primary, VERMILLION, "s"),
        ("ControllerV3", "GenericCountMatched", "Controller − generic count", supplementary, PURPLE, "^"),
        ("ControllerV3", "ControllerV3_no_section", "Full − no section", primary, GREEN, "D"),
    ]
    metrics = [("evidence_recall", "Evidence Recall"), ("question_hit_rate", "Question Hit Rate")]

    with mpl.rc_context(style()):
        fig, (quality_ax, cost_ax) = plt.subplots(
            2,
            1,
            figsize=(160 / 25.4, 132 / 25.4),
            layout="constrained",
            gridspec_kw={"height_ratios": [1.7, 1]},
        )
        y_positions: list[float] = []
        y_labels: list[str] = []
        cursor = 0.0
        for first, second, label, rows, color, marker in contrasts:
            for metric, metric_label in metrics:
                row = matched_row(rows, first, second, metric, threshold=0.5)
                point = 100 * float_value(row, "point_difference")
                lower = 100 * float_value(row, "ci_lower")
                upper = 100 * float_value(row, "ci_upper")
                quality_ax.errorbar(
                    point,
                    cursor,
                    xerr=[[point - lower], [upper - point]],
                    marker=marker,
                    color=color,
                    markeredgecolor=BLACK,
                    markeredgewidth=0.4,
                    linestyle="none",
                    capsize=2,
                )
                y_positions.append(cursor)
                y_labels.append(f"{label}\n{metric_label}")
                cursor += 1.0
            cursor += 0.35
        quality_ax.axvline(0, color=BLACK, linewidth=0.8)
        quality_ax.set_yticks(y_positions, y_labels)
        quality_ax.invert_yaxis()
        quality_ax.set(
            xlabel="Paired difference (percentage points)",
            title="a  Retrieval-quality contrasts",
        )
        quality_ax.grid(True, axis="x")

        cost_positions: list[float] = []
        cost_labels: list[str] = []
        for index, (first, second, label, rows, color, marker) in enumerate(contrasts):
            row = matched_row(rows, first, second, "avg_estimated_tokens", threshold=0.5)
            point = float_value(row, "point_difference")
            lower = float_value(row, "ci_lower")
            upper = float_value(row, "ci_upper")
            cost_ax.errorbar(
                point,
                index,
                xerr=[[point - lower], [upper - point]],
                marker=marker,
                color=color,
                markeredgecolor=BLACK,
                markeredgewidth=0.4,
                linestyle="none",
                capsize=2,
            )
            cost_positions.append(index)
            cost_labels.append(label)
        cost_ax.axvline(0, color=BLACK, linewidth=0.8)
        cost_ax.set_yticks(cost_positions, cost_labels)
        cost_ax.invert_yaxis()
        cost_ax.set(
            xlabel="Paired difference (estimated tokens)",
            title="b  Retrieval-cost contrasts",
        )
        cost_ax.grid(True, axis="x")
        fig.suptitle("Controller contrasts with 95% paired paper-cluster bootstrap intervals")
        paths = export(fig, output_dir, "fig_paired_retrieval_effects", overwrite)

    return {
        "stem": "fig_paired_retrieval_effects",
        "files": [str(path) for path in paths],
        "source_data": [str(primary_path), str(supplementary_path)],
        "transformations": "Recall and hit-rate differences multiplied by 100 to percentage points; token differences unchanged.",
        "alt_text": "Two forest plots. ControllerV3 minus BM25 top-7 and budget-matched generic controls have small retrieval-quality intervals crossing zero. Full ControllerV3 minus no-section has positive retrieval intervals and roughly 104 additional estimated tokens.",
    }


def controller_budget_distribution(output_dir: Path, overwrite: bool) -> dict[str, Any]:
    source_path = Path(
        "outputs/supplementary/test416_controller_behavior_paired_budget.csv"
    )
    rows = read_csv(source_path)
    differences = np.array([float(row["token_difference"]) for row in rows])
    relations = Counter(row["controller_budget_relation"] for row in rows)
    mean_value = float(np.mean(differences))
    median_value = float(np.median(differences))

    with mpl.rc_context(style()):
        fig, ax = plt.subplots(
            figsize=(160 / 25.4, 88 / 25.4), layout="constrained"
        )
        bins = np.linspace(-1150, 1100, 37)
        ax.hist(
            differences,
            bins=bins,
            color=BLUE,
            edgecolor="white",
            linewidth=0.5,
        )
        ax.axvline(0, color=BLACK, linewidth=1.0, label="Equal cost")
        ax.axvline(mean_value, color=VERMILLION, linestyle="--", label=f"Mean = {mean_value:.1f}")
        ax.axvline(median_value, color=GREEN, linestyle=":", label=f"Median = {median_value:.1f}")
        total = len(rows)
        relation_text = (
            f"Lower: {relations['lower'] / total:.1%}   "
            f"Equal: {relations['equal'] / total:.1%}   "
            f"Higher: {relations['higher'] / total:.1%}"
        )
        ax.text(
            0.5,
            0.97,
            relation_text,
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=8,
        )
        ax.set(
            xlabel="ControllerV3 − BM25 top-7 estimated tokens per question",
            ylabel="Questions",
            xlim=(-1150, 1100),
            title="Question-level redistribution of the evidence budget",
        )
        ax.grid(True, axis="y")
        ax.legend(frameon=False, loc="upper right")
        paths = export(fig, output_dir, "fig_controller_budget_distribution", overwrite)

    return {
        "stem": "fig_controller_budget_distribution",
        "files": [str(path) for path in paths],
        "source_data": [str(source_path)],
        "transformations": "Fixed 62.5-token-width bins across the observed range; no smoothing. Equal/lower/higher categories copied from the audited per-question table.",
        "alt_text": "Histogram of ControllerV3 minus BM25 top-7 estimated tokens across 1,451 questions. The median is zero and mean is about eight tokens, but the distribution is wide, showing substantial question-level budget redistribution.",
    }


def generation_results(output_dir: Path, overwrite: bool) -> dict[str, Any] | None:
    summary_path = Path(
        "outputs/supplementary/generation/test_generation_answer_summary.csv"
    )
    method_ci_path = Path(
        "outputs/supplementary/generation/test_generation_answer_bootstrap_method_cis.csv"
    )
    paired_path = Path(
        "outputs/supplementary/generation/test_generation_answer_bootstrap_paired.csv"
    )
    if not (summary_path.exists() and method_ci_path.exists() and paired_path.exists()):
        return None
    method_ci_rows = read_csv(method_ci_path)
    paired_rows = read_csv(paired_path)
    methods = ["BM25_top7", "BM25_top8", "ControllerV3", "ControllerV3_no_section"]
    colors = [BLUE, GREY, VERMILLION, GREEN]
    markers = ["o", "X", "s", "D"]
    ci_index = {(row["method"], row["metric"]): row for row in method_ci_rows}

    with mpl.rc_context(style()):
        fig, axes = plt.subplots(
            3,
            1,
            figsize=(160 / 25.4, 150 / 25.4),
            layout="constrained",
            gridspec_kw={"height_ratios": [1.25, 1, 1.25]},
        )
        positions = np.arange(len(methods))
        for position, method, color, marker in zip(positions, methods, colors, markers):
            row = ci_index[(method, "f1")]
            point = float_value(row, "point_estimate")
            lower = float_value(row, "ci_lower")
            upper = float_value(row, "ci_upper")
            axes[0].errorbar(
                point,
                position,
                xerr=[[point - lower], [upper - point]],
                marker=marker,
                color=color,
                markeredgecolor=BLACK,
                markeredgewidth=0.4,
                linestyle="none",
                capsize=2,
            )
        axes[0].set_yticks(positions, [METHOD_LABELS[method] for method in methods])
        axes[0].invert_yaxis()
        axes[0].set(xlabel="Answer F1", title="a  Method estimates", xlim=(0, None))
        axes[0].grid(True, axis="x")

        contrast_labels: list[str] = []
        for index, second in enumerate(("BM25_top7", "BM25_top8", "ControllerV3_no_section")):
            row = matched_row(paired_rows, "ControllerV3", second, "f1")
            point = float_value(row, "point_difference")
            lower = float_value(row, "ci_lower")
            upper = float_value(row, "ci_upper")
            axes[1].errorbar(
                point,
                index,
                xerr=[[point - lower], [upper - point]],
                marker="s",
                color=VERMILLION,
                markeredgecolor=BLACK,
                markeredgewidth=0.4,
                linestyle="none",
                capsize=2,
            )
            contrast_labels.append(f"Controller −\n{METHOD_LABELS[second]}")
        axes[1].axvline(0, color=BLACK, linewidth=0.8)
        axes[1].set_yticks(range(3), contrast_labels)
        axes[1].invert_yaxis()
        axes[1].set(xlabel="Paired Answer F1 difference", title="b  Paired contrasts")
        axes[1].grid(True, axis="x")

        for position, method, color, marker in zip(positions, methods, colors, markers):
            row = ci_index[(method, "prompt_tokens")]
            point = float_value(row, "point_estimate")
            lower = float_value(row, "ci_lower")
            upper = float_value(row, "ci_upper")
            axes[2].errorbar(
                point,
                position,
                xerr=[[point - lower], [upper - point]],
                marker=marker,
                color=color,
                markeredgecolor=BLACK,
                markeredgewidth=0.4,
                linestyle="none",
                capsize=2,
            )
        axes[2].set_yticks(positions, [METHOD_LABELS[method] for method in methods])
        axes[2].invert_yaxis()
        axes[2].set(
            xlabel="Actual prompt tokens",
            title="c  Model input cost",
            xlim=(0, None),
        )
        axes[2].grid(True, axis="x")
        fig.suptitle("Frozen test-sample answer generation (53 papers, 201 questions)")
        paths = export(fig, output_dir, "fig_generation_results", overwrite)

    return {
        "stem": "fig_generation_results",
        "files": [str(path) for path in paths],
        "source_data": [str(summary_path), str(method_ci_path), str(paired_path)],
        "transformations": "Direct plotting of method estimates and 95% paper-cluster bootstrap intervals; failed generations, if any, remain in the answer denominator.",
        "alt_text": "Three panels compare frozen test-sample Answer F1, paired ControllerV3 F1 differences, and actual prompt tokens for four retrieval methods. Intervals show paper-cluster bootstrap uncertainty.",
    }


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [
        retrieval_quality_cost(output_dir, args.overwrite),
        paired_retrieval_effects(output_dir, args.overwrite),
        controller_budget_distribution(output_dir, args.overwrite),
    ]
    generation = generation_results(output_dir, args.overwrite)
    if generation is not None:
        records.append(generation)

    all_source_paths = sorted(
        {Path(path) for record in records for path in record["source_data"]}
    )
    manifest = {
        "status": "provisional_general_thesis_figures",
        "destination": "Imperial College Computing MSc thesis; exact template text width pending final LaTeX integration",
        "physical_width_mm": 160,
        "raster_dpi": 400,
        "formats": ["PDF", "PNG"],
        "background": "opaque white",
        "palette": "Okabe-Ito-derived colors with marker/line-style redundancy",
        "uncertainty": "95% percentile paper-cluster bootstrap, 5,000 replicates, seed 42",
        "figures": records,
        "source_sha256": {
            str(path): sha256(path) for path in all_source_paths
        },
        "output_sha256": {
            str(path): sha256(path)
            for record in records
            for path in map(Path, record["files"])
        },
        "matplotlib_version": mpl.__version__,
    }
    manifest_path = output_dir / "figure_manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Refusing to overwrite {manifest_path}; use --overwrite."
        )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created {len(records)} figures in {output_dir}")
    for record in records:
        print(f"- {record['stem']}")
    if generation is None:
        print("- generation figure skipped because final generation summaries are absent")
    print(f"Saved provenance and alt text to {manifest_path}")


if __name__ == "__main__":
    main()
