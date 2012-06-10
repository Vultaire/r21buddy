import os, sys, traceback
from cStringIO import StringIO
import Tkinter, tkFileDialog, tkMessageBox
from r21buddy import oggpatch


class CompositeControl(object):

    def configure(self, **kwargs):
        self.entry.configure(**kwargs)
        self.button.configure(**kwargs)

    def get(self):
        return self.entry.get()


class Input(CompositeControl):

    def __init__(self, parent, label_text, default_text=None):
        self.label = Tkinter.Label(parent, text=label_text)
        self.str_var = Tkinter.StringVar()
        if default_text is not None:
            self.str_var.set(default_text)
        self.entry = Tkinter.Entry(parent, textvariable=self.str_var)

    def grid(self, row):
        self.label.grid(row=row, column=0, sticky=Tkinter.W)
        self.entry.grid(row=row, column=1, columnspan=2,
                        sticky=(Tkinter.W + Tkinter.E))


class File(CompositeControl):

    def __init__(self, parent, label_text, default_text=None, save=False):
        self.label = Tkinter.Label(parent, text=label_text)
        self.str_var = Tkinter.StringVar()
        if default_text is not None:
            self.str_var.set(default_text)
        self.entry = Tkinter.Entry(parent, textvariable=self.str_var)
        self.button = Tkinter.Button(parent, text="Browse...", 
                                     command=self.on_browse)
        self.save = save

    def on_browse(self):
        if self.save:
            path = tkFileDialog.asksaveasfilename(
                filetypes=[
                    ("Ogg files", "*.ogg"),
                    ("All files", "*.*"),
                    ])
        else:
            path = tkFileDialog.askopenfilename(
                filetypes=[
                    ("Ogg files", "*.ogg"),
                    ("All files", "*.*"),
                    ])
        if len(path) > 0:
            self.str_var.set(path)

    def grid(self, row):
        self.label.grid(row=row, column=0, sticky=Tkinter.W)
        self.entry.grid(row=row, column=1, sticky=(Tkinter.W, Tkinter.E))
        self.button.grid(row=row, column=2, sticky=(Tkinter.W, Tkinter.E))

    def configure(self, **kwargs):
        self.entry.configure(**kwargs)
        self.button.configure(**kwargs)


class MainWindow(object):
    def __init__(self):
        self.root = Tkinter.Tk()
        self.root.title("r21buddy: Ogg Length Patch Utility")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        main_frame = Tkinter.Frame(self.root, padx=5, pady=5)
        main_frame.grid(row=0, column=0,
                        sticky=(Tkinter.N, Tkinter.S, Tkinter.E, Tkinter.W))
        main_frame.columnconfigure(1, weight=1)

        self.input_file = File(main_frame, "Input file name:")
        self.input_file.grid(row=0)

        self.mode = Tkinter.StringVar()
        patch_mode = Tkinter.Radiobutton(
            main_frame, text="Apply patch",
            variable=self.mode, value="patch", command=self.on_patch_mode)
        patch_mode.select()
        patch_mode.grid(row=1, column=0, columnspan=3, sticky=Tkinter.W)
        check_mode = Tkinter.Radiobutton(
            main_frame, text="Check length only; do not modify file",
            variable=self.mode, value="check", command=self.on_check_mode)
        check_mode.grid(row=2, column=0, columnspan=3, sticky=Tkinter.W)

        # Radio select: patch or check
        # Also: update execute button text depending on which is selected!

        self.output_file = File(main_frame, "Output file name (optional):",
                                save=True)
        self.output_file.grid(row=3)

        self.song_length = Input(main_frame, "Desired song length:", "1:45")
        self.song_length.grid(row=4)

        self.execute_btn = Tkinter.Button(main_frame, text="Make it so!", command=self.execute)
        self.execute_btn.grid(row=5, columnspan=3)

        self.on_patch_mode()

    def mainloop(self):
        self.root.mainloop()

    def on_patch_mode(self):
        # Enable output file
        self.output_file.configure(state=Tkinter.NORMAL)
        self.execute_btn.configure(text="Patch file")

    def on_check_mode(self):
        # Disable output file
        self.output_file.configure(state=Tkinter.DISABLED)
        self.execute_btn.configure(text="Check file")

    def get_time(self):
        length = self.song_length.get()
        if length.count(":") == 0:
            h = 0
            m = 0
            s = int(length)
        elif length.count(":") == 1:
            h = 0
            m, s = map(int, length.rsplit(":", 1))
        elif length.count(":") == 2:
            h, m, s = map(int, length.rsplit(":", 2))
        else:
            raise ValueError("Bad time", length)
        if h < 0 or m < 0 or s < 0:
            raise ValueError("Bad time", length)
        return (h*3600) + (m*60) + s

    def execute(self):
        input_file = self.input_file.get()
        if len(input_file) == 0:
            tkMessageBox.showinfo(
                title="No input file",
                message="Please select an input file")
            return
        elif not os.path.isfile(input_file):
            tkMessageBox.showinfo(
                title="Bad input file",
                message=("Could not find the specified input file.  "
                         "Please re-select the file."))

        try:
            length = self.get_time()
        except ValueError:
            tkMessageBox.showinfo(
                title="Invalid song length",
                message="Enter a valid song length.  (i.e. 1:45, 3:13:37, etc.)")
            return

        mode = self.mode.get()
        if mode == "patch":
            output_file = self.output_file.get()
            if len(output_file) == 0:
                output_file = input_file
            output_dir = os.path.split(output_file)[0]

            # Allow the output file to be a dir.  In this case take
            # the input file's name and append it.
            if os.path.isdir(output_file):
                output_dir = output_file
                output_file = os.path.join(output_dir,
                                           os.path.basename(input_file))

            if not os.path.exists(output_dir):
                tkMessageBox.showinfo(
                    title="Output directory not found",
                    message=("Output directory does not exist.  "
                             "Please check your output file name."))
            elif not os.path.isdir(output_dir):
                tkMessageBox.showinfo(
                    title="Bad output directory",
                    message=("The specified output directory conflicts with "
                             "an existing file.  Please use a different "
                             "output file name."))

            self.hijack_output()
            try:
                oggpatch.patch_file(
                    input_file, length, output_file=output_file, verbose=True)
            except:
                print traceback.format_exc()
            self.restore_output()
        elif mode == "check":
            self.hijack_output()
            try:
                oggpatch.check_file(input_file, length, verbose=True)
            except:
                print traceback.format_exc()
            self.restore_output()
        else:
            raise ValueError("Bad mode", mode)

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
