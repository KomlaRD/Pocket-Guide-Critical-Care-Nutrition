from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_single_persistent_mobile_close_control():
    app=(ROOT/'app.py').read_text()
    js=(ROOT/'www/navigation.js').read_text()
    css=(ROOT/'www/styles.css').read_text()
    assert 'id="pg-mobile-close-menu"' in app
    assert "event.target.closest('#pg-mobile-close-menu')" in js
    assert 'visibility:hidden!important' in css
    assert 'position:sticky' in css
