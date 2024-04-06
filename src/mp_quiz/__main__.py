import rich_click as click

from .get_data import create_json


@click.group()
def cli():
    pass


def main():
    cli()


@cli.command()
def get_data():
    create_json()


if __name__ == "__main__":
    main()
