# TG Fish Bot
TG Fish Bot - простой telegram бот, позволяющий делать заказы товаров. В роли CMS используется [elasticpath](https://elasticpath.com/),
поэтому необходима регистрация и API-токен данного сервиса. Так же необходим Redis (можно зарегистрироваться [тут](https://redislabs.com/))

Попробовать бота можно тут @tg_fish_shop_bot

## Требования к окружению
1. `python>=3.8`
1. `requests==2.26.0`
2. `redis==3.2.1`
3. `environs==9.3.5`
4. `python-telegram-bot==11.1.0`

## Необходимые переменные окружения
1. `TG_TOKEN` - токер бота telegram (можно получить, создав нового бота через `@BotFather`)
2. `REDIS_HOST` - хост Redis
3. `REDIS_PORT` - порт Redis
4. `REDIS_PASSWORD` - пароль для Redis
5. `ELASTICPATH_ID=` - токен сервиса Elasticpath

## Деплой на Heroku
1. Сделать fork репозитория
2. Зарегистрироваться на [heroku](https://www.heroku.com/)
3. Создать новое приложения в heroku
4. Подключить репозиторий с кодом в приложении
5. Создать бота в telegram 
6. В настройках приложения в heroku создать переменные окружения (выше)
