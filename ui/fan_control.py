# ui/fan_control.py
"""Fan Control page — profile buttons, fan curve editor, temp graph."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from ui.theme import (
    CPU_COLOR, GPU_COLOR, WARNING_COLOR, TEXT_SECONDARY,
    make_label, make_card,
)
from ui.widgets import RollingGraph
from ui.fan_curve_editor import FanCurveEditor
from ui.helpers import (
    safe_read_byte, apply_profile, PROFILE_DISPLAY,
)
from model_config import save_user_config


class FanControlPage(Gtk.Box):
    """Fan control page with profile buttons, curve editor, and temp graph.

    Args:
        model: ModelConfig instance
        ec: ECAccess instance
        user_cfg: user config dict (mutated in-place on profile change)
        on_profile_changed: callback(profile_name) to update sidebar indicator
    """

    def __init__(self, model, ec, user_cfg, on_profile_changed=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.model = model
        self.ec = ec
        self.user_cfg = user_cfg
        self.on_profile_changed = on_profile_changed
        self._profile_buttons = {}
        self._boost_button = None
        self._active_curve = "cpu"  # which curve is shown in editor

        # --- Profile toggle buttons ---
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        for mode_name in model.fan_modes:
            display = PROFILE_DISPLAY.get(mode_name, mode_name.title())
            btn = Gtk.Button(label=display)
            btn.get_style_context().add_class("profile-btn")
            btn.connect("clicked", self._on_profile_clicked, mode_name)
            self._profile_buttons[mode_name] = btn
            btn_row.pack_start(btn, False, False, 0)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        sep.set_margin_start(4)
        sep.set_margin_end(4)
        btn_row.pack_start(sep, False, False, 0)

        # Cooler Boost toggle switch
        boost_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        boost_box.set_valign(Gtk.Align.CENTER)
        boost_box.pack_start(make_label("Cooler Boost", color=WARNING_COLOR, size=12), False, False, 0)
        self._boost_switch = Gtk.Switch()
        self._boost_switch.get_style_context().add_class("boost-switch")
        self._boost_switch.set_valign(Gtk.Align.CENTER)
        # Read current boost state
        current = safe_read_byte(ec, model.cooler_boost_addr)
        is_boosted = bool(current & (1 << model.cooler_boost_bit))
        self._boost_switch.set_active(is_boosted)
        self._boost_switch.connect("state-set", self._on_boost_toggled)
        boost_box.pack_start(self._boost_switch, False, False, 0)
        btn_row.pack_start(boost_box, False, False, 0)

        self.pack_start(btn_row, False, False, 0)

        # Highlight the current profile
        self._update_profile_buttons(user_cfg.get("profile", "auto"))

        # --- Fan curve editor ---
        curve_card = make_card()

        curve_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        curve_header.pack_start(make_label("Fan Curve Editor", size=12, bold=True), False, False, 0)

        # CPU/GPU tabs (only if model has GPU)
        if model.has_gpu:
            tab_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            self._cpu_tab = Gtk.Button(label="CPU")
            self._cpu_tab.get_style_context().add_class("profile-btn")
            self._cpu_tab.get_style_context().add_class("active")
            self._cpu_tab.connect("clicked", self._on_curve_tab, "cpu")
            tab_box.pack_start(self._cpu_tab, False, False, 0)

            self._gpu_tab = Gtk.Button(label="GPU")
            self._gpu_tab.get_style_context().add_class("profile-btn")
            self._gpu_tab.connect("clicked", self._on_curve_tab, "gpu")
            tab_box.pack_start(self._gpu_tab, False, False, 0)

            curve_header.pack_end(tab_box, False, False, 0)

        curve_card.pack_start(curve_header, False, False, 0)

        # Subtitle
        curve_card.pack_start(
            make_label("Click a point to edit its speed value", color=TEXT_SECONDARY, size=10),
            False, False, 0,
        )

        # Read current fan curve temps from EC (6 temp thresholds)
        self._cpu_temps = [safe_read_byte(ec, a) for a in model.cpu_fan_curve_temp_addrs]
        self._cpu_speeds = [safe_read_byte(ec, a) for a in model.cpu_fan_curve_speed_addrs]
        if model.has_gpu:
            self._gpu_temps = [safe_read_byte(ec, a) for a in model.gpu_fan_curve_temp_addrs]
            self._gpu_speeds = [safe_read_byte(ec, a) for a in model.gpu_fan_curve_speed_addrs]

        self.curve_editor = FanCurveEditor(
            color=CPU_COLOR,
            temps=self._cpu_temps,
            speeds=self._cpu_speeds,
            on_speed_changed=self._on_cpu_speed_changed,
        )
        # Only enabled for "advanced" profile
        is_adv = user_cfg.get("profile", "auto") == "advanced"
        self.curve_editor.set_enabled(is_adv and not ec.is_read_only)
        curve_card.pack_start(self.curve_editor, True, True, 0)
        self.pack_start(curve_card, True, True, 0)

        # --- Compact temperature history graph ---
        temp_lines = [{'color': CPU_COLOR, 'label': 'CPU', 'dashed': False}]
        if model.has_gpu:
            temp_lines.append({'color': GPU_COLOR, 'label': 'GPU', 'dashed': False})
        self.temp_graph = RollingGraph(
            lines=temp_lines, y_min=25, y_max=100, y_label="°C"
        )
        self.temp_graph.set_size_request(-1, 100)
        temp_card = make_card()
        temp_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        temp_header.pack_start(make_label("Temperature History", size=12, bold=True), False, False, 0)
        self._temp_legend = make_label("", size=10)
        self._temp_legend.set_halign(Gtk.Align.END)
        temp_header.pack_end(self._temp_legend, False, False, 0)
        temp_card.pack_start(temp_header, False, False, 0)
        temp_card.pack_start(self.temp_graph, True, True, 0)
        self.pack_start(temp_card, False, False, 0)

    def update(self, ec):
        """Called every 500ms to update live temp display."""
        cpu_temp = safe_read_byte(ec, self.model.cpu_temp_addr)
        self.temp_graph.add_point(0, cpu_temp)
        self.curve_editor.set_current_temp(cpu_temp)

        legend_parts = [f'<span foreground="{CPU_COLOR}">CPU {cpu_temp}°C</span>']

        if self.model.has_gpu:
            gpu_temp = safe_read_byte(ec, self.model.gpu_temp_addr)
            self.temp_graph.add_point(1, gpu_temp)
            legend_parts.append(f'<span foreground="{GPU_COLOR}">GPU {gpu_temp}°C</span>')

        self._temp_legend.set_markup("  ".join(legend_parts))
        self.temp_graph.queue_draw()

    def _update_profile_buttons(self, active_name):
        """Highlight the active profile button."""
        for name, btn in self._profile_buttons.items():
            ctx = btn.get_style_context()
            if name == active_name:
                ctx.add_class("active")
            else:
                ctx.remove_class("active")

    def _on_profile_clicked(self, button, profile_name):
        if self.ec.is_read_only:
            return
        apply_profile(self.ec, self.model, self.user_cfg, profile_name)
        self._update_profile_buttons(profile_name)

        is_adv = profile_name == "advanced"
        self.curve_editor.set_enabled(is_adv)

        if self.on_profile_changed:
            self.on_profile_changed(profile_name)

    def _on_boost_toggled(self, switch, state):
        if self.ec.is_read_only:
            switch.set_active(not state)
            return True
        current = self.ec.read_byte(self.model.cooler_boost_addr)
        if state:
            self.ec.write_byte(
                self.model.cooler_boost_addr,
                current | (1 << self.model.cooler_boost_bit)
            )
        else:
            self.ec.write_byte(
                self.model.cooler_boost_addr,
                current & ~(1 << self.model.cooler_boost_bit)
            )
        return False

    def _on_curve_tab(self, button, which):
        """Switch between CPU and GPU fan curves."""
        self._active_curve = which
        if which == "cpu":
            self.curve_editor.set_temps(self._cpu_temps)
            self.curve_editor.set_curve(self._cpu_speeds)
            self.curve_editor.color = CPU_COLOR
            self.curve_editor.rgba = (0xFF/255, 0x46/255, 0x55/255, 1.0)
            self.curve_editor.on_speed_changed = self._on_cpu_speed_changed
            self._cpu_tab.get_style_context().add_class("active")
            self._gpu_tab.get_style_context().remove_class("active")
        else:
            self.curve_editor.set_temps(self._gpu_temps)
            self.curve_editor.set_curve(self._gpu_speeds)
            self.curve_editor.color = GPU_COLOR
            self.curve_editor.rgba = (0x00/255, 0xD4/255, 0xFF/255, 1.0)
            self.curve_editor.on_speed_changed = self._on_gpu_speed_changed
            self._gpu_tab.get_style_context().add_class("active")
            self._cpu_tab.get_style_context().remove_class("active")

    def _on_cpu_speed_changed(self, index, new_speed):
        """Write updated CPU fan speed to EC."""
        self._cpu_speeds[index] = new_speed
        self.ec.write_byte(self.model.cpu_fan_curve_speed_addrs[index], new_speed)

    def _on_gpu_speed_changed(self, index, new_speed):
        """Write updated GPU fan speed to EC."""
        self._gpu_speeds[index] = new_speed
        self.ec.write_byte(self.model.gpu_fan_curve_speed_addrs[index], new_speed)
