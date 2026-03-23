from PIL import Image


def test_render_icon_returns_64x64():
    from icon_renderer import render_icon
    img = render_icon(4.20, warning=50.0, critical=100.0)
    assert isinstance(img, Image.Image)
    assert img.size == (64, 64)


def test_render_icon_below_warning():
    from icon_renderer import render_icon
    img = render_icon(1.00, warning=50.0, critical=100.0)
    assert img.size == (64, 64)


def test_render_icon_at_warning():
    from icon_renderer import render_icon
    img = render_icon(50.0, warning=50.0, critical=100.0)
    assert img.size == (64, 64)


def test_render_icon_at_critical():
    from icon_renderer import render_icon
    img = render_icon(100.0, warning=50.0, critical=100.0)
    assert img.size == (64, 64)


def test_render_icon_zero_cost():
    from icon_renderer import render_icon
    img = render_icon(0.0, warning=50.0, critical=100.0)
    assert img.size == (64, 64)


def test_render_icon_large_cost():
    from icon_renderer import render_icon
    img = render_icon(999.99, warning=50.0, critical=100.0)
    assert img.size == (64, 64)
