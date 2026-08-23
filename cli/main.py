import typer
from .commands import app as commands_app

app = typer.Typer(
    name="docswarm",
    help="DocSwarm CLI for deterministic architecture analysis.",
    add_completion=False
)

app.registered_commands = commands_app.registered_commands
app.registered_groups = commands_app.registered_groups
app.registered_callback = commands_app.registered_callback

if __name__ == "__main__":
    app()
