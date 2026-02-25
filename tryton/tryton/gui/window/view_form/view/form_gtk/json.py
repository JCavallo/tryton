import json

from gi.repository import Gtk

from .widget import Widget


class JSON(Widget):
    "JSON Widget"
    expand = True

    def __init__(self, view, attrs):
        super().__init__(view, attrs)

        self.widget = Gtk.VBox()
        self.scrolledwindow = Gtk.ScrolledWindow()
        self.scrolledwindow.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scrolledwindow.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.scrolledwindow.set_size_request(100, 100)

        self.textview = self.mnemonic_widget = self._get_textview()
        self.scrolledwindow.add(self.textview)
        self.scrolledwindow.show_all()
        self.widget.pack_end(
            self.scrolledwindow, expand=True, fill=True, padding=0)

    def _readonly_set(self, value):
        super()._readonly_set(value)
        self.textview.set_editable(not value)

    def _color_widget(self):
        return self.textview

    def _get_textview(self):
        textview = Gtk.TextView()
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_accepts_tab(False)
        return textview

    def set_buffer(self, value, textview):
        buf = textview.get_buffer()
        buf.delete(buf.get_start_iter(), buf.get_end_iter())
        iter_start = buf.get_start_iter()
        buf.insert(iter_start, value)

    def display(self):
        super().display()
        value = self.field and self.field.get(self.record)
        if value is None:
            value = ''
        else:
            value = json.dumps(value, indent=2)
        self.set_buffer(value, self.textview)
