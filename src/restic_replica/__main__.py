from restic_replica import __version__, app, console


def main():
    config = app.read_config_file()
    console.setup_logging()
    app.logging_headers(__version__)


if __name__ == "__main__":
    main()
