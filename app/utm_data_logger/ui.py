# SPDX-License-Identifier: MIT
"""
Main UI for UTM data logger.
Tkinter-based interface with test list and graph.
"""

import logging
import os

try:
    import tkinter as tk
    from tkinter import ttk
    from tkinter import messagebox
except ImportError:
    import Tkinter as tk
    import tkMessageBox as messagebox
    import ttk

from .models import Test

logger = logging.getLogger(__name__)

from .graph import GraphCanvas
from .settings import load_settings, save_settings, list_serial_ports, BAUDRATES, EXPORT_COLUMNS


class SettingsDialog(tk.Toplevel):
    """Settings dialog for COM port and baudrate."""

    def __init__(self, parent, current_settings):
        tk.Toplevel.__init__(self, parent)
        self.title('Settings')
        self.transient(parent)
        self.grab_set()

        self.result = None
        self._create_widgets(current_settings)

        # Center on parent
        self.geometry('+{}+{}'.format(
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        self.wait_window(self)

    def _create_widgets(self, current):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill='both', expand=True)

        # COM port
        ttk.Label(frame, text='COM Port:').grid(row=0, column=0, sticky='e', pady=5)
        self._port_var = tk.StringVar(value=current.get('port', ''))
        self._port_combo = ttk.Combobox(frame, textvariable=self._port_var, width=20)
        self._port_combo.grid(row=0, column=1, sticky='w', pady=5, padx=(5, 0))

        # Refresh button
        ttk.Button(frame, text='Refresh', command=self._refresh_ports).grid(
            row=0, column=2, padx=5)

        # Baudrate
        ttk.Label(frame, text='Baudrate:').grid(row=1, column=0, sticky='e', pady=5)
        self._baud_var = tk.StringVar(value=current.get('baudrate', '9600'))
        self._baud_combo = ttk.Combobox(frame, textvariable=self._baud_var,
                                        values=BAUDRATES, width=20)
        self._baud_combo.grid(row=1, column=1, sticky='w', pady=5, padx=(5, 0))

        # Auto-reconnect checkbox
        self._auto_reconnect_var = tk.BooleanVar(value=current.get('auto_reconnect', True))
        ttk.Checkbutton(frame, text='Auto-reconnect',
                        variable=self._auto_reconnect_var).grid(
            row=2, column=0, columnspan=3, sticky='w', pady=(5, 0))

        # Export section separator
        ttk.Separator(frame, orient='horizontal').grid(
            row=3, column=0, columnspan=3, sticky='ew', pady=(15, 10))
        ttk.Label(frame, text='Export Settings', font=('TkDefaultFont', 9, 'bold')).grid(
            row=4, column=0, columnspan=3, sticky='w')

        # Export columns format string
        ttk.Label(frame, text='Columns:').grid(row=5, column=0, sticky='e', pady=5)
        self._export_columns_var = tk.StringVar(value=current.get('export_columns', 'mean,peak,low,stdev'))
        columns_entry = ttk.Entry(frame, textvariable=self._export_columns_var, width=25)
        columns_entry.grid(row=5, column=1, columnspan=2, sticky='w', pady=5, padx=(5, 0))

        # Available columns hint
        available = ', '.join(sorted(EXPORT_COLUMNS.keys()))
        ttk.Label(frame, text='Available: {}'.format(available),
                  font=('TkDefaultFont', 8)).grid(
            row=6, column=1, columnspan=2, sticky='w', padx=(5, 0))

        # Export checkboxes
        self._export_headers_var = tk.BooleanVar(value=current.get('export_headers', True))
        ttk.Checkbutton(frame, text='Include column headers',
                        variable=self._export_headers_var).grid(
            row=7, column=0, columnspan=3, sticky='w', pady=(5, 0))

        self._export_datapoints_var = tk.BooleanVar(value=current.get('export_datapoints', False))
        ttk.Checkbutton(frame, text='Include all datapoints as columns',
                        variable=self._export_datapoints_var).grid(
            row=8, column=0, columnspan=3, sticky='w')

        self._export_transpose_var = tk.BooleanVar(value=current.get('export_transpose', False))
        ttk.Checkbutton(frame, text='Transpose output (tests as columns)',
                        variable=self._export_transpose_var).grid(
            row=9, column=0, columnspan=3, sticky='w')

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=10, column=0, columnspan=3, pady=(15, 0))

        ttk.Button(btn_frame, text='OK', command=self._on_ok).pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Cancel', command=self._on_cancel).pack(side='left', padx=5)

        # Initial port list
        self._refresh_ports()

    def _refresh_ports(self):
        ports = list_serial_ports()
        self._port_combo['values'] = ports
        # Keep current selection if still valid
        if self._port_var.get() not in ports and ports:
            self._port_var.set(ports[0])

    def _on_ok(self):
        self.result = {
            'port': self._port_var.get(),
            'baudrate': self._baud_var.get(),
            'auto_reconnect': self._auto_reconnect_var.get(),
            'export_columns': self._export_columns_var.get(),
            'export_datapoints': self._export_datapoints_var.get(),
            'export_transpose': self._export_transpose_var.get(),
            'export_headers': self._export_headers_var.get(),
        }
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


class UTMLoggerApp(tk.Tk):
    """Main application window."""

    UPDATE_INTERVAL_MS = 100  # UI refresh rate
    RECONNECT_INTERVAL_MS = 1000  # Auto-reconnect interval

    def __init__(self, session, socket_path=None):
        tk.Tk.__init__(self)

        self.title('UTM Data Logger')
        self.geometry('900x600')

        # Set application icon
        self._set_icon()

        self._session = session
        self._socket_path = socket_path
        self._settings = load_settings()

        # UI state - shadow copies
        self._shadow_tests = []      # Test objects matching listbox contents
        self._selected_tests = []    # Currently selected Test objects
        self._active_test = None     # In-progress test being monitored

        self._last_test_duration = 1.0  # For X scale hint
        self._reconnect_scheduled = False  # Track if reconnect timer is pending

        self._create_menu()
        self._create_widgets()
        self._bind_events()

        # Connect to data source
        self._connect()

        # Start update loop
        self._schedule_update()

    def _set_icon(self):
        """Set the application icon."""
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if not os.path.exists(icon_path):
            logger.warning("Icon file not found: %s", icon_path)
            return
        try:
            icon = tk.PhotoImage(file=icon_path)
            # Try modern iconphoto first, fall back to wm_iconphoto for older Tk
            if hasattr(self, 'iconphoto'):
                self.iconphoto(True, icon)
            else:
                self.tk.call('wm', 'iconphoto', self._w, icon)
            self._icon = icon  # Keep reference to prevent garbage collection
        except tk.TclError as e:
            logger.error("Failed to load icon: %s", e)
        except Exception as e:
            logger.error("Unexpected error loading icon: %s: %s", type(e).__name__, e)

    def _connect(self):
        """Connect to data source (serial port or socket)."""
        if self._socket_path:
            self._session.connect(socket=self._socket_path)
        else:
            port = self._settings.get('port', '')
            baudrate = int(self._settings.get('baudrate', '9600'))
            if port:
                self._session.connect(serial=(port, baudrate))

    def shutdown(self):
        """Clean up resources before exit."""
        self._session.disconnect()

    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='File', menu=file_menu)
        file_menu.add_command(label='Settings...', command=self._show_settings)
        file_menu.add_separator()
        file_menu.add_command(label='Exit', command=self.quit)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label='Edit', menu=edit_menu)
        edit_menu.add_command(label='Copy', command=self._copy_selected,
                             accelerator='Ctrl+C')
        edit_menu.add_command(label='Select All', command=self._select_all,
                             accelerator='Ctrl+A')
        edit_menu.add_separator()
        edit_menu.add_command(label='Delete', command=self._delete_selected,
                             accelerator='Delete')
        edit_menu.add_command(label='Delete All', command=self._delete_all)

    def _create_widgets(self):
        """Create main UI widgets."""
        # Main paned window
        paned = ttk.PanedWindow(self, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=5, pady=5)

        # Left frame - test list
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text='Tests').pack(anchor='w')

        # Listbox with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')

        self._listbox = tk.Listbox(list_frame, selectmode='extended',
                                   yscrollcommand=scrollbar.set,
                                   font=('TkFixedFont', 9))
        self._listbox.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self._listbox.yview)

        # Right frame - graph
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=3)

        ttk.Label(right_frame, text='Graph').pack(anchor='w')

        self._graph = GraphCanvas(right_frame)
        self._graph.pack(fill='both', expand=True)

        # Status bar
        self._status_var = tk.StringVar(value='Not connected')
        status = ttk.Label(self, textvariable=self._status_var, relief='sunken')
        status.pack(fill='x', side='bottom')

    def _bind_events(self):
        """Bind keyboard and mouse events."""
        self._listbox.bind('<<ListboxSelect>>', self._on_selection_change)
        self.bind('<Control-c>', lambda e: self._copy_selected())
        self.bind('<Control-a>', lambda e: self._select_all())
        self.bind('<Delete>', lambda e: self._delete_selected())

    def _format_test(self, test, index):
        """Format test for display in listbox."""
        if test.status == Test.STATUS_ERROR:
            prefix = '[ERR] '
        elif test.status == Test.STATUS_IN_PROGRESS:
            prefix = '[...] '
        else:
            prefix = ''

        n = test.sample_count
        if n == 0:
            stats = 'no points'
        elif test.status == Test.STATUS_IN_PROGRESS:
            stats = '{} points'.format(n)
        else:
            mean_v = test.mean_value
            max_v = test.max_value
            min_v = test.min_value
            if mean_v is not None:
                stats = '{:.1f} / {:.1f} / {:.1f} ({})'.format(mean_v, max_v, min_v, n)
            else:
                stats = '{:.1f} - {:.1f} ({})'.format(max_v, min_v, n)

        return '{}Test {}: {}'.format(prefix, index, stats)

    def _schedule_update(self):
        """Schedule the next UI update."""
        self._update_ui()
        self.after(self.UPDATE_INTERVAL_MS, self._schedule_update)

    def _update_ui(self):
        """Update UI from current session state."""
        self._session.process_events()
        tests = self._session.tests

        # Check if list structure changed
        if self._shadow_tests != tests:
            self._sync_listbox(tests)
        else:
            self._refresh_listbox_text()

        # Find in-progress test
        in_progress = None
        for t in tests:
            if t.status == Test.STATUS_IN_PROGRESS:
                in_progress = t
                break

        # Auto-select new in-progress test
        if in_progress and in_progress is not self._active_test:
            self._active_test = in_progress
            self._select_tests([in_progress])

        # Capture duration hint and clear active test when it completes
        if self._active_test and self._active_test.status == Test.STATUS_COMPLETE:
            if self._active_test.estimated_duration:
                self._last_test_duration = self._active_test.estimated_duration

        if in_progress is None:#clear active test if nothing in progress now that update logic has finished
           self._active_test = None
           
        self._update_graph()
        self._update_status()

        # Auto-reconnect if enabled and disconnected
        self._check_auto_reconnect()

    def _check_auto_reconnect(self):
        """Schedule auto-reconnect if enabled and disconnected."""
        if self._socket_path:
            return  # Don't auto-reconnect in socket mode

        if self._session.is_connected:
            self._reconnect_scheduled = False
            return

        if not self._settings.get('auto_reconnect', True):
            return

        if not self._settings.get('port', ''):
            return  # No port configured

        if self._reconnect_scheduled:
            return  # Already scheduled

        self._reconnect_scheduled = True
        self.after(self.RECONNECT_INTERVAL_MS, self._try_reconnect)

    def _try_reconnect(self):
        """Attempt to reconnect to serial port."""
        self._reconnect_scheduled = False

        if self._session.is_connected:
            return

        if not self._settings.get('auto_reconnect', True):
            return

        port = self._settings.get('port', '')
        if port:
            baudrate = int(self._settings.get('baudrate', '9600'))
            self._session.connect(serial=(port, baudrate))

    def _sync_listbox(self, tests):
        """Full rebuild of listbox from test list."""
        # Clear listbox
        self._listbox.delete(0, 'end')

        # Rebuild
        for i, test in enumerate(tests):
            test.update()
            self._listbox.insert('end', self._format_test(test, i + 1))

        # Update shadow
        self._shadow_tests = list(tests)

        # Restore selection
        for i, test in enumerate(self._shadow_tests):
            if test in self._selected_tests:
                self._listbox.selection_set(i)

        # Clean up selected_tests to only include tests still in list
        self._selected_tests = [t for t in self._selected_tests if t in self._shadow_tests]

    def _refresh_listbox_text(self):
        """Update listbox text without rebuilding."""
        for i, test in enumerate(self._shadow_tests):
            if test.status == Test.STATUS_IN_PROGRESS:
                test.update()
            new_text = self._format_test(test, i + 1)
            if self._listbox.get(i) != new_text:
                # Update text in place
                self._listbox.delete(i)
                self._listbox.insert(i, new_text)
                # Restore selection if this item was selected
                if test in self._selected_tests:
                    self._listbox.selection_set(i)

    def _on_selection_change(self, event):
        """Handle listbox selection change."""
        indices = self._listbox.curselection()
        self._selected_tests = [self._shadow_tests[i] for i in indices if i < len(self._shadow_tests)]

        if self._selected_tests:
            self._update_graph()
        else:
            self._graph.clear()

    def _select_tests(self, tests):
        """Programmatically select tests in listbox."""
        self._listbox.selection_clear(0, 'end')
        self._selected_tests = []

        for test in tests:
            if test in self._shadow_tests:
                idx = self._shadow_tests.index(test)
                self._listbox.selection_set(idx)
                self._listbox.see(idx)
                self._selected_tests.append(test)

        if self._selected_tests:
            self._update_graph()

    def _update_graph(self):
        """Update graph with first selected test's data."""
        if not self._selected_tests:
            self._graph.clear()
            return

        test = self._selected_tests[0]
        values, timestamps = test.values, test.timestamps
        logger.debug("update_graph: %d points, duration_hint=%.3f",
                     len(values), self._last_test_duration)

        # Update duration hint from completed tests
        if test.status == Test.STATUS_COMPLETE and test.estimated_duration:
            self._last_test_duration = test.estimated_duration

        completed = test.status != Test.STATUS_IN_PROGRESS
        self._graph.set_data(values, timestamps, self._last_test_duration, completed=completed)

    def _update_status(self):
        """Update status bar."""
        if self._session.is_connected:
            if self._active_test:
                self._status_var.set('Recording: {} points'.format(
                    self._active_test.sample_count))
            else:
                self._status_var.set('Connected - waiting for data')
        else:
            if self._session.disconnect_reason:
                self._status_var.set('Disconnected: {}'.format(
                    self._session.disconnect_reason))
            elif self._settings.get('port', ''):
                self._status_var.set('Disconnected ({})'.format(self._settings['port']))
            else:
                self._status_var.set('Not configured - open Settings')

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self, self._settings)
        if dialog.result:
            old_settings = self._settings
            self._settings = dialog.result
            save_settings(self._settings)

            # Reconnect if settings changed and not in socket mode
            if not self._socket_path and self._settings != old_settings:
                self._session.disconnect()
                port = self._settings.get('port', '')
                baudrate = int(self._settings.get('baudrate', '9600'))
                if port:
                    self._session.connect(serial=(port, baudrate))

    def _copy_selected(self):
        """Copy selected tests' stats to clipboard."""
        if not self._selected_tests:
            return

        # Get export settings
        columns_str = self._settings.get('export_columns', 'mean,peak,low,stdev')
        export_datapoints = self._settings.get('export_datapoints', False)
        export_transpose = self._settings.get('export_transpose', False)
        export_headers = self._settings.get('export_headers', True)

        # Parse column names from settings
        column_names = [c.strip().lower() for c in columns_str.split(',') if c.strip()]

        # Find max number of datapoints if exporting them
        max_points = 0
        if export_datapoints:
            for test in self._selected_tests:
                if test.sample_count > max_points:
                    max_points = test.sample_count

        # Build rows as list of lists of strings
        rows = []

        # Header row
        if export_headers:
            header_row = []
            for col in column_names:
                if col in EXPORT_COLUMNS:
                    header_row.append(col.capitalize())
            if export_datapoints and max_points > 0:
                header_row.extend(['V{}'.format(i + 1) for i in range(max_points)])
            rows.append(header_row)

        # Data rows
        for test in self._selected_tests:
            if test.sample_count == 0:
                continue

            row = []
            for col in column_names:
                if col not in EXPORT_COLUMNS:
                    continue
                attr = EXPORT_COLUMNS[col]
                if attr == 'test':
                    idx = self._shadow_tests.index(test) + 1 if test in self._shadow_tests else 0
                    row.append(str(idx))
                elif attr == 'sample_count':
                    row.append(str(test.sample_count))
                else:
                    val = getattr(test, attr, None)
                    row.append('{:.4f}'.format(val) if val is not None else '')

            if export_datapoints and max_points > 0:
                values = ['{:.4f}'.format(v) for v in test.values]
                values.extend([''] * (max_points - len(values)))
                row.extend(values)

            rows.append(row)

        if not rows:
            return

        # Transpose if requested
        if export_transpose:
            # Pad rows to max length before transpose
            max_len = max(len(r) for r in rows)
            for r in rows:
                r.extend([''] * (max_len - len(r)))

            # Transpose
            rows = list(map(list, zip(*rows)))

            # Trim trailing empty strings from each row
            for r in rows:
                while r and r[-1] == '':
                    r.pop()

        # Join to text
        lines = ['\t'.join(row) for row in rows]
        text = '\n'.join(lines)

        self.clipboard_clear()
        self.clipboard_append(text)

    def _select_all(self):
        """Select all tests in list."""
        self._listbox.selection_set(0, 'end')
        self._selected_tests = list(self._shadow_tests)

    def _delete_selected(self):
        """Delete selected tests after confirmation."""
        if not self._selected_tests:
            return

        count = len(self._selected_tests)
        msg = 'Delete {} test{}?'.format(count, 's' if count > 1 else '')
        if not messagebox.askyesno('Confirm Delete', msg):
            return

        for test in self._selected_tests:
            self._session.delete_test(test)

        self._selected_tests = []
        self._graph.clear()

    def _delete_all(self):
        """Delete all tests after confirmation."""
        if not self._shadow_tests:
            return

        if not messagebox.askyesno('Confirm Delete All',
                                   'Delete all {} tests?'.format(len(self._shadow_tests))):
            return

        self._session.clear_all()
        self._selected_tests = []
        self._graph.clear()


def run_app(session, socket_path=None):
    """
    Run the application.

    Args:
        session: TestSession instance
        socket_path: Unix socket path for dev mode (None for serial mode)

    Returns:
        The app instance
    """
    app = UTMLoggerApp(session, socket_path)
    return app
