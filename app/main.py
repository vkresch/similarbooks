from similarbooks import create_app
from app.similarbooks.main.constants import DEBUG

som_app = create_app()

if __name__ == "__main__":
    som_app.run(host="127.0.0.1", port=8000, threaded=True, debug=DEBUG)
