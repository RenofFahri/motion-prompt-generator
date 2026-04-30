"""Entry point: ``python -m motion_prompt_generator`` or the ``motion-prompt-generator`` script."""

from __future__ import annotations

from .app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
