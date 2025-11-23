from flask import Flask
from routes.subscriptions import bp as subscriptions_bp
from routes.home import home_bp
from routes.shorts import shorts_bp
from routes.mypage import yt_bp


def create_app():
    app = Flask(__name__)

    app.register_blueprint(subscriptions_bp, url_prefix="/subscriptions")
    app.register_blueprint(home_bp, url_prefix='/')
    app.register_blueprint(shorts_bp, url_prefix='/')
    app.register_blueprint(yt_bp, url_prefix='/')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=8000)


