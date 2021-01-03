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
from concurrent.futures import ThreadPoolExecutor

__author__ = 'Ole Martin Bjorndalen'
__email__ = 'ombdalen@gmail.com'
__license__ = 'MIT'
__url__ = 'http://github.com/olemb/launchbox/'


def get_commands():
    """Get a sorted list of all commands available to the shell."""
    commands = set()

    for dirname in map(Path, set(os.environ['PATH'].split(':'))):
        if not dirname.is_dir():
            continue

        for command in dirname.iterdir():
            if command.is_file() and os.access(command, os.X_OK):
                commands.add(str(command.name))

    return sorted(commands)


class Completer:
    """Tab completer."""
    def __init__(self, commands):
        self.prefix = ''
        self.commands = commands
        self.matches = commands
        self.index = None

    def set_prefix(self, prefix):
        self.prefix = prefix
        self.matches = [
            command for command in self.commands
            if command.startswith(prefix)
        ] or [prefix]
        self.index = None

    def next(self):
        if self.index is None:
            self.index = 0
        else:
            self.index = (self.index + 1) % len(self.matches)
        return self.matches[self.index]

    def prev(self):
        if self.index is None:
            self.index = -1
        else:
            self.index = (self.index - 1) % len(self.matches)
        return self.matches[self.index]


class Launcher:
    def __init__(self):
        # Run this is the background so we can collect commands
        # and initialize Tk at the same time.
        executor = ThreadPoolExecutor(max_workers=1)
        self.commands_future = executor.submit(get_commands)
        # The completer will be created at the first keypress.
        self.completer = None

        window = tkinter.Tk(className='launchbox')
        window.configure(background='black')
        entry = tkinter.Entry(window)
        entry.pack(padx=8, pady=8)
        entry.configure(background='black', foreground='#bbb')

        font = tkinter.font.nametofont(entry['font'])
        font.config(size=40)

        window.bind('<Escape>', lambda _: self.window.quit())
        window.bind('<Return>', lambda _: self.run())
        window.bind('<Key>', self.handle_key)

        window.eval('tk::PlaceWindow . center')
        entry.focus_force()

        self.window = window
        self.entry = entry

    def main(self):
        self.window.mainloop()

    def run(self):
        command = self.get_text()
        if command:
            os.system(f'{command}&')
            self.window.quit()

    def handle_key(self, event):
        if self.completer is None:
            commands = self.commands_future.result()
            self.completer = Completer(commands)

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
        self.entry.delete(0, tkinter.END)
        self.entry.insert(0, text)
        self.entry.select_range(len(self.completer.prefix), tkinter.END)

    def get_text(self):
        return self.entry.get().strip()


def main():
    Launcher().main()


if __name__ == '__main__':
    sys.exit(main())
