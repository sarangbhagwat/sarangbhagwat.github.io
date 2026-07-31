import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import detect_cv  # noqa: E402


def test_find_cv_returns_matching_file(tmp_path):
    (tmp_path / "Bhagwat-Sarang_CV.pdf").write_bytes(b"%PDF-")
    (tmp_path / "headshot.jpg").write_bytes(b"x")
    assert detect_cv.find_cv(tmp_path) == "Bhagwat-Sarang_CV.pdf"


def test_find_cv_prefers_lexicographically_greatest(tmp_path):
    (tmp_path / "Bhagwat-Sarang_CV_2025.pdf").write_bytes(b"%PDF-")
    (tmp_path / "Bhagwat-Sarang_CV_2026.pdf").write_bytes(b"%PDF-")
    assert detect_cv.find_cv(tmp_path) == "Bhagwat-Sarang_CV_2026.pdf"


def test_find_cv_ignores_non_matching_names(tmp_path):
    (tmp_path / "cv.pdf").write_bytes(b"%PDF-")
    (tmp_path / "Bhagwat-Sarang_Resume.pdf").write_bytes(b"%PDF-")
    assert detect_cv.find_cv(tmp_path) is None


def test_render_cv_json_shapes_path_and_null():
    assert '"file": "assets/Bhagwat-Sarang_CV.pdf"' in \
        detect_cv.render_cv_json("Bhagwat-Sarang_CV.pdf")
    assert '"file": null' in detect_cv.render_cv_json(None)


def test_write_cv_json_reports_change_then_no_change(tmp_path):
    out = tmp_path / "cv.json"
    assert detect_cv.write_cv_json("Bhagwat-Sarang_CV.pdf", out) is True
    assert detect_cv.write_cv_json("Bhagwat-Sarang_CV.pdf", out) is False
