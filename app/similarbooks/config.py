import os


class Config:
    VERSION_MAJOR = 1
    VERSION_MINOR = 1
    VERSION_PATCH = 0
    SECRET_KEY = os.environ.get("API_SECRET_KEY")
    EVAL_API_SECRET_KEY = os.environ.get("EVAL_API_SECRET_KEY")
    MONGODB_DB = "similarbooks"
    MONGODB_SIMILARBOOKS_URL = os.environ.get("MONGODB_SIMILARBOOKS_URL")
    MONGODB_SIMILARBOOKS_USER = os.environ.get("MONGODB_SIMILARBOOKS_USER")
    MONGODB_SIMILARBOOKS_PWD = os.environ.get("MONGODB_SIMILARBOOKS_PWD")
    MONGO_URI = f"mongodb://{MONGODB_SIMILARBOOKS_USER}:{MONGODB_SIMILARBOOKS_PWD}@{MONGODB_SIMILARBOOKS_URL}:27017/{MONGODB_DB}?authMechanism=DEFAULT&authSource={MONGODB_DB}&tls=true&tlsCAFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.crt&tlsCertificateKeyFile=%2Fetc%2Fssl%2Fmongodb%2Fmongodb.pem"
    MONGODB_SETTINGS = {
        "host": MONGO_URI,
    }
    SENDER_NAME = "similarbooks Support"
    MAIL_USERNAME = "support@findsimilarbooks.com"
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_SERVER = "mail.privateemail.com"
    MAIL_PORT = 465

    TELEGRAM_BOT_USERNAME = "@similarbooksBot"
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

    CAPTCHA_CONFIG = {
        "SECRET_CAPTCHA_KEY": "7df1e1c05304sdsdf26faa49fa752a8c690126cf98b40b931d54e6e9cc3b7d6ffe8b7",
        "CAPTCHA_LENGTH": 6,
        "CAPTCHA_DIGITS": False,
        "EXPIRE_SECONDS": 300,
    }
