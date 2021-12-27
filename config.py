from environs import Env


env = Env()
env.read_env()

ELASTICPATH_ID = env('ELASTICPATH_ID')
TG_TOKEN = env("TG_TOKEN")

REDIS_PASSWORD = env("REDIS_PASSWORD")
REDIS_HOST = env("REDIS_HOST")
REDIS_PORT = env("REDIS_PORT")