from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] / "www" / "styles.css").read_text()

def test_desktop_sidebar_is_viewport_bounded():
    rule = CSS.split("/* RC3.5: viewport-bounded navigation", 1)[1]
    desktop = rule.split("@media (max-width: 767px)", 1)[0]
    assert "@media (min-width: 768px)" in desktop
    assert "position: sticky !important" in desktop
    assert "height: 100dvh !important" in desktop
    assert "max-height: 100dvh !important" in desktop
    assert "overflow-y: auto !important" in desktop

def test_mobile_sidebar_remains_viewport_bounded():
    mobile = CSS.split("/* RC3.5: viewport-bounded navigation", 1)[1].split("@media (max-width: 767px)", 1)[1]
    assert "max-height: 100dvh !important" in mobile
