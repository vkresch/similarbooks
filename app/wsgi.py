import multiprocessing
import gunicorn.app.base
from similarbooks import create_app


def number_of_workers():
    # return (multiprocessing.cpu_count() * 2) + 1
    return 4


class StandaloneApplication(gunicorn.app.base.BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


if __name__ == "__main__":
    som_app = create_app()
    options = {
        "bind": "%s:%s" % ("127.0.0.1", "8000"),
        "workers": number_of_workers(),
    }
    StandaloneApplication(som_app, options).run()
