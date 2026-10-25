from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "www/navigation.js").read_text()
CSS = (ROOT / "www/styles.css").read_text()
APP = (ROOT / "app.py").read_text()

def test_mobile_menu_resets_scroll():
    assert "function resetMenuScroll()" in JS
    assert "sidebar.scrollTop = 0" in JS
    assert "requestAnimationFrame(resetMenuScroll)" in JS
    assert "openMobileMenu();" in JS

def test_mobile_drawer_has_independent_scroll():
    assert "overscroll-behavior-y: contain" in CSS
    assert "height: 100dvh !important" in CSS
    assert "overflow-y: auto !important" in CSS

def test_existing_navigation_remains():
    assert 'id="mobile-nav-menu"' in APP
    for name in ('Home', 'Guidance', 'Nutrition', 'Tools'):
        assert f'ui.a("{name}"' in APP
