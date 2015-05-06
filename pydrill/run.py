from pydrill.app import app
from pydrill import views  # noqa


if __name__ == '__main__':
    app.run(host='0', port=5000, debug=True)
