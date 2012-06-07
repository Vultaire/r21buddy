import os, sys, Tkinter, tkFileDialog, tkMessageBox


class Input(object):

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


class File(object):

    def __init__(self, parent, label_text, default_text=None):
        self.label = Tkinter.Label(parent, text=label_text)
        self.str_var = Tkinter.StringVar()
        if default_text is not None:
            self.str_var.set(default_text)
        self.entry = Tkinter.Entry(parent, textvariable=self.str_var)
        self.button = Tkinter.Button(parent, text="Browse...", 
                                     command=self.on_browse)

    def on_browse(self):
        path = tkFileDialog.askopenfilename()
        if len(path) > 0:
            self.str_var.set(path)

    def grid(self, row):
        self.label.grid(row=row, column=0, sticky=Tkinter.W)
        self.entry.grid(row=row, column=1)
        self.button.grid(row=row, column=2)


class MainWindow(object):
    def __init__(self):
        self.root = Tkinter.Tk()
        self.root.title("r21buddy: Ogg Length Patch Utility")
        main_frame = Tkinter.Frame(self.root, padx=5, pady=5)
        main_frame.pack()

        input_file = File(main_frame, "Input file name:")
        input_file.grid(row=0)

        # Radio select: patch or check
        # Also: update execute button text depending on which is selected!

        output_file = File(main_frame, "Output file name (optional):")
        output_file.grid(row=1)

        song_length = Input(main_frame, "Desired song length:", "1:45")
        song_length.grid(row=2)

        check_length = Tkinter.Checkbutton(main_frame, text="Check length only; do not modify file")
        check_length.grid(row=4, columnspan=2, sticky=Tkinter.W)

        btn = Tkinter.Button(main_frame, text="Make it so!", command=self.execute)
        btn.grid(row=5, columnspan=3)

    def mainloop(self):
        self.root.mainloop()

    def execute(self):
        print "EXECUTE PLACEHOLDER"


def main():
    root = MainWindow()
    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
