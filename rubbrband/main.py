import subprocess

import docker
import typer
from yaspin import yaspin

from rubbrband.controllers import eval, train

__author__ = "Rubbrband"

app = typer.Typer(no_args_is_help=True, rich_markup_mode="rich")
app.add_typer(train.app, name="train", subcommand_metavar="MODEL")
app.add_typer(eval.app, name="eval", subcommand_metavar="MODEL")

try:
    client = docker.from_env()
except docker.errors.DockerException:
    typer.echo("Docker is not running. Please start Docker and try again.")
    exit()


# create our database of models
db = {
    "lora": {
        "description": "Low-rank adapation for efficient stable diffusion fine tuning",
        "shape": "anything",
    },
    "dreambooth": {
        "description": "Stable diffusion models, trained with dreambooth method",
        "shape": "anything",
    },
    "control": {
        "description": "Control diffusion models by adding extra conditions",
        "shape": "anything",
    },
}

# Pass singleton objects to our subcommands
train.client = client
eval.client = client
train.db = db
eval.db = db


@app.callback()
def main():
    """
    The Rubbrband CLI allows you to train and evaluate models.
    """
    pass


@app.command()
def models():
    """List all supported models"""
    typer.echo("Supported Models:")
    typer.echo(f"{'NAME':12} DESCRIPTION")
    for key, val in db.items():
        typer.echo(f"{key:12} {val['description']}")


@app.command()
def ls():
    """List all running models"""
    typer.echo("Running Models:")
    containers = client.containers.list()

    # filter containers that start with rb-
    for container in containers:
        if container.name.startswith("rb-"):
            typer.echo(container.name)


@app.command()
def launch(model: str):
    """
    Launch a new MODEL.

    MODEL is the name of the model to launch.

    Example: rubbrband launch lora
    """

    if model not in db:
        typer.echo("Model not found")
        return

    with yaspin() as sp:
        sp.text = "Setting Up Environment. This may take up to 10 minutes."
        image_name = f"rubbrband/{model}"
        # pull image if not already pulled
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            client.images.pull(image_name)

    with yaspin() as sp:
        sp.text = f"Finished. Run rubbrband train {model} to train this model on sample data."


@app.command()
def enter(model: str):
    """
    Enter into a running MODEL.

    MODEL is the name of the model.

    Example: rubbrband enter lora
    """
    # if container not running, start it
    with yaspin() as sp:
        sp.text = "Launching Docker Container"

        container_name = f"rb-{model}"
        try:
            container = client.containers.get(container_name)
        except docker.errors.NotFound:
            client.containers.run(container_name, detach=True, name=container_name, tty=True, stdin_open=True)

        container = client.containers.get(container_name)

        if container.status != "running":
            container.start()

    subprocess.run(["docker", "exec", "-it", container_name, "/bin/bash"])


if __name__ == "__main__":
    app()
