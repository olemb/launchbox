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
import tkinter
import tkinter.font
from pathlib import Path

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
                commands.add(str(command.name))

    return sorted(commands)


def run_command(command):
    """Run a command line in the shell."""
    os.system(f'(echo {command} | {SHELL})&')


class Completer:
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


class Launcher:
    def __init__(self):
        self.tk = tkinter

        root = self.tk.Tk(className='launchbox')
        root.configure(background='black')
        entry = self.tk.Entry(root)
        entry.pack(padx=8, pady=8)
        entry.configure(background='black', foreground='#bbb')

        font = tkinter.font.nametofont(entry['font'])
        font.config(size=40)

        root.bind('<Escape>', lambda _: self.window.quit())
        root.bind('<Return>', lambda _: self.run())
        root.bind('<Key>', self.handle_key)

        root.eval('tk::PlaceWindow . center')
        entry.focus_force()

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


def main():
    Launcher().main()


if __name__ == '__main__':
    sys.exit(main())
