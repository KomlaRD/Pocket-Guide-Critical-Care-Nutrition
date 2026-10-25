from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_native_mobile_back_control_without_duplicate():
    app=(ROOT/'app.py').read_text()
    js=(ROOT/'www/navigation.js').read_text()
    css=(ROOT/'www/styles.css').read_text()
    assert 'pg-mobile-close-menu' not in app
    assert 'pg-mobile-close-menu' not in js
    assert 'margin-top: 58px !important' in css
    assert 'bslib-sidebar-toggle' in css
