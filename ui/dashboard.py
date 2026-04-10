# ui/dashboard.py
"""Dashboard page — stat cards and rolling temperature/RPM graphs."""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from ui.theme import CPU_COLOR, GPU_COLOR, make_label, make_card
from ui.widgets import RollingGraph, StatCard
from ui.helpers import safe_read_byte, safe_read_rpm


class DashboardPage(Gtk.Box):
    """Dashboard page with stat cards and real-time graphs.

    Args:
        model: ModelConfig instance
    """

    def __init__(self, model):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(20)
        self.set_margin_end(20)
        self.set_margin_top(20)
        self.set_margin_bottom(20)
        self.model = model

        # Stat cards row
        cards_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cards_row.set_homogeneous(True)

        self.cpu_card = StatCard("CPU", CPU_COLOR)
        cards_row.pack_start(self.cpu_card, True, True, 0)

        self.gpu_card = None
        if model.has_gpu:
            self.gpu_card = StatCard("GPU", GPU_COLOR)
            cards_row.pack_start(self.gpu_card, True, True, 0)

        self.pack_start(cards_row, False, False, 0)

        # Temperature history graph
        temp_lines = [{'color': CPU_COLOR, 'label': 'CPU', 'dashed': False}]
        if model.has_gpu:
            temp_lines.append({'color': GPU_COLOR, 'label': 'GPU', 'dashed': False})
        self.temp_graph = RollingGraph(
            lines=temp_lines, y_min=25, y_max=100, y_label="°C"
        )
        temp_card = make_card()
        temp_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        temp_header.pack_start(make_label("Temperature History", size=12, bold=True), False, False, 0)
        temp_header.pack_end(make_label("Last 60 seconds", color="#666666", size=10), False, False, 0)
        temp_card.pack_start(temp_header, False, False, 0)
        temp_card.pack_start(self.temp_graph, True, True, 0)
        self.pack_start(temp_card, True, True, 0)

        # Fan RPM history graph
        rpm_lines = [{'color': CPU_COLOR, 'label': 'CPU', 'dashed': True}]
        if model.has_gpu:
            rpm_lines.append({'color': GPU_COLOR, 'label': 'GPU', 'dashed': True})
        self.rpm_graph = RollingGraph(
            lines=rpm_lines, y_min=0, y_max=6000, y_label=""
        )
        rpm_card = make_card()
        rpm_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        rpm_header.pack_start(make_label("Fan Speed History", size=12, bold=True), False, False, 0)
        rpm_header.pack_end(make_label("Last 60 seconds", color="#666666", size=10), False, False, 0)
        rpm_card.pack_start(rpm_header, False, False, 0)
        rpm_card.pack_start(self.rpm_graph, True, True, 0)
        self.pack_start(rpm_card, True, True, 0)

    def update(self, ec):
        """Called every 500ms to read EC and update displays."""
        cpu_temp = safe_read_byte(ec, self.model.cpu_temp_addr)
        cpu_rpm = safe_read_rpm(ec, self.model, self.model.cpu_fan_rpm_addr)

        self.cpu_card.update(cpu_temp, cpu_rpm)
        self.temp_graph.add_point(0, cpu_temp)
        self.rpm_graph.add_point(0, cpu_rpm)

        if self.model.has_gpu and self.gpu_card:
            gpu_temp = safe_read_byte(ec, self.model.gpu_temp_addr)
            gpu_rpm = safe_read_rpm(ec, self.model, self.model.gpu_fan_rpm_addr)
            self.gpu_card.update(gpu_temp, gpu_rpm)
            self.temp_graph.add_point(1, gpu_temp)
            self.rpm_graph.add_point(1, gpu_rpm)

        self.temp_graph.queue_draw()
        self.rpm_graph.queue_draw()
