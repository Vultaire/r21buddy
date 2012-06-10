from __future__ import absolute_import

import os, sys
from cStringIO import StringIO
import Tkinter, tkFileDialog, tkMessageBox
from r21buddy import oggpatch, r21buddy


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
        path = tkFileDialog.askdirectory(mustexist=True)
        if len(path) > 0:
            self.str_var.set(path)

    def pack(self, *args, **kwargs):
        self.frame.pack(*args, **kwargs)
        self.label.pack(side=Tkinter.LEFT)
        self.entry.pack(side=Tkinter.LEFT, fill=Tkinter.X, expand=True)
        self.button.pack(side=Tkinter.LEFT)

    def configure(self, **kwargs):
        self.entry.configure(**kwargs)
        self.button.configure(**kwargs)


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
        Tkinter.Button(f, text="Add...", command=self.on_inputdir_add, width=10) \
            .pack(side=Tkinter.LEFT)

        inputdir_frame = Tkinter.LabelFrame(control_frame, text="Selected input directories")
        inputdir_frame.pack(anchor=Tkinter.W, fill=Tkinter.X, expand=True)

        # Create listbox w/ scrollbars
        listbox_grid = Tkinter.Frame(inputdir_frame, relief=Tkinter.GROOVE, borderwidth=2)
        listbox_grid.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        listbox_grid.rowconfigure(0, weight=1)
        listbox_grid.columnconfigure(0, weight=1)
        self.input_dirs = Tkinter.Listbox(
            listbox_grid, width=1, height=1, activestyle=Tkinter.NONE)
        self.input_dirs.grid(
            row=0, column=0,
            sticky=(Tkinter.N, Tkinter.E, Tkinter.S, Tkinter.W))
        yscroll = Tkinter.Scrollbar(listbox_grid)
        yscroll.grid(row=0, column=1, sticky=(Tkinter.N, Tkinter.S))
        xscroll = Tkinter.Scrollbar(listbox_grid, orient=Tkinter.HORIZONTAL)
        xscroll.grid(row=1, column=0, sticky=(Tkinter.W, Tkinter.E))
        self.input_dirs.configure(yscrollcommand=yscroll.set)
        self.input_dirs.configure(xscrollcommand=xscroll.set)
        yscroll.configure(command=self.input_dirs.yview)
        xscroll.configure(command=self.input_dirs.xview)

        # Create buttons to control listbox
        button_frame = Tkinter.Frame(inputdir_frame)
        button_frame.pack(side=Tkinter.LEFT, anchor=Tkinter.N)
        Tkinter.Button(button_frame, text="Move Up", width=10,
                       command=self.on_move_up).pack()
        Tkinter.Button(button_frame, text="Move Down", width=10,
                       command=self.on_move_down).pack()
        Tkinter.Button(button_frame, text="Delete", width=10,
                       command=self.on_delete).pack()

        self.skip_ogg_patch = Tkinter.IntVar()
        Tkinter.Checkbutton(
            control_frame, text="Check length only; do not modify file",
            variable=self.skip_ogg_patch).pack(anchor=Tkinter.W)

        Tkinter.Button(control_frame, text="Run", command=self.on_run, width=10).pack()

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

    def mainloop(self):
        self.root.mainloop()

    def on_inputdir_add(self):
        path = tkFileDialog.askdirectory(mustexist=True)
        if len(path) == 0:
            return
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
        target_dir = self.target_dir.get()
        if len(target_dir) == 0:
            tkMessageBox.showinfo(title="No target directory",
                                  message="No target directory selected.")
            return
        input_paths = self.input_dirs.get(0, Tkinter.END)
        no_length_patch = bool(self.skip_ogg_patch.get())
        self.hijack_output()
        r21buddy.run(target_dir, input_paths,
                     length_patch=(not no_length_patch), verbose=True)
        output = self.restore_output()
        self.log_window.configure(state=Tkinter.NORMAL)
        self.log_window.insert(Tkinter.END, output)
        self.log_window.see(Tkinter.END)
        self.log_window.configure(state=Tkinter.DISABLED)

    def log(self, msg, *tags):
        self.log_window.insert(Tkinter.INSERT, msg, *tags)

    def hijack_output(self):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = sys.stderr = StringIO()

    def restore_output(self):
        sio = sys.stdout
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        output = sio.getvalue()
        return output

def main():
    root = MainWindow()
    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
