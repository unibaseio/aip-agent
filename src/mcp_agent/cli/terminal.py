from rich.console import Console


class Application:
    def __init__(self, verbosity: int = 0, enable_color: bool = True):
        self.verbosity = verbosity
        self.console = Console(color_system="auto" if enable_color else None)

    def log(self, message: str, level: str = "info"):
        if level == "info" or (level == "debug" and self.verbosity > 0):
            self.console.print(f"[{level.upper()}] {message}")

    def status(self, message: str):
        return self.console.status(f"[bold cyan]{message}[/bold cyan]")
