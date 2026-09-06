from flask import Flask

from App.routes import main


app = Flask(__name__, template_folder='App/templates', static_folder='App/static')

app.register_blueprint(main)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)