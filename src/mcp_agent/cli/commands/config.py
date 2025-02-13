import typer

app = typer.Typer()


@app.command()
def show():
    """Show the configuration."""
    print("NotImplemented")
