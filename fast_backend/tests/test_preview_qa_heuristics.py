import numpy as np

from fast_backend.app.services.preview_qa_service import analyze_frame_heuristics


def _issue_codes(result):
    return {issue["code"] for issue in result["issues"]}


def test_analyze_frame_heuristics_flags_border_crowding():
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    frame[:10, :, :] = 255
    frame[-10:, :, :] = 255
    frame[:, :10, :] = 255
    frame[:, -10:, :] = 255

    result = analyze_frame_heuristics(frame)
    assert "border_crowding" in _issue_codes(result)


def test_analyze_frame_heuristics_flags_top_bottom_empty_imbalance():
    frame = np.zeros((180, 240, 3), dtype=np.uint8)
    frame[70:120, 30:210, :] = 255

    result = analyze_frame_heuristics(frame)
    assert "top_bottom_empty_imbalance" in _issue_codes(result)


def test_analyze_frame_heuristics_prefers_balance_issue_for_generic_dense_band():
    frame = np.zeros((200, 260, 3), dtype=np.uint8)
    frame[40:140, 40:220, :] = 120
    for y in range(110, 145, 2):
        frame[y : y + 1, 40:220, :] = 255

    result = analyze_frame_heuristics(frame)
    codes = _issue_codes(result)
    assert "top_bottom_empty_imbalance" in codes


def test_analyze_frame_heuristics_does_not_flag_normal_graph_line_density():
    frame = np.zeros((320, 180, 3), dtype=np.uint8)
    frame[65:285, 30:150, :] = 85
    for x in range(30, 150):
        y1 = int(145 + 22 * np.sin((x - 30) / 11.0))
        y2 = int(165 + 22 * np.cos((x - 30) / 10.0))
        frame[max(65, y1 - 1) : min(285, y1 + 2), x : x + 1, :] = 255
        frame[max(65, y2 - 1) : min(285, y2 + 2), x : x + 1, :] = 240

    result = analyze_frame_heuristics(frame)
    assert "dense_horizontal_label_band" not in _issue_codes(result)


def test_analyze_frame_heuristics_does_not_flag_formula_only_center_stack_as_label_band():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    # Simulate four centered equation rows with healthy margins.
    rows = [(52, 68), (88, 104), (124, 140), (160, 176)]
    widths = [(86, 234), (76, 244), (92, 228), (82, 238)]
    for (y0, y1), (x0, x1) in zip(rows, widths):
        frame[y0:y1, x0:x1, :] = 235
        for y in range(y0 + 2, y1, 4):
            frame[y : y + 1, x0:x1, :] = 255

    result = analyze_frame_heuristics(frame)
    codes = _issue_codes(result)
    assert "dense_horizontal_label_band" not in codes


def test_analyze_frame_heuristics_keeps_clean_frame_without_flags():
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    frame[45:75, 85:115, :] = 220

    result = analyze_frame_heuristics(frame)
    assert result["issues"] == []
