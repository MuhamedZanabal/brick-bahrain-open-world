"""CI-only compatibility shim for Pillow's Latin-1 fallback font.

The canonical evidence workflow uses exact ASCII labels after this adapter. It does
not alter runtime assets, screenshots, source-project files, or game behavior.
"""

try:
    from PIL import ImageDraw

    _original_text = ImageDraw.ImageDraw.text

    def _ascii_safe_text(self, xy, text, *args, **kwargs):
        if isinstance(text, str):
            text = text.replace("—", "-")
        return _original_text(self, xy, text, *args, **kwargs)

    ImageDraw.ImageDraw.text = _ascii_safe_text
except Exception:
    # Pillow is not required by every Python invocation in the repository.
    pass
