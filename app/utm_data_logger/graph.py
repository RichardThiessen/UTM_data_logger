"""
Graph widget for UTM data logger.
Simple line plot using Tkinter Canvas.
"""

import logging

try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

logger = logging.getLogger(__name__)


class GraphCanvas(tk.Canvas):
    """
    Canvas widget for plotting test data.

    Features:
    - Auto-scaling X and Y axes
    - Axis labels with tick marks
    - Grid lines
    - Smooth line rendering
    """

    # Layout constants
    MARGIN_LEFT = 60
    MARGIN_RIGHT = 20
    MARGIN_TOP = 20
    MARGIN_BOTTOM = 40

    # Colors
    COLOR_BG = '#ffffff'
    COLOR_AXIS = '#000000'
    COLOR_GRID = '#e0e0e0'
    COLOR_LINE = '#2060c0'
    COLOR_TEXT = '#000000'

    # Axis tick count targets
    TARGET_X_TICKS = 6
    TARGET_Y_TICKS = 5

    def __init__(self, parent, **kwargs):
        kwargs.setdefault('bg', self.COLOR_BG)
        kwargs.setdefault('highlightthickness', 0)
        tk.Canvas.__init__(self, parent, **kwargs)

        self._values = []
        self._timestamps = []
        self._x_min = 0.0
        self._x_max = 1.0
        self._y_min = 0.0
        self._y_max = 1.0

        self.bind('<Configure>', self._on_resize)

    def set_data(self, values, timestamps, x_scale_hint=None):
        """
        Set the data to plot.

        Args:
            values: list of Y values
            timestamps: list of X values (timestamps)
            x_scale_hint: optional minimum X range (e.g., previous test duration)
        """
        self._values = list(values) if values else []
        self._timestamps = list(timestamps) if timestamps else []

        if self._timestamps:
            t0 = self._timestamps[0]
            self._timestamps = [t - t0 for t in self._timestamps]
            logger.debug("set_data: %d points, t_range=[0, %.3f], hint=%.3f",
                         len(self._values),
                         self._timestamps[-1] if self._timestamps else 0,
                         x_scale_hint or 0)

        self._calculate_bounds(x_scale_hint)
        self._redraw()

    def clear(self):
        """Clear the graph."""
        self._values = []
        self._timestamps = []
        self._x_min = 0.0
        self._x_max = 1.0
        self._y_min = 0.0
        self._y_max = 1.0
        self._redraw()

    def _calculate_bounds(self, x_scale_hint):
        """Calculate axis bounds from data."""
        if not self._values:
            self._x_min = 0.0
            self._x_max = max(1.0, x_scale_hint or 1.0)
            self._y_min = 0.0
            self._y_max = 1.0
            return

        # X bounds (time)
        self._x_min = 0.0
        self._x_max = max(self._timestamps) if self._timestamps else 1.0
        if x_scale_hint and x_scale_hint > self._x_max:
            self._x_max = x_scale_hint
        if self._x_max <= self._x_min:
            self._x_max = self._x_min + 1.0

        # Y bounds (values)
        self._y_min = min(min(self._values),0) #always include zero
        self._y_max = max(self._values)

        # Add some padding to Y
        y_range = self._y_max - self._y_min
        if y_range < 0.001:
            y_range = 1.0
        padding = y_range * 0.05
        self._y_min -= padding
        self._y_max += padding

        logger.debug("bounds: x=[%.3f, %.3f], y=[%.3f, %.3f]",
                     self._x_min, self._x_max, self._y_min, self._y_max)

    def _on_resize(self, event):
        """Handle canvas resize."""
        self._redraw()

    def _redraw(self):
        """Redraw the entire graph."""
        self.delete('all')

        width = self.winfo_width()
        height = self.winfo_height()

        if width < 100 or height < 100:
            return

        plot_left = self.MARGIN_LEFT
        plot_right = width - self.MARGIN_RIGHT
        plot_top = self.MARGIN_TOP
        plot_bottom = height - self.MARGIN_BOTTOM
        plot_width = plot_right - plot_left
        plot_height = plot_bottom - plot_top

        if plot_width < 10 or plot_height < 10:
            return

        # Draw grid and axes
        self._draw_grid(plot_left, plot_top, plot_right, plot_bottom)
        self._draw_axes(plot_left, plot_top, plot_right, plot_bottom)

        # Draw data
        if self._values and self._timestamps:
            self._draw_line(plot_left, plot_top, plot_width, plot_height)

    def _draw_grid(self, left, top, right, bottom):
        """Draw grid lines."""
        # Vertical grid lines (X axis)
        x_ticks = self._nice_ticks(self._x_min, self._x_max, self.TARGET_X_TICKS)
        for x_val in x_ticks:
            x = self._map_x(x_val, left, right)
            self.create_line(x, top, x, bottom, fill=self.COLOR_GRID)

        # Horizontal grid lines (Y axis)
        y_ticks = self._nice_ticks(self._y_min, self._y_max, self.TARGET_Y_TICKS)
        for y_val in y_ticks:
            y = self._map_y(y_val, top, bottom)
            self.create_line(left, y, right, y, fill=self.COLOR_GRID)

    def _draw_axes(self, left, top, right, bottom):
        """Draw axis lines and labels."""
        # Axis lines
        self.create_line(left, bottom, right, bottom, fill=self.COLOR_AXIS, width=2)
        self.create_line(left, top, left, bottom, fill=self.COLOR_AXIS, width=2)

        # X axis labels
        x_ticks = self._nice_ticks(self._x_min, self._x_max, self.TARGET_X_TICKS)
        for x_val in x_ticks:
            x = self._map_x(x_val, left, right)
            label = self._format_number(x_val)
            self.create_text(x, bottom + 5, text=label, anchor='n',
                           fill=self.COLOR_TEXT, font=('TkDefaultFont', 8))

        # X axis title
        self.create_text((left + right) / 2, bottom + 25, text='Time (s)',
                        anchor='n', fill=self.COLOR_TEXT)

        # Y axis labels
        y_ticks = self._nice_ticks(self._y_min, self._y_max, self.TARGET_Y_TICKS)
        for y_val in y_ticks:
            y = self._map_y(y_val, top, bottom)
            label = self._format_number(y_val)
            self.create_text(left - 5, y, text=label, anchor='e',
                           fill=self.COLOR_TEXT, font=('TkDefaultFont', 8))

        # Y axis title
        self.create_text(15, (top + bottom) / 2, text='Load',
                        anchor='center', fill=self.COLOR_TEXT, angle=90)

    def _draw_line(self, left, top, width, height):
        """Draw the data line."""
        if len(self._values) < 2:
            # Single point - draw a dot
            if self._values:
                x = self._map_x(self._timestamps[0], left, left + width)
                y = self._map_y(self._values[0], top, top + height)
                self.create_oval(x - 3, y - 3, x + 3, y + 3,
                               fill=self.COLOR_LINE, outline=self.COLOR_LINE)
            return

        # Build list of coordinates
        coords = []
        for i in range(len(self._values)):
            x = self._map_x(self._timestamps[i], left, left + width)
            y = self._map_y(self._values[i], top, top + height)
            coords.extend([x, y])

        self.create_line(*coords, fill=self.COLOR_LINE, width=2, smooth=False)

    def _map_x(self, value, left, right):
        """Map X value to canvas coordinate."""
        if self._x_max == self._x_min:
            return (left + right) / 2
        ratio = (value - self._x_min) / (self._x_max - self._x_min)
        return left + ratio * (right - left)

    def _map_y(self, value, top, bottom):
        """Map Y value to canvas coordinate (note: Y is inverted)."""
        if self._y_max == self._y_min:
            return (top + bottom) / 2
        ratio = (value - self._y_min) / (self._y_max - self._y_min)
        return bottom - ratio * (bottom - top)

    def _nice_ticks(self, min_val, max_val, target_count):
        """Generate nice tick values for an axis."""
        if max_val <= min_val:
            return [min_val]

        range_val = max_val - min_val
        rough_step = range_val / target_count

        # Find a nice step size
        import math
        magnitude = math.pow(10, math.floor(math.log10(rough_step)))
        residual = rough_step / magnitude

        if residual <= 1.5:
            nice_step = magnitude
        elif residual <= 3:
            nice_step = 2 * magnitude
        elif residual <= 7:
            nice_step = 5 * magnitude
        else:
            nice_step = 10 * magnitude

        # Generate ticks
        ticks = []
        tick = math.ceil(min_val / nice_step) * nice_step
        while tick <= max_val:
            ticks.append(tick)
            tick += nice_step

        return ticks

    def _format_number(self, value):
        """Format a number for axis label."""
        if abs(value) < 0.01 and value != 0:
            return '{:.2e}'.format(value)
        elif abs(value) >= 1000:
            return '{:.0f}'.format(value)
        elif abs(value) >= 100:
            return '{:.1f}'.format(value)
        elif abs(value) >= 1:
            return '{:.2f}'.format(value)
        else:
            return '{:.3f}'.format(value)
