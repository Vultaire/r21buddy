from __future__ import absolute_import

import os, sys, threading, time
from cStringIO import StringIO
import Tkinter, tkFileDialog, tkMessageBox
from r21buddy import oggpatch, r21buddy
from r21buddy.logger import ThreadQueueLogger

# Interval to poll stdout/stderr capture of r21buddy console code.
POLL_INTERVAL = 100  # milliseconds


def askdirectory(*args, **kwargs):
    """Workaround for Tkinter-related encoding oddities."""
    result = tkFileDialog.askdirectory(*args, **kwargs)
    if isinstance(result, unicode):
        result = eval(repr(result)[1:])
    return result


class CompositeControl(object):

    def configure(self, **kwargs):
        self.entry.configure(**kwargs)
        self.button.configure(**kwargs)

    def get(self):
        return self.entry.get()


class Directory(CompositeControl):

    def __init__(self, parent, label_text, default_text=None, save=False):
        self.frame = Tkinter.Frame(parent)
        self.frame.pack()
        self.label = Tkinter.Label(self.frame, text=label_text)
        self.str_var = Tkinter.StringVar()
        if default_text is not None:
            self.str_var.set(default_text)
        self.entry = Tkinter.Entry(self.frame, textvariable=self.str_var)
        self.button = Tkinter.Button(self.frame, text="Browse...",
                                     width=10, command=self.on_browse)
        self.save = save

    def on_browse(self):
        # Meh, no "Create Folder" button for this dialog??  And
        # creating directories via adding slashes is counterintuitive
        # to say the least.
        dialog_args = {"mustexist": True}
        initialdir = self.str_var.get()
        if len(initialdir) > 0:
            dialog_args["initialdir"] = initialdir
        path = askdirectory(**dialog_args)
        path = path.replace("/", os.sep)
        if len(path) > 0:
            self.str_var.set(path)

    def pack(self, *args, **kwargs):
        self.frame.pack(*args, **kwargs)
        self.label.pack(side=Tkinter.LEFT)
        self.entry.pack(side=Tkinter.LEFT, fill=Tkinter.X, expand=True)
        self.button.pack(side=Tkinter.LEFT)


class InputDirs(object):
    def __init__(self, parent):
        self.frame = Tkinter.Frame(parent)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.input_dirs = Tkinter.Listbox(
            self.frame, width=1, height=1, activestyle=Tkinter.NONE)
        self.input_dirs.grid(
            row=0, column=0,
            sticky=(Tkinter.N, Tkinter.E, Tkinter.S, Tkinter.W))
        self.yscroll = Tkinter.Scrollbar(self.frame)
        self.yscroll.grid(row=0, column=1, sticky=(Tkinter.N, Tkinter.S))
        self.xscroll = Tkinter.Scrollbar(self.frame, orient=Tkinter.HORIZONTAL)
        self.xscroll.grid(row=1, column=0, sticky=(Tkinter.W, Tkinter.E))
        self.input_dirs.configure(yscrollcommand=self.yscroll.set)
        self.input_dirs.configure(xscrollcommand=self.xscroll.set)
        self.yscroll.configure(command=self.input_dirs.yview)
        self.xscroll.configure(command=self.input_dirs.xview)

    def pack(self, *args, **kwargs):
        self.frame.pack(*args, **kwargs)

    def __getattr__(self, key):
        """Passthrough for most functions to the ListBox inside."""
        return getattr(self.input_dirs, key)


class MainWindow(object):
    def __init__(self):
        self.root = Tkinter.Tk()
        self.root.title("r21buddy: Automated StepMania-to-R21 Converter")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        main_frame = Tkinter.Frame(self.root, padx=5, pady=5)
        main_frame.pack(fill=Tkinter.BOTH, expand=True)

        control_frame = Tkinter.Frame(main_frame)
        control_frame.pack(anchor=Tkinter.W, fill=Tkinter.X)

        self.target_dir = Directory(control_frame, "Target directory:")
        self.target_dir.pack(anchor=Tkinter.W, fill=Tkinter.X)

        f = Tkinter.Frame(control_frame)
        f.pack(anchor=Tkinter.W, fill=Tkinter.X, expand=True)
        Tkinter.Label(f, text="Input directories:") \
            .pack(side=Tkinter.LEFT)
        self.add_btn = Tkinter.Button(
            f, text="Add...", command=self.on_inputdir_add, width=10)
        self.add_btn.pack(side=Tkinter.LEFT)
        self.last_dir = None  # For tracking the last input directory added

        inputdir_frame = Tkinter.LabelFrame(control_frame, text="Selected input directories")
        inputdir_frame.pack(anchor=Tkinter.W, fill=Tkinter.X, expand=True)

        # Create listbox w/ scrollbars
        self.input_dirs = InputDirs(inputdir_frame)
        self.input_dirs.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)

        # Create buttons to control listbox
        button_frame = Tkinter.Frame(inputdir_frame)
        button_frame.pack(side=Tkinter.LEFT, anchor=Tkinter.N)
        self.move_up_btn = Tkinter.Button(
            button_frame, text="Move Up", width=10, command=self.on_move_up)
        self.move_up_btn.pack()
        self.move_down_btn = Tkinter.Button(
            button_frame, text="Move Down", width=10, command=self.on_move_down)
        self.move_down_btn.pack()
        self.delete_btn = Tkinter.Button(
            button_frame, text="Delete", width=10, command=self.on_delete)
        self.delete_btn.pack()

        self.skip_ogg_patch = Tkinter.IntVar()
        self.skip_ogg_chk = Tkinter.Checkbutton(
            control_frame, text="Check length only; do not modify file",
            variable=self.skip_ogg_patch)
        self.skip_ogg_chk.pack(anchor=Tkinter.W)

        self.run_btn = Tkinter.Button(
            control_frame, text="Run", command=self.on_run, width=10)
        self.run_btn.pack()

        # Scrollable text area for log output
        log_frame = Tkinter.LabelFrame(main_frame, text="Log")
        log_frame.pack(fill=Tkinter.BOTH, expand=True)
        # Note: using really small width since we'll auto-expand.
        self.log_window = Tkinter.Text(log_frame, width=1, height=10, state=Tkinter.DISABLED)
        self.log_window.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        scroll = Tkinter.Scrollbar(log_frame)
        scroll.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)
        self.log_window.configure(yscrollcommand=scroll.set)
        scroll.configure(command=self.log_window.yview)

        self.toggle_control_set = (
            self.target_dir,
            self.add_btn,
            self.input_dirs,
            self.move_up_btn,
            self.move_down_btn,
            self.delete_btn,
            self.skip_ogg_chk,
            self.run_btn,
            )

    def disable(self):
        for control in self.toggle_control_set:
            control.configure(state=Tkinter.DISABLED)

    def enable(self):
        for control in self.toggle_control_set:
            control.configure(state=Tkinter.NORMAL)

    def mainloop(self):
        self.root.mainloop()

    def after(self, *args, **kwargs):
        self.root.after(*args, **kwargs)

    def on_inputdir_add(self):
        dialog_kwargs = {"mustexist": True}
        if self.last_dir is not None:
            dialog_kwargs["initialdir"] = self.last_dir
        path = askdirectory(**dialog_kwargs)
        path = path.replace("/", os.sep)
        if len(path) == 0:
            return
        self.last_dir = path
        if path in self.input_dirs.get(0, Tkinter.END):
            tkMessageBox.showinfo(
                title="Directory already queued",
                message="This directory is already in the queue.")
        else:
            self.input_dirs.insert(Tkinter.END, path)

    def on_move_up(self):
        input_indices = map(int, self.input_dirs.curselection())
        if len(input_indices) < 1:
            return
        i = input_indices[0]
        if i > 0:
            self.input_dirs.selection_clear(i)
            val = self.input_dirs.get(i)
            self.input_dirs.delete(i)
            self.input_dirs.insert(i-1, val)
            self.input_dirs.selection_set(i-1)
            self.input_dirs.see(i-1)

    def on_move_down(self):
        input_indices = map(int, self.input_dirs.curselection())
        if len(input_indices) < 1:
            return
        i = input_indices[0]
        if i < self.input_dirs.size() - 1:
            self.input_dirs.selection_clear(i)
            val = self.input_dirs.get(i)
            self.input_dirs.delete(i)
            self.input_dirs.insert(i+1, val)
            self.input_dirs.selection_set(i+1)
            self.input_dirs.see(i+1)

    def on_delete(self):
        input_indices = map(int, self.input_dirs.curselection())
        if len(input_indices) < 1:
            return
        i = input_indices[0]
        self.input_dirs.selection_clear(i)
        self.input_dirs.delete(i)

    def on_run(self):
        target_dir = self.target_dir.get().decode(sys.getfilesystemencoding())
        if len(target_dir) == 0:
            tkMessageBox.showinfo(title="No target directory",
                                  message="No target directory selected.")
            return
        input_paths = self.input_dirs.get(0, Tkinter.END)
        input_paths = [ip.decode(sys.getfilesystemencoding())
                       for ip in input_paths]
        no_length_patch = bool(self.skip_ogg_patch.get())

        # Disable GUI
        self.disable()

        logger = ThreadQueueLogger()

        # To avoid locking the GUI, run execution in another thread.
        thread = threading.Thread(
            target=r21buddy.run,
            args=(target_dir, input_paths),
            kwargs={"length_patch": (not no_length_patch), "verbose": True,
                    "ext_logger": logger})
        thread.start()

        # Initiate a polling function which will update until the
        # thread finishes.
        self._on_run(thread, logger)

    def _on_run(self, thread, logger):
        def append_log(msg):
            self.log_window.configure(state=Tkinter.NORMAL)
            self.log_window.insert(Tkinter.END, msg)
            self.log_window.see(Tkinter.END)
            self.log_window.configure(state=Tkinter.DISABLED)

        msg = logger.read()
        if len(msg) > 0:
            append_log(msg)
        if thread.is_alive():
            self.after(POLL_INTERVAL, self._on_run, thread, logger)
        else:
            msg = logger.read()
            if len(msg) > 0:
                append_log(msg)
            append_log("Operation complete.\n\n")
            self.enable()

    def log(self, msg, *tags):
        self.log_window.insert(Tkinter.INSERT, msg, *tags)

def main():
    root = MainWindow()
    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
