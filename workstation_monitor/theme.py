"""Local GTK palette; no fonts, assets or services are downloaded at runtime."""

from pathlib import Path
from .native import Adw, Gtk


PALETTES = {
    True: {"bg": "#101215", "panel": "#181b1f", "raised": "#202429", "text": "#f3f5f6",
           "muted": "#aab1bb", "border": "#343a42", "accent": "#92efd5", "secondary": "#8cbce8",
           "track": "#40464e", "selection": "#243b36", "warning": "#f2bd74"},
    False: {"bg": "#f4f6f7", "panel": "#ffffff", "raised": "#edf1f3", "text": "#19242b",
            "muted": "#52616c", "border": "#d1d9de", "accent": "#087c64", "secondary": "#216eaa",
            "track": "#dbe3e7", "selection": "#d9eee7", "warning": "#925500"},
}


class Theme:
    def __init__(self, display):
        self.provider = Gtk.CssProvider()
        self.css = Path(__file__).with_name("theme.css").read_text()
        Gtk.StyleContext.add_provider_for_display(display, self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.manager = Adw.StyleManager.get_default()
        self.signal = self.manager.connect("notify::dark", lambda *_: self.reload())
        self.reload()

    def reload(self):
        colors = PALETTES[self.manager.get_dark()]
        definitions = "\n".join(f"@define-color monitor_{key} {value};" for key, value in colors.items())
        self.provider.load_from_data((definitions + "\n" + self.css).encode())

    def close(self, display):
        self.manager.disconnect(self.signal)
        Gtk.StyleContext.remove_provider_for_display(display, self.provider)
