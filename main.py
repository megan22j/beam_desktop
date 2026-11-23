"""Launch the Tkinter Beam Designer."""

import tkinter as tk

from beam_app import BeamDesignerApp


def main() -> None:
    root = tk.Tk()
    BeamDesignerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
