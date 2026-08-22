from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .core import fha_response_curve


PASS_COLOR = "#16794b"
REJECT_COLOR = "#b64a3a"
FAILED_COLOR = "#8b5a12"
NEUTRAL_COLOR = "#536273"
GRID_COLOR = "#d8dee6"
TEXT_COLOR = "#17212b"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_workflow_svg(path: Path) -> None:
    nodes = [
        (25, 65, 135, "Specification"),
        (190, 65, 135, "Candidate generation"),
        (355, 65, 105, "FHA gate"),
        (490, 30, 180, "Time-stepped linear\nequivalent evaluation"),
        (490, 120, 180, "Reject + reason"),
        (700, 30, 145, "Decision contract"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="880" height="205" viewBox="0 0 880 205" role="img" aria-labelledby="title desc">',
        '<title id="title">LLC demonstration decision flow</title>',
        '<desc id="desc">Specification creates candidates, FHA rejects weak cases or sends survivors to a time-stepped linear-equivalent evaluation, then a decision contract preserves execution, gate, and engineering approval states.</desc>',
        f'<rect x="0.5" y="0.5" width="879" height="204" rx="8" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<g stroke="{NEUTRAL_COLOR}" stroke-width="2" fill="none" marker-end="url(#arrow)">',
        '<path d="M160 85 H190"/><path d="M325 85 H355"/>',
        '<path d="M460 76 C475 76 475 63 490 63"/>',
        '<path d="M460 94 C475 94 475 151 490 151"/>',
        '<path d="M670 63 H700"/>',
        '</g>',
        f'<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="{NEUTRAL_COLOR}"/></marker></defs>',
    ]
    for x, y, width, label in nodes:
        height = 65 if "\n" in label else 40
        color = REJECT_COLOR if "Reject" in label else PASS_COLOR if "Decision" in label else "#eef3f7"
        text_color = "#ffffff" if color in {REJECT_COLOR, PASS_COLOR} else TEXT_COLOR
        parts.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="6" fill="{color}" stroke="{GRID_COLOR}"/>'
        )
        lines = label.split("\n")
        start_y = y + height / 2 - (len(lines) - 1) * 9 + 4
        for index, line in enumerate(lines):
            parts.append(
                f'<text x="{x + width / 2}" y="{start_y + index * 18}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{text_color}">{html.escape(line)}</text>'
            )
    parts.append(
        f'<text x="407" y="50" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{PASS_COLOR}">pass</text>'
    )
    parts.append(
        f'<text x="408" y="134" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{REJECT_COLOR}">reject</text>'
    )
    parts.append("</svg>")
    _write(path, "\n".join(parts))


def write_gate_counts_svg(path: Path, summary: dict[str, Any]) -> None:
    values = [
        ("FHA pass", summary["fha_counts"].get("pass", 0), PASS_COLOR),
        ("FHA reject", summary["fha_counts"].get("reject", 0), REJECT_COLOR),
        ("Gate pass", summary["gate_counts"].get("pass", 0), PASS_COLOR),
        ("Gate reject", summary["gate_counts"].get("reject", 0), REJECT_COLOR),
        ("Method failed", summary["execution_counts"].get("failed", 0), FAILED_COLOR),
    ]
    maximum = max(1, max(value for _, value, _ in values))
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="260" viewBox="0 0 760 260" role="img" aria-labelledby="title desc">',
        '<title id="title">Candidate counts by gate</title>',
        '<desc id="desc">Horizontal bars compare FHA and time-stepped evaluation outcomes. The forced failure fixture is not included in campaign counts.</desc>',
        f'<rect x="0.5" y="0.5" width="759" height="259" rx="8" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<text x="24" y="30" font-family="Segoe UI,Arial,sans-serif" font-size="17" font-weight="600" fill="{TEXT_COLOR}">Candidate counts by gate</text>',
    ]
    for index, (label, value, color) in enumerate(values):
        y = 58 + index * 37
        width = 500 * value / maximum
        parts.extend(
            [
                f'<text x="150" y="{y + 16}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">{html.escape(label)}</text>',
                f'<rect x="170" y="{y}" width="500" height="22" rx="3" fill="#eef2f5"/>',
                f'<rect x="170" y="{y}" width="{width:.2f}" height="22" rx="3" fill="{color}"/>',
                f'<text x="{min(705, 180 + width):.2f}" y="{y + 16}" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">{value}</text>',
            ]
        )
    parts.append("</svg>")
    _write(path, "\n".join(parts))


def write_design_space_svg(path: Path, candidates: list[dict[str, Any]]) -> None:
    width, height = 760, 420
    left, right, top, bottom = 75, 28, 50, 62
    x_min = min(row["design_variables"]["ln"] for row in candidates)
    x_max = max(row["design_variables"]["ln"] for row in candidates)
    y_min = min(row["design_variables"]["q"] for row in candidates)
    y_max = max(row["design_variables"]["q"] for row in candidates)

    def sx(value: float) -> float:
        return left + (value - x_min) * (width - left - right) / max(1e-15, x_max - x_min)

    def sy(value: float) -> float:
        return height - bottom - (value - y_min) * (height - top - bottom) / max(1e-15, y_max - y_min)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Generated design space</title>',
        '<desc id="desc">Scatter plot of inductance ratio versus quality factor. Each point is labeled by FHA pass or reject color and shape.</desc>',
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="8" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<text x="24" y="30" font-family="Segoe UI,Arial,sans-serif" font-size="17" font-weight="600" fill="{TEXT_COLOR}">Generated design space</text>',
        f'<rect x="{left}" y="{top}" width="{width-left-right}" height="{height-top-bottom}" fill="#ffffff" stroke="{GRID_COLOR}"/>',
    ]
    for tick in range(6):
        x = left + tick * (width - left - right) / 5
        value = x_min + tick * (x_max - x_min) / 5
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" stroke="{GRID_COLOR}"/>')
        parts.append(f'<text x="{x:.1f}" y="{height-bottom+24}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{value:.2f}</text>')
    for tick in range(6):
        y = top + tick * (height - top - bottom) / 5
        value = y_max - tick * (y_max - y_min) / 5
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{GRID_COLOR}"/>')
        parts.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{value:.2f}</text>')
    for row in candidates:
        x = sx(row["design_variables"]["ln"])
        y = sy(row["design_variables"]["q"])
        result = row["fha_screen"]["gate_result"]
        color = PASS_COLOR if result == "pass" else REJECT_COLOR
        if result == "pass":
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}"><title>{row["candidate_id"]}: FHA pass</title></circle>')
        else:
            parts.append(f'<path d="M{x-5:.2f},{y-5:.2f} L{x+5:.2f},{y+5:.2f} M{x+5:.2f},{y-5:.2f} L{x-5:.2f},{y+5:.2f}" stroke="{color}" stroke-width="2.5"><title>{row["candidate_id"]}: FHA reject</title></path>')
    parts.extend(
        [
            f'<text x="{(left+width-right)/2:.1f}" y="{height-18}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Inductance ratio, Ln [1]</text>',
            f'<text x="18" y="{(top+height-bottom)/2:.1f}" transform="rotate(-90 18 {(top+height-bottom)/2:.1f})" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Quality factor, Q [1]</text>',
            f'<circle cx="565" cy="27" r="5" fill="{PASS_COLOR}"/><text x="577" y="31" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">FHA pass</text>',
            f'<path d="M655,22 L665,32 M665,22 L655,32" stroke="{REJECT_COLOR}" stroke-width="2.5"/><text x="672" y="31" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">FHA reject</text>',
            "</svg>",
        ]
    )
    _write(path, "\n".join(parts))


def write_model_outputs_svg(path: Path, records: list[dict[str, Any]]) -> None:
    evaluated = [
        row for row in records if row["decision_contract"]["execution_status"] == "completed"
    ]
    if not evaluated:
        _write(
            path,
            "\n".join(
                [
                    '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="180" viewBox="0 0 760 180" role="img" aria-labelledby="title desc">',
                    '<title id="title">No time-domain evaluations completed</title>',
                    '<desc id="desc">All candidates were rejected by the completed FHA screen, so the time-stepped evaluation was not run.</desc>',
                    f'<rect x="0.5" y="0.5" width="759" height="179" rx="8" fill="#ffffff" stroke="{GRID_COLOR}"/>',
                    f'<text x="24" y="42" font-family="Segoe UI,Arial,sans-serif" font-size="17" font-weight="600" fill="{TEXT_COLOR}">No time-domain evaluations completed</text>',
                    f'<text x="24" y="82" font-family="Segoe UI,Arial,sans-serif" font-size="14" fill="{TEXT_COLOR}">The FHA stage completed and rejected the full population.</text>',
                    f'<text x="24" y="112" font-family="Segoe UI,Arial,sans-serif" font-size="14" fill="{NEUTRAL_COLOR}">This is a valid engineering result, not a pipeline failure.</text>',
                    "</svg>",
                ]
            ),
        )
        return
    width, height = 760, 420
    left, right, top, bottom = 82, 28, 50, 62
    x_values = [row["time_domain_evaluation"]["metrics"]["switching_frequency_hz"] / 1000 for row in evaluated]
    y_values = [row["time_domain_evaluation"]["metrics"]["resonant_current_rms_a"] for row in evaluated]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_pad = max(1.0, (x_max - x_min) * 0.08)
    y_pad = max(0.02, (y_max - y_min) * 0.08)
    x_min -= x_pad
    x_max += x_pad
    y_min = max(0.0, y_min - y_pad)
    y_max += y_pad

    def sx(value: float) -> float:
        return left + (value - x_min) * (width - left - right) / (x_max - x_min)

    def sy(value: float) -> float:
        return height - bottom - (value - y_min) * (height - top - bottom) / (y_max - y_min)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Equivalent-model evaluation outputs</title>',
        '<desc id="desc">Switching frequency versus resonant current RMS for candidates that completed the time-stepped linear-equivalent evaluation.</desc>',
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="8" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<text x="24" y="30" font-family="Segoe UI,Arial,sans-serif" font-size="17" font-weight="600" fill="{TEXT_COLOR}">Time-stepped linear-equivalent outputs</text>',
        f'<rect x="{left}" y="{top}" width="{width-left-right}" height="{height-top-bottom}" fill="#ffffff" stroke="{GRID_COLOR}"/>',
    ]
    for tick in range(6):
        x = left + tick * (width - left - right) / 5
        value = x_min + tick * (x_max - x_min) / 5
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" stroke="{GRID_COLOR}"/>')
        parts.append(f'<text x="{x:.1f}" y="{height-bottom+24}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{value:.1f}</text>')
    for tick in range(6):
        y = top + tick * (height - top - bottom) / 5
        value = y_max - tick * (y_max - y_min) / 5
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="{GRID_COLOR}"/>')
        parts.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{value:.2f}</text>')
    for row in evaluated:
        metrics = row["time_domain_evaluation"]["metrics"]
        x = sx(metrics["switching_frequency_hz"] / 1000)
        y = sy(metrics["resonant_current_rms_a"])
        color = PASS_COLOR if row["decision_contract"]["gate_result"] == "pass" else REJECT_COLOR
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{color}"><title>{row["candidate_id"]}: {metrics["switching_frequency_hz"]/1000:.2f} kHz, {metrics["resonant_current_rms_a"]:.3f} A RMS</title></circle>')
    parts.extend(
        [
            f'<text x="{(left+width-right)/2:.1f}" y="{height-18}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Switching frequency [kHz]</text>',
            f'<text x="20" y="{(top+height-bottom)/2:.1f}" transform="rotate(-90 20 {(top+height-bottom)/2:.1f})" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Resonant current RMS [A]</text>',
            "</svg>",
        ]
    )
    _write(path, "\n".join(parts))


def _line_path(
    points: list[tuple[float, float]],
    sx: Any,
    sy: Any,
) -> str:
    return " ".join(
        ("M" if index == 0 else "L") + f"{sx(x):.2f},{sy(y):.2f}"
        for index, (x, y) in enumerate(points)
    )


def write_fha_case_svg(
    path: Path,
    record: dict[str, Any],
    config: dict[str, Any],
    case_label: str,
) -> None:
    curve = fha_response_curve(record, config)
    points = curve["points"]
    frequencies_khz = [point["frequency_hz"] / 1000.0 for point in points]
    gains = [point["gain"] for point in points]
    phases = [point["input_phase_deg"] for point in points]
    required_gain = float(curve["required_gain"])
    minimum_phase = float(curve["minimum_inductive_phase_deg"])
    width, height = 880, 690
    left, right = 82, 32
    top_gain, gain_height = 76, 238
    top_phase, phase_height = 385, 238
    x_min, x_max = frequencies_khz[0], frequencies_khz[-1]

    gain_min = min(min(gains), required_gain)
    gain_max = max(max(gains), required_gain)
    gain_pad = max(0.02, 0.08 * (gain_max - gain_min))
    gain_min = max(0.0, gain_min - gain_pad)
    gain_max += gain_pad
    phase_min = min(min(phases), minimum_phase)
    phase_max = max(max(phases), minimum_phase)
    phase_pad = max(2.0, 0.08 * (phase_max - phase_min))
    phase_min -= phase_pad
    phase_max += phase_pad

    def sx(value: float) -> float:
        return left + (value - x_min) * (width - left - right) / (x_max - x_min)

    def sy_gain(value: float) -> float:
        return top_gain + gain_height - (value - gain_min) * gain_height / (
            gain_max - gain_min
        )

    def sy_phase(value: float) -> float:
        return top_phase + phase_height - (value - phase_min) * phase_height / (
            phase_max - phase_min
        )

    valid_intervals: list[tuple[float, float]] = []
    interval_start: float | None = None
    previous_frequency = frequencies_khz[0]
    for frequency, phase in zip(frequencies_khz, phases, strict=True):
        if phase >= minimum_phase and interval_start is None:
            interval_start = frequency
        elif phase < minimum_phase and interval_start is not None:
            valid_intervals.append((interval_start, previous_frequency))
            interval_start = None
        previous_frequency = frequency
    if interval_start is not None:
        valid_intervals.append((interval_start, frequencies_khz[-1]))

    selected_frequency = record["fha_screen"]["metrics"].get("best_frequency_hz")
    selected_gain = record["fha_screen"]["metrics"].get("best_gain")
    selected_phase = record["fha_screen"]["metrics"].get("best_input_phase_deg")
    gate_result = record["fha_screen"]["gate_result"]
    warning = "FHA_SEARCH_BOUNDARY_HIT" in record["fha_screen"].get(
        "warnings", []
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">FHA response for {html.escape(case_label)} {html.escape(record["candidate_id"])}</title>',
        '<desc id="desc">Gain and input phase versus switching frequency, with required gain, the phase-qualified frequency zone, selected point and configured search limits.</desc>',
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="8" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<text x="24" y="31" font-family="Segoe UI,Arial,sans-serif" font-size="18" font-weight="600" fill="{TEXT_COLOR}">FHA response — {html.escape(case_label)}: {html.escape(record["candidate_id"])}</text>',
        f'<text x="24" y="55" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{NEUTRAL_COLOR}">FHA gate: {html.escape(gate_result)}. Green zones satisfy input phase ≥ {minimum_phase:.1f}°.</text>',
        f'<rect x="{left}" y="{top_gain}" width="{width-left-right}" height="{gain_height}" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<rect x="{left}" y="{top_phase}" width="{width-left-right}" height="{phase_height}" fill="#ffffff" stroke="{GRID_COLOR}"/>',
    ]
    for start, end in valid_intervals:
        interval_width = max(0.0, sx(end) - sx(start))
        parts.append(
            f'<rect x="{sx(start):.2f}" y="{top_gain}" width="{interval_width:.2f}" height="{gain_height}" fill="#e8f4ec"/>'
        )
        parts.append(
            f'<rect x="{sx(start):.2f}" y="{top_phase}" width="{interval_width:.2f}" height="{phase_height}" fill="#e8f4ec"/>'
        )

    for tick in range(6):
        frequency = x_min + tick * (x_max - x_min) / 5
        x = sx(frequency)
        parts.extend(
            [
                f'<line x1="{x:.1f}" y1="{top_gain}" x2="{x:.1f}" y2="{top_gain+gain_height}" stroke="{GRID_COLOR}"/>',
                f'<line x1="{x:.1f}" y1="{top_phase}" x2="{x:.1f}" y2="{top_phase+phase_height}" stroke="{GRID_COLOR}"/>',
                f'<text x="{x:.1f}" y="{top_phase+phase_height+23}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{frequency:.0f}</text>',
            ]
        )
    for tick in range(5):
        gain_value = gain_min + tick * (gain_max - gain_min) / 4
        gain_y = sy_gain(gain_value)
        phase_value = phase_min + tick * (phase_max - phase_min) / 4
        phase_y = sy_phase(phase_value)
        parts.extend(
            [
                f'<line x1="{left}" y1="{gain_y:.1f}" x2="{width-right}" y2="{gain_y:.1f}" stroke="{GRID_COLOR}"/>',
                f'<text x="{left-11}" y="{gain_y+4:.1f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{gain_value:.3f}</text>',
                f'<line x1="{left}" y1="{phase_y:.1f}" x2="{width-right}" y2="{phase_y:.1f}" stroke="{GRID_COLOR}"/>',
                f'<text x="{left-11}" y="{phase_y+4:.1f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{phase_value:.1f}</text>',
            ]
        )

    gain_points = list(zip(frequencies_khz, gains, strict=True))
    phase_points = list(zip(frequencies_khz, phases, strict=True))
    parts.extend(
        [
            f'<path d="{_line_path(gain_points, sx, sy_gain)}" fill="none" stroke="#165d8f" stroke-width="2"/>',
            f'<line x1="{left}" y1="{sy_gain(required_gain):.2f}" x2="{width-right}" y2="{sy_gain(required_gain):.2f}" stroke="{REJECT_COLOR}" stroke-width="2" stroke-dasharray="7 5"/>',
            f'<text x="{width-right-6}" y="{sy_gain(required_gain)-7:.2f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{REJECT_COLOR}">required gain {required_gain:.4f}</text>',
            f'<path d="{_line_path(phase_points, sx, sy_phase)}" fill="none" stroke="#6b4ba3" stroke-width="2"/>',
            f'<line x1="{left}" y1="{sy_phase(minimum_phase):.2f}" x2="{width-right}" y2="{sy_phase(minimum_phase):.2f}" stroke="{PASS_COLOR}" stroke-width="2" stroke-dasharray="7 5"/>',
            f'<text x="{width-right-6}" y="{sy_phase(minimum_phase)-7:.2f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{PASS_COLOR}">minimum phase {minimum_phase:.1f}°</text>',
            f'<text x="22" y="{top_gain+gain_height/2:.1f}" transform="rotate(-90 22 {top_gain+gain_height/2:.1f})" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Tank gain [1]</text>',
            f'<text x="22" y="{top_phase+phase_height/2:.1f}" transform="rotate(-90 22 {top_phase+phase_height/2:.1f})" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Input phase [deg]</text>',
            f'<text x="{(left+width-right)/2:.1f}" y="{height-18}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Switching frequency [kHz]</text>',
            f'<text x="{left}" y="{top_gain-9}" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{NEUTRAL_COLOR}">Lower search limit {x_min:.0f} kHz</text>',
            f'<text x="{width-right}" y="{top_gain-9}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{NEUTRAL_COLOR}">Upper search limit {x_max:.0f} kHz</text>',
        ]
    )
    if selected_frequency is not None and selected_gain is not None and selected_phase is not None:
        selected_khz = float(selected_frequency) / 1000.0
        x_selected = sx(selected_khz)
        selected_color = FAILED_COLOR if warning else TEXT_COLOR
        if x_selected > width - right - 120:
            selected_label_x = width - right - 6
            selected_label_anchor = "end"
        elif x_selected < left + 120:
            selected_label_x = left + 6
            selected_label_anchor = "start"
        else:
            selected_label_x = x_selected
            selected_label_anchor = "middle"
        parts.extend(
            [
                f'<line x1="{x_selected:.2f}" y1="{top_gain}" x2="{x_selected:.2f}" y2="{top_phase+phase_height}" stroke="{selected_color}" stroke-width="1.5" stroke-dasharray="4 4"/>',
                f'<circle cx="{x_selected:.2f}" cy="{sy_gain(float(selected_gain)):.2f}" r="5" fill="{selected_color}"/>',
                f'<circle cx="{x_selected:.2f}" cy="{sy_phase(float(selected_phase)):.2f}" r="5" fill="{selected_color}"/>',
                f'<text x="{selected_label_x:.2f}" y="{top_phase-14}" text-anchor="{selected_label_anchor}" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{selected_color}">selected {selected_khz:.2f} kHz{(" — boundary hit" if warning else "")}</text>',
            ]
        )
    parts.append("</svg>")
    _write(path, "\n".join(parts))


def write_waveform_svg(
    path: Path,
    samples: list[tuple[float, float, float, float, float, float]],
) -> None:
    if not samples:
        return
    width, height = 880, 690
    left, right = 86, 32
    top_voltage, panel_height = 76, 238
    top_current = 385
    time_us = [row[0] * 1e6 for row in samples]
    voltage_series = [
        ("Drive voltage", [row[1] for row in samples], "#165d8f"),
        ("Resonant-capacitor voltage", [row[4] for row in samples], "#b64a3a"),
        ("Parallel-branch voltage", [row[5] for row in samples], "#16794b"),
    ]
    current_series = [
        ("Resonant current", [row[2] for row in samples], "#6b4ba3"),
        ("Magnetizing current", [row[3] for row in samples], "#8b5a12"),
    ]

    def domain(values: list[float]) -> tuple[float, float]:
        low, high = min(min(values), 0.0), max(max(values), 0.0)
        pad = max(1e-9, 0.08 * (high - low))
        return low - pad, high + pad

    voltage_min, voltage_max = domain(
        [value for _, values, _ in voltage_series for value in values]
    )
    current_min, current_max = domain(
        [value for _, values, _ in current_series for value in values]
    )
    x_min, x_max = time_us[0], time_us[-1]

    def sx(value: float) -> float:
        return left + (value - x_min) * (width - left - right) / (x_max - x_min)

    def sy_voltage(value: float) -> float:
        return top_voltage + panel_height - (value - voltage_min) * panel_height / (
            voltage_max - voltage_min
        )

    def sy_current(value: float) -> float:
        return top_current + panel_height - (value - current_min) * panel_height / (
            current_max - current_min
        )

    switching_times = [
        time_us[index]
        for index in range(1, len(samples))
        if samples[index][1] != samples[index - 1][1]
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Selected pass-case time-domain waveform</title>',
        '<desc id="desc">Drive voltage, resonant-capacitor voltage, parallel-branch voltage, resonant current and magnetizing current. Dashed vertical lines mark switching instants.</desc>',
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="8" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<text x="24" y="31" font-family="Segoe UI,Arial,sans-serif" font-size="18" font-weight="600" fill="{TEXT_COLOR}">Selected pass-case time-domain waveform</text>',
        f'<text x="24" y="55" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{NEUTRAL_COLOR}">Dashed vertical lines mark drive commutations; current sign is only a commutation proxy.</text>',
        f'<rect x="{left}" y="{top_voltage}" width="{width-left-right}" height="{panel_height}" fill="#ffffff" stroke="{GRID_COLOR}"/>',
        f'<rect x="{left}" y="{top_current}" width="{width-left-right}" height="{panel_height}" fill="#ffffff" stroke="{GRID_COLOR}"/>',
    ]
    for switch_time in switching_times:
        x = sx(switch_time)
        parts.append(
            f'<line x1="{x:.2f}" y1="{top_voltage}" x2="{x:.2f}" y2="{top_voltage+panel_height}" stroke="{NEUTRAL_COLOR}" stroke-width="1" stroke-dasharray="3 4"/>'
        )
        parts.append(
            f'<line x1="{x:.2f}" y1="{top_current}" x2="{x:.2f}" y2="{top_current+panel_height}" stroke="{NEUTRAL_COLOR}" stroke-width="1" stroke-dasharray="3 4"/>'
        )
    for tick in range(6):
        time_value = x_min + tick * (x_max - x_min) / 5
        x = sx(time_value)
        parts.extend(
            [
                f'<line x1="{x:.1f}" y1="{top_voltage}" x2="{x:.1f}" y2="{top_voltage+panel_height}" stroke="{GRID_COLOR}"/>',
                f'<line x1="{x:.1f}" y1="{top_current}" x2="{x:.1f}" y2="{top_current+panel_height}" stroke="{GRID_COLOR}"/>',
                f'<text x="{x:.1f}" y="{top_current+panel_height+23}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{time_value:.1f}</text>',
            ]
        )
    for tick in range(5):
        voltage_value = voltage_min + tick * (voltage_max - voltage_min) / 4
        voltage_y = sy_voltage(voltage_value)
        current_value = current_min + tick * (current_max - current_min) / 4
        current_y = sy_current(current_value)
        parts.extend(
            [
                f'<line x1="{left}" y1="{voltage_y:.1f}" x2="{width-right}" y2="{voltage_y:.1f}" stroke="{GRID_COLOR}"/>',
                f'<text x="{left-11}" y="{voltage_y+4:.1f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{voltage_value:.1f}</text>',
                f'<line x1="{left}" y1="{current_y:.1f}" x2="{width-right}" y2="{current_y:.1f}" stroke="{GRID_COLOR}"/>',
                f'<text x="{left-11}" y="{current_y+4:.1f}" text-anchor="end" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="{TEXT_COLOR}">{current_value:.2f}</text>',
            ]
        )
    for label, values, color in voltage_series:
        series_points = list(zip(time_us, values, strict=True))
        parts.append(
            f'<path d="{_line_path(series_points, sx, sy_voltage)}" fill="none" stroke="{color}" stroke-width="1.6"><title>{html.escape(label)}</title></path>'
        )
    for label, values, color in current_series:
        series_points = list(zip(time_us, values, strict=True))
        parts.append(
            f'<path d="{_line_path(series_points, sx, sy_current)}" fill="none" stroke="{color}" stroke-width="1.8"><title>{html.escape(label)}</title></path>'
        )
    parts.extend(
        [
            f'<text x="22" y="{top_voltage+panel_height/2:.1f}" transform="rotate(-90 22 {top_voltage+panel_height/2:.1f})" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Voltage [V]</text>',
            f'<text x="22" y="{top_current+panel_height/2:.1f}" transform="rotate(-90 22 {top_current+panel_height/2:.1f})" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Current [A]</text>',
            f'<text x="{(left+width-right)/2:.1f}" y="{height-18}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="13" fill="{TEXT_COLOR}">Time [µs]</text>',
            '<g font-family="Segoe UI,Arial,sans-serif" font-size="12">',
            '<line x1="390" y1="30" x2="414" y2="30" stroke="#165d8f" stroke-width="2"/><text x="420" y="34" fill="#17212b">drive</text>',
            '<line x1="475" y1="30" x2="499" y2="30" stroke="#b64a3a" stroke-width="2"/><text x="505" y="34" fill="#17212b">vCr</text>',
            '<line x1="545" y1="30" x2="569" y2="30" stroke="#16794b" stroke-width="2"/><text x="575" y="34" fill="#17212b">vParallel</text>',
            '<line x1="660" y1="30" x2="684" y2="30" stroke="#6b4ba3" stroke-width="2"/><text x="690" y="34" fill="#17212b">iLr</text>',
            '<line x1="735" y1="30" x2="759" y2="30" stroke="#8b5a12" stroke-width="2"/><text x="765" y="34" fill="#17212b">iLm</text>',
            "</g>",
            "</svg>",
        ]
    )
    _write(path, "\n".join(parts))


def write_plots(
    output_dir: Path,
    candidates: list[dict[str, Any]],
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    cases: list[dict[str, Any]],
    config: dict[str, Any],
    waveform_samples: list[tuple[float, float, float, float, float, float]],
) -> None:
    plots = output_dir / "plots"
    write_workflow_svg(plots / "workflow.svg")
    write_gate_counts_svg(plots / "gate_counts.svg", summary)
    write_design_space_svg(plots / "design_space.svg", candidates)
    write_model_outputs_svg(plots / "model_outputs.svg", records)
    for case in cases:
        record = case["record"]
        if "design_variables" not in record or "metrics" not in record.get(
            "fha_screen", {}
        ):
            continue
        if case["case_type"] == "automatic gate pass":
            write_fha_case_svg(plots / "fha_pass_case.svg", record, config, "pass")
        elif case["case_type"] == "valid analytical reject":
            write_fha_case_svg(
                plots / "fha_reject_case.svg", record, config, "reject"
            )
    write_waveform_svg(plots / "pass_case_waveform.svg", waveform_samples)


def _status_table(cases: list[dict[str, Any]]) -> str:
    rows = []
    for case in cases:
        record = case["record"]
        contract = record["decision_contract"]
        fha = record.get("fha_screen", {})
        time_domain = record.get("time_domain_evaluation", {})
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(record['candidate_id'])}</code></td>"
            f"<td>{html.escape(case['case_type'])}</td>"
            f"<td><code>{html.escape(fha.get('execution_status', 'not_applicable'))}</code></td>"
            f"<td><code>{html.escape(fha.get('gate_result', 'not_applicable'))}</code></td>"
            f"<td><code>{html.escape(time_domain.get('execution_status', 'not_applicable'))}</code></td>"
            f"<td><code>{html.escape(contract['gate_result'])}</code></td>"
            f"<td><code>{html.escape(contract['engineering_approval'])}</code></td>"
            f"<td>{html.escape(', '.join(contract['reason_codes']))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def write_html_report(
    output_dir: Path,
    config: dict[str, Any],
    summary: dict[str, Any],
    cases: list[dict[str, Any]],
    verification: dict[str, Any],
) -> None:
    spec = config["input_spec"]
    run_name = str(config["run_name"])
    if run_name == "llc-quick-demo-v1":
        report_title = "LLC quick demo"
    elif run_name == "llc-full-rebuild-v1" and summary["candidate_count"] == 200:
        report_title = "LLC full 200-candidate rebuild"
    else:
        report_title = f"Custom LLC campaign — {run_name}"
    status = str(verification.get("status", "FAIL"))
    status_class = "pass" if status == "PASS" else "fail"
    verification_errors = verification.get("errors", [])
    verification_errors_html = ""
    if verification_errors:
        items = "".join(
            f"<li><code>{html.escape(str(error))}</code></li>"
            for error in verification_errors
        )
        verification_errors_html = (
            '<div class="verification-failure"><strong>Verification errors:</strong>'
            f"<ul>{items}</ul></div>"
        )
    generated_at = html.escape(str(summary.get("generated_at_utc", "unknown")))
    verified_at = html.escape(str(verification.get("verified_at_utc", "unknown")))
    survivor_count = int(summary["gate_counts"].get("pass", 0))
    if survivor_count:
        survivor_notice = ""
    else:
        survivor_notice = (
            '<div class="boundary"><strong>0 candidates passed the configured gate.</strong><br>'
            "The current design space does not contain a surviving candidate. "
            "Review turns ratio, frequency range or tank-variable bounds.</div>"
        )
    if int(summary["fha_counts"].get("reject", 0)) == 0:
        reject_notice = (
            '<div class="boundary"><strong>No real analytical rejection occurred in this run.</strong> '
            "No synthetic reject has been added to the evidence table.</div>"
        )
    else:
        reject_notice = ""
    boundary_ids = summary.get("fha_search_boundary_hit_ids", [])
    if boundary_ids:
        boundary_warning = (
            '<div class="boundary"><strong>FHA_SEARCH_BOUNDARY_HIT.</strong> '
            "The selected FHA point lies on a configured search boundary for: "
            + html.escape(", ".join(boundary_ids))
            + ". These candidates keep their gate result but require inspection before interpreting the selected frequency as an interior optimum.</div>"
        )
    else:
        boundary_warning = ""
    reject_boundary_ids = summary.get("fha_reject_upper_boundary_ids", [])
    if reject_boundary_ids:
        reject_boundary_warning = (
            '<div class="boundary"><strong>FHA_REJECT_AT_UPPER_SEARCH_BOUNDARY.</strong> '
            + html.escape(str(len(reject_boundary_ids)))
            + " rejected candidates selected their closest gain point at the 180 kHz upper limit. "
            "They did not reach the target within the allowed search and phase-qualified region.</div>"
        )
    else:
        reject_boundary_warning = ""
    fha_visuals = ""
    if (output_dir / "plots" / "fha_pass_case.svg").is_file():
        fha_visuals += (
            '<img class="chart" src="plots/fha_pass_case.svg" '
            'alt="FHA gain and input phase curves for the selected pass case">'
        )
    if (output_dir / "plots" / "fha_reject_case.svg").is_file():
        fha_visuals += (
            '<img class="chart" src="plots/fha_reject_case.svg" '
            'alt="FHA gain and input phase curves for the selected reject case">'
        )
    waveform_visual = ""
    if (output_dir / "plots" / "pass_case_waveform.svg").is_file():
        waveform_visual = (
            '<img class="chart" src="plots/pass_case_waveform.svg" '
            'alt="Drive voltage, tank voltages and tank currents for the selected pass case">'
            '<p>The dashed lines are switching instants. Current polarity at those instants is a commutation-current sign proxy; it is not a complete demonstration of device-level ZVS.</p>'
        )
    report = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(report_title)} report</title>
<style>
:root {{ color-scheme: light dark; --bg:#f5f7fa; --surface:#fff; --text:#17212b; --muted:#536273; --line:#d8dee6; --accent:#165d8f; --pass:#16794b; --reject:#b64a3a; --failed:#8b5a12; }}
@media (prefers-color-scheme:dark) {{ :root {{ --bg:#10151b; --surface:#18212a; --text:#eef3f7; --muted:#b6c2cf; --line:#3a4652; --accent:#79b8e5; }} img {{ background:#fff; border-radius:8px; }} }}
* {{ box-sizing:border-box; }} body {{ margin:0; font:16px/1.55 "Segoe UI",Arial,sans-serif; background:var(--bg); color:var(--text); }}
main {{ max-width:1050px; margin:auto; padding:32px 20px 64px; }} h1 {{ line-height:1.15; margin-bottom:8px; }} h2 {{ margin-top:42px; }} p.lead {{ color:var(--muted); font-size:1.08rem; max-width:850px; }}
.status {{ display:inline-block; padding:4px 10px; border-radius:999px; font-weight:600; color:#fff; }} .status.pass {{ background:var(--pass); }} .status.fail {{ background:var(--reject); }}
.facts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:12px; margin:24px 0; }} .fact {{ background:var(--surface); border:1px solid var(--line); border-radius:8px; padding:14px; }} .fact b {{ display:block; font-size:1.35rem; }} .fact span {{ color:var(--muted); }}
.boundary {{ border-left:5px solid var(--failed); padding:12px 18px; background:var(--surface); }}
.verification-failure {{ border-left:5px solid var(--reject); padding:12px 18px; margin:18px 0; background:var(--surface); }} .verification-failure ul {{ margin-bottom:0; }}
.timestamps {{ color:var(--muted); font-size:.92rem; }}
img.chart {{ display:block; width:100%; max-width:880px; height:auto; margin:16px 0 26px; }}
table {{ width:100%; border-collapse:collapse; background:var(--surface); }} th,td {{ text-align:left; padding:10px; border-bottom:1px solid var(--line); vertical-align:top; }} th {{ color:var(--muted); }} code {{ font-size:.9em; }}
.files li {{ margin:6px 0; }}
.continue {{ margin-top:42px; padding:24px; border:1px solid var(--line); border-radius:10px; background:var(--surface); }}
.continue h2 {{ margin-top:0; }} .brand {{ color:var(--accent); font-weight:700; letter-spacing:.02em; }}
.cta {{ display:inline-block; margin-top:8px; padding:10px 16px; border-radius:6px; background:var(--accent); color:#fff; font-weight:600; text-decoration:none; }}
.cta:hover,.cta:focus {{ text-decoration:underline; }} footer {{ margin-top:48px; color:var(--muted); font-size:.92rem; }}
</style>
</head>
<body><main>
<span class="status {status_class}">OUTPUT INTEGRITY: {html.escape(status)}</span>
<h1>{html.escape(report_title)}: from engineering rules to auditable decisions</h1>
<p class="lead">This report was generated from configuration, seed, equations and decision rules. It does not reuse the archived 200-candidate outputs and it does not require LTspice for the core demonstration.</p>
<p class="timestamps">Generated at: <code>{generated_at}</code><br>Last verified at: <code>{verified_at}</code></p>
{verification_errors_html}

<div class="facts">
<div class="fact"><b>{spec['vin_v']:.0f} V</b><span>Input voltage</span></div>
<div class="fact"><b>{spec['vout_v']:.0f} V</b><span>Output target</span></div>
<div class="fact"><b>{spec['pout_w']:.0f} W</b><span>Power target</span></div>
<div class="fact"><b>{summary['candidate_count']}</b><span>Generated candidates</span></div>
<div class="fact"><b>{summary['fha_counts']['reject']}</b><span>FHA rejects</span></div>
<div class="fact"><b>{summary['gate_counts']['pass']}</b><span>Automatic gate passes</span></div>
</div>
{survivor_notice}
{reject_notice}
{boundary_warning}
{reject_boundary_warning}

<h2>Decision flow</h2>
<img class="chart" src="plots/workflow.svg" alt="Decision workflow from specification through FHA, equivalent evaluation and decision contract">
<p>The workflow keeps three independent fields: method execution, automatic gate result and engineering approval. A completed method can reject a candidate; a failed method cannot.</p>

<h2>Candidate population</h2>
<img class="chart" src="plots/gate_counts.svg" alt="Candidate counts by decision gate">
<img class="chart" src="plots/design_space.svg" alt="Generated design space plotted as Ln versus Q">

<h2>Why FHA advances or rejects a candidate</h2>
{fha_visuals}
<p>The green frequency zones satisfy the configured input-phase threshold. The gain target, search limits and selected point show whether extending the frequency range could reveal an interior solution or merely move the optimum to another boundary.</p>

<h2>Time-stepped linear-equivalent evaluation</h2>
<img class="chart" src="plots/model_outputs.svg" alt="Switching frequency versus resonant current RMS">
<p>The reported power ratio and commutation-current sign proxies belong only to this simplified model. They are not device-efficiency or measured-ZVS claims.</p>
{waveform_visual}

<h2>{len(cases)} cases to learn from</h2>
<div style="overflow-x:auto"><table>
<thead><tr><th>Record</th><th>Case</th><th>FHA execution</th><th>FHA gate</th><th>Time-domain execution</th><th>Final automated disposition</th><th>Engineering</th><th>Reason</th></tr></thead>
<tbody>{_status_table(cases)}</tbody>
</table></div>
<p>The forced failure is an explicitly synthetic pipeline test. It demonstrates bookkeeping behavior and is excluded from campaign and ML rows.</p>

<h2>Machine-learning export</h2>
<p><code>ml_dataset_v1.csv</code> keeps hardware-only design identity, hashed operating-point identity, method fidelity, target availability and decision states separate. Failures and not-run evaluations do not receive zero-valued targets. The split manifest assigns every hardware design to exactly one block.</p>

<div class="boundary"><strong>Model boundary.</strong> This run covers one operating point with FHA and a switched linear-equivalent tank model. It does not approve hardware and does not validate magnetics, semiconductor losses, thermal behavior, EMI, control robustness, tolerances or correlation with LTspice.</div>

<h2>Next evidence</h2>
<p>Add controlled line, load, temperature and tolerance operating points, then complete a tractable higher-fidelity comparison for selected designs. Freeze design-grouped splits before fitting a surrogate. More rows alone do not resolve the current model boundary.</p>

<h2>Generated files</h2>
<ul class="files">
<li><code>candidate_records.csv</code> and <code>candidate_records.jsonl</code></li>
<li><code>manifest.json</code> and <code>verification.json</code></li>
<li><code>pedagogical_cases.json</code></li>
<li><code>ml_dataset_v1.csv</code>, dictionaries, split manifest and dataset card</li>
<li><code>plots/</code> with offline SVG figures</li>
<li><code>plots/fha_*_case.svg</code> and, when a pass exists, <code>plots/pass_case_waveform.svg</code></li>
</ul>
<section class="continue">
<p class="brand">AI-Native Power Electronics — Rafael Collado</p>
<h2>Continue the evidence-led sequence</h2>
<p>The next Field Note shows how a simulation result becomes a training label—and which rows must be excluded before training a first model.</p>
<a class="cta" href="https://ainativepower.com/field-notes">Get the next Field Note</a>
</section>
<footer>Configuration schema: {html.escape(config['schema_version'])}. Run definition: <code>{html.escape(str(summary.get('run_definition_id', 'unknown')))}</code>. Execution: <code>{html.escape(str(summary.get('execution_id', 'unknown')))}</code>.</footer>
</main></body></html>
"""
    _write(output_dir / "summary.html", report)


def write_verification_failure_html(
    output_dir: Path, verification: dict[str, Any], generated_at_utc: str = "unknown"
) -> None:
    errors = verification.get("errors", ["REPORT_CONTEXT_MISSING"])
    items = "".join(
        f"<li><code>{html.escape(str(error))}</code></li>" for error in errors
    )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLC output integrity failure</title><style>body{{font:16px/1.5 "Segoe UI",Arial,sans-serif;max-width:900px;margin:auto;padding:32px;color:#17212b}}.status{{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:600;color:#fff;background:#b64a3a}}code{{font-size:.92em}}</style></head>
<body><span class="status">OUTPUT INTEGRITY: FAIL</span><h1>Generated report context is unavailable or invalid</h1>
<p>Generated at: <code>{html.escape(generated_at_utc)}</code><br>Last verified at: <code>{html.escape(str(verification.get('verified_at_utc', 'unknown')))}</code></p>
<h2>Verification errors</h2><ul>{items}</ul></body></html>"""
    _write(output_dir / "summary.html", document)
