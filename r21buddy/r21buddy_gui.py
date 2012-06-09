import os, sys
from cStringIO import StringIO
import Tkinter, tkFileDialog, tkMessageBox
from r21buddy import oggpatch


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

        """
        Layouts:

        ----------------------------------------

        Target dir: [______________] [Browse...]

        Input directories: [Add ...]

        C:/foo/bar   [Up] [Down] [Drop]  ^
        C:/foo/bar2  [Up] [Down] [Drop]  o
        C:/foo/bar3  [Up] [Down] [Drop]  |
        C:/foo/bar3  [Up] [Down] [Drop]  |
        C:/foo/bar3  [Up] [Down] [Drop]  v

        [ ] Don't apply the Ogg length patch

        [Run]

        +-Log------------+
        |<log...>        |
        |                |
        |                |
        |                |
        |                |
        |                |
        +----------------+

        ----------------------------------------

        Target dir: [______________] [Browse...]

        Input directories: [Add ...]

        +--------------+
        |C:/foo/bar   ^|[Move Up]
        |C:/foo/bar   o|
        |C:/foo/bar2  ||[Move Down]
        |C:/foo/bar3  ||
        |C:/foo/bar3  ||
        |C:/foo/bar3  v|[Drop]
        +--------------+
        [ ] Don't apply the Ogg length patch

        [Run]

        +-Log------------+
        |<log...>        |
        |                |
        |                |
        |                |
        |                |
        |                |
        +----------------+


        """

        control_frame = Tkinter.Frame(main_frame)
        control_frame.pack(anchor=Tkinter.W)

        self.target_dir = Directory(control_frame, "Target directory:")
        self.target_dir.pack(anchor=Tkinter.W)

        f = Tkinter.Frame(control_frame)
        f.pack(anchor=Tkinter.W, fill=Tkinter.X, expand=True)
        Tkinter.Label(f, text="Input directories:") \
            .pack(side=Tkinter.LEFT)
        Tkinter.Button(f, text="Add...", command=self.on_inputdir_add, width=10) \
            .pack(side=Tkinter.LEFT)

        input_dir_frame = Tkinter.LabelFrame(
            control_frame, text="Selected input directories")
        input_dir_frame.pack(fill=Tkinter.BOTH, expand=True)
        self.input_dirs = Tkinter.Listbox(input_dir_frame)
        self.input_dirs.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        button_frame = Tkinter.Frame(input_dir_frame)
        button_frame.pack(side=Tkinter.RIGHT, anchor=Tkinter.N)
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
        scroll = Tkinter.Scrollbar(log_frame)
        # Note: using really small width since we'll auto-expand.
        self.log_window = Tkinter.Text(log_frame, yscrollcommand=scroll.set,
                                       width=1, height=10)
        self.log_window.pack(side=Tkinter.LEFT, fill=Tkinter.BOTH, expand=True)
        scroll.pack(side=Tkinter.RIGHT, fill=Tkinter.Y)

    def mainloop(self):
        self.root.mainloop()

    def on_inputdir_add(self):
        print "on_inputdir_add"
    def on_run(self):
        print "on_run"
    def on_move_up(self):
        print "on_move_up"
    def on_move_down(self):
        print "on_move_down"
    def on_delete(self):
        print "on_delete"

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
        tkMessageBox.showinfo(
            title="Execution log",
            message=output)

def main():
    root = MainWindow()
    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
