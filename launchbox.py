#!/usr/bin/env python
"""
Launchbox - Command launcher with tab completion and full shell commands.

Keys:

    tab             - cycle through tab completions
    shift-tab       - cycle backwards
    shift-backspace - delete all text
    enter           - run command
    escape          - close window

Launchbox will use the shell found in $SHELL or default to
/bin/bash. It uses the shell to get available commands (found by run
the shell and having it echo its $PATH) and to run the command (which
can be a full command line).
"""
from __future__ import print_function
import os
import sys
from Tkinter import *
import tkFont

__author__ = 'Ole Martin Bjorndalen'
__email__ = 'ombdalen@gmail.com'
__license__ = 'MIT'
__version__ = '1.0.0'
__url__ = 'http://github.com/olemb/launchbox/'

SHELL = os.environ.get('SHELL', '/bin/bash')


def get_path():
    command = "{} -c 'echo $PATH'".format(SHELL)
    path = os.popen(command).read().strip().split(':')
    path = [os.path.expanduser(dirname) for dirname in path]

    return path


def get_commands():
    """Get a sorted list of all commands available to the shell."""
    commands = set()

    for dirname in get_path():
        if os.path.isdir(dirname):
            for command in os.listdir(dirname):
                filename = os.path.join(dirname, command)
                if not os.path.isdir(filename):
                    if os.access(filename, os.X_OK):
                        commands.add(command)

    commands = list(set(commands))
    commands.sort()

    return commands


def run_command(command):
    """Run a command line in the shell."""
    os.system('(echo {} | {})&'.format(command, SHELL))



class Completer(object):
    """Tab completer."""
    def __init__(self):
        self.start = ''
        self.commands = []
        self.current = -1

    def update(self, text):
        """Update tab completion starting string.

        text is a string which will be stripped and used
        as a starting point for tab completion."""
        start = text.strip()
        if start != self.start:
            self.start = start
            self.commands = [c for c in get_commands() \
                             if c.startswith(self.start)]
            self.current = -1
            self._needs_get_commands = True

    def next(self, reverse=False):
        """Return the next command that starts with self.start.

        Calling this repeatedly will cycle through all matching
        commands. If reverse=True is passed it will instead return the
        previous command."""
        if len(self.commands) == 0:
            self.current = -1
            return ''
        else:
            if reverse:
                self.current -= 1
            else:
                self.current += 1
            self.current %= len(self.commands)

            return self.commands[self.current]


def center_window(root):
    # From https://bbs.archlinux.org/viewtopic.php?pid=1166787

    # Apparently a common hack to get the window size. Temporarily hide the
    # window to avoid update_idletasks() drawing the window in the wrong
    # position.
    root.withdraw()
    root.update_idletasks()  # Update "requested size" from geometry manager

    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) / 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) / 2
    root.geometry('+%d+%d' % (x, y))

    # This seems to draw the window frame immediately, so only call deiconify()
    # after setting correct window position
    root.deiconify()


class Launcher(object):
    def __init__(self):
        root = Tk(className='launchbox')
        entry = Entry(root)
        entry.pack(padx=10, pady=10)

        font = tkFont.nametofont(entry['font'])
        font.config(size=40)

        root.bind('<Escape>', lambda _: self.window.quit())
        root.bind('<Return>', lambda _: self.run())
        root.bind('<Key>', self.handle_key)

        entry.focus_force()
        center_window(root)

        self.window = root
        self.entry = entry
        self.completer = Completer()

    def get_text(self):
        return self.entry.get().strip()

    def mainloop(self):
        self.window.mainloop()

    def run(self):
        command = self.entry.get().strip()
        if command:
            run_command(command)
            self.window.quit()

    def handle_key(self, event):
        # event.state == 0 for no modifiers
        # event.state == 1 for shift

        # Delete text with shift-backspace.
        if (event.keysym, event.state) == ('Tab', 0):
            self.handle_tab()
            return 'break'
        elif event.keysym in ('Tab', 'ISO_Left_Tab') and event.state == 1:
            # I don't know why this is suddenly ISO_Left_Tab when you
            # hold down space.
            self.handle_tab(reverse=True)
            return 'break'
        elif (event.keysym, event.state) == ('BackSpace', 1):
            self.entry.delete(0, END)
            self.completer.update(self.entry.get())
            return 'break'
        elif event.char != '':
            self.completer.update(self.entry.get())

    def handle_tab(self, reverse=False):
        # http://infohost.nmt.edu/tcc/help/pubs/tkinter/web/entry.html
        if self.completer.commands:
            text = self.completer.next(reverse=reverse) + ' '
        else:
            text = self.entry.get().strip()

        self.entry.delete(0, END)
        self.entry.insert(0, text)
        self.entry.select_range(END, END)


if __name__ == '__main__':
    if '-h' in sys.argv[1:] or '--help' in sys.argv[1:]:
        print(__doc__)
    else:
        Launcher().mainloop()
