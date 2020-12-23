#!/usr/bin/env python
"""
Launchbox - Command launcher with tab completion and full shell commands.

Keys:

    tab             - cycle through tab completions
    shift-tab       - cycle backwards
    shift-backspace - delete all text
    ctrl-backspace  - delete word for word (Gtk only)
    enter           - run command
    escape          - close window

Launchbox will use the shell found in $SHELL or default to
/bin/sh. It uses the shell to get available commands (found by run
the shell and having it echo its $PATH) and to run the command (which
can be a full command line).
"""
import os
import sys
from pathlib import Path
from argparse import ArgumentParser, RawTextHelpFormatter

__author__ = 'Ole Martin Bjorndalen'
__email__ = 'ombdalen@gmail.com'
__license__ = 'MIT'
__url__ = 'http://github.com/olemb/launchbox/'

SHELL = os.environ.get('SHELL', '/bin/sh')


def iter_path():
    command = f"{SHELL} -c 'echo $PATH'"
    with os.popen(command) as pipe:
        for dirname in pipe.read().strip().split(':'):
            yield Path(dirname).expanduser()


def get_commands():
    """Get a sorted list of all commands available to the shell."""
    commands = set()

    for dirname in iter_path():
        if not dirname.is_dir():
            continue

        for command in dirname.iterdir():
            if command.is_file() and os.access(command, os.X_OK):
                commands.add(command)

    return sorted(commands)


def run_command(command):
    """Run a command line in the shell."""
    os.system('(echo {} | {})&'.format(command, SHELL))


class Completer(object):
    """Tab completer."""
    def __init__(self):
        self.commands = None
        self.current = -1
        self._prefix = ''

    def set_prefix(self, prefix):
        if prefix != self._prefix:
            self.commands = None
            self.current = -1
            self._prefix = prefix

    def _cycle(self, step):
        if self.commands is None:
            self.commands = [
                command for command in get_commands()
                if command.startswith(self._prefix)
            ]
            self.current = -1

        if len(self.commands) == 0:
            return self._prefix
        else:
            self.current += step
            self.current %= len(self.commands)
            return self.commands[self.current]

    def next(self):
        return self._cycle(1)

    def prev(self):
        return self._cycle(-1)


def center_window(root):
    # From https://bbs.archlinux.org/viewtopic.php?pid=1166787

    # Apparently a common hack to get the window size. Temporarily hide the
    # window to avoid update_idletasks() drawing the window in the wrong
    # position.
    root.withdraw()
    root.update_idletasks()  # Update "requested size" from geometry manager

    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) // 2
    root.geometry(f'+{x}+{y}')

    # This seems to draw the window frame immediately, so only call deiconify()
    # after setting correct window position
    root.deiconify()


def import_tk():
    """Return (tkinter, tkinter.font)"""
    if sys.version_info.major == 2:
        import Tkinter
        import tkFont
        return (Tkinter, tkFont)
    else:
        import tkinter
        import tkinter.font
        return (tkinter, tkinter.font)


class LauncherTk(object):
    def __init__(self):
        self.tk, self.tkfont = import_tk()

        root = self.tk.Tk(className='launchbox')
        root.configure(background='black')
        entry = self.tk.Entry(root)
        entry.pack(padx=8, pady=8)
        entry.configure(background='black', foreground='#bbb')

        font = self.tkfont.nametofont(entry['font'])
        font.config(size=40)

        root.bind('<Escape>', lambda _: self.window.quit())
        root.bind('<Return>', lambda _: self.run())
        root.bind('<Key>', self.handle_key)

        entry.focus_force()
        center_window(root)

        self.window = root
        self.entry = entry
        self.completer = Completer()

    def main(self):
        self.window.mainloop()

    def run(self):
        command = self.entry.get().strip()
        if command:
            run_command(command)
            self.window.quit()

    def handle_key(self, event):
        # event state values.
        SHIFT = 1
        # CTRL = 4

        key = event.keysym
        mod = event.state

        if key in {'Tab', 'ISO_Left_Tab'}:
            if mod == SHIFT:
                self.set_text(self.completer.prev())
            else:
                self.set_text(self.completer.next())
            return 'break'
        elif key == 'BackSpace' and mod == SHIFT:
            # Clear text.
            self.set_text('')
            self.completer.set_prefix('')
            return 'break'
        elif event.char != '':
            # Any other visible or control character.
            self.completer.set_prefix(self.get_text())

    def set_text(self, text):
        # http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/entry.html
        self.entry.delete(0, self.tk.END)
        self.entry.insert(0, text)
        self.entry.select_range(self.tk.END, self.tk.END)

    def get_text(self):
        return self.entry.get().strip()


class LauncherGtk2(object):
    def __init__(self):
        import pygtk
        pygtk.require('2.0')
        import gtk
        import pango

        self.gtk = gtk

        self.gtk.gdk.set_program_class('launchbox')

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.connect('delete_event', self.on_delete_event)
        self.window.connect('destroy', self.on_destroy)
        self.window.padding = 10

        self.alignment = gtk.Alignment()
        self.alignment.set_padding(10, 10, 10, 10)
        self.window.add(self.alignment)

        self.entry = gtk.Entry()
        self.entry.set_width_chars(24)
        self.entry.modify_font(pango.FontDescription('40'))
        self.alignment.add(self.entry)
        # self.window.set_focus(self.entry)

        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.show_all()
        self.window.window.focus()

        self.completer = Completer()

        self.window.add_events(gtk.gdk.KEY_PRESS_MASK)
        self.entry.connect('key-press-event', self.on_key_press_event)
        self.entry.connect('key-release-event', self.on_key_release_event)

    def set_text(self, text):
        self.entry.set_text(text)

    def get_text(self):
        return self.entry.get_text()

    def shift_held(self, event):
        return event.state & self.gtk.gdk.SHIFT_MASK

    def ctrl_held(self, event):
        return event.state & self.gtk.gdk.CONTROL_MASK

    def on_key_press_event(self, window, event):
        key = self.gtk.gdk.keyval_name(event.keyval)
        if key in ['Tab', 'ISO_Left_Tab']:
            if self.shift_held(event):
                text = self.completer.prev()
            else:
                text = self.completer.next()
            self.set_text(text)
            self.entry.set_position(len(text))
            return True
        elif key == 'Escape':
            self.quit()
        elif key == 'BackSpace' and self.shift_held(event):
            self.set_text('')
            self.completer.set_prefix('')
            return True
        elif key == 'Return':
            command = self.get_text()
            if command:
                run_command(command)
                self.quit()

    def on_key_release_event(self, window, event):
        key = self.gtk.gdk.keyval_name(event.keyval)
        if len(key) == 1 or key in ['BackSpace', 'Delete']:
            self.completer.set_text(self.get_text())

    def on_delete_event(self, widget, event, data=None):
        return False

    def on_destroy(self, widget, data=None):
        self.quit()

    def quit(self):
        self.gtk.main_quit()

    def main(self):
        self.gtk.main()


def parse_args():
    parser = ArgumentParser(
        description=__doc__,
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        '--gtk2',
        dest='gtk2',
        action='store_true',
        default=False,
        help='use Gtk 2 window. The default is Tkinter.',
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.gtk2:
        Class = LauncherGtk2
    else:
        Class = LauncherTk

    Class().main()


if __name__ == '__main__':
    sys.exit(main())
