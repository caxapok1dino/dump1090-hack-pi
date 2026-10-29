# Запуск на Raspberry Pi с HackRF

Контейнер принимает сигнал ADS-B на 1090 МГц через HackRF, сохраняет исходные
IQ-данные и одновременно передаёт их в `dump1090`. Для запуска нужны Raspberry
Pi с USB, HackRF с антенной на 1090 МГц, Docker Engine и плагин Docker Compose.
Для непрерывной записи используйте накопитель, способный выдерживать 16 МБ/с;
предпочтительнее USB SSD, чем карта памяти.

## 1. Подготовьте Raspberry Pi

Рекомендуется 64-битная Raspberry Pi OS. Установите Docker Engine по
[инструкции для Debian/arm64](https://docs.docker.com/engine/install/debian/)
и [плагин Compose](https://docs.docker.com/compose/install/linux/).
Для 32-битной Raspberry Pi OS есть
[отдельная инструкция Docker](https://docs.docker.com/engine/install/raspberry-pi-os/).
Docker Engine v28 — последняя основная версия с поддержкой armhf. Проверьте установку:

```sh
sudo docker info
sudo docker compose version
```

Подключите HackRF к USB-порту Pi. Если используется PortaPack, переключите его
в режим HackRF. Убедитесь, что на накопителе достаточно свободного места.
Для клонирования проекта установите Git, если его ещё нет:

```sh
sudo apt-get update
sudo apt-get install -y git
```

## 2. Получите проект и проверьте HackRF

```sh
git clone https://github.com/caxapok1dino/dump1090-hack-pi.git
cd dump1090-hack-pi
mkdir -p recordings
sudo docker compose build
sudo docker compose run --rm --no-deps --entrypoint hackrf_info dump1090
```

Если репозиторий приватный, используйте URL с настроенным доступом к GitHub.
Команда `hackrf_info` должна показать подключённое устройство. Compose
передаёт контейнеру `/dev/bus/usb` и разрешает доступ к USB-устройствам.
Если HackRF не найден, проверьте подключение на хосте (`lsusb`, если установлен),
кабель, питание и режим PortaPack. См. также
[рекомендации HackRF](https://hackrf.readthedocs.io/en/latest/troubleshooting.html).

## 3. Настройте хранение и усиление

По умолчанию создаётся файл за каждую минуту записи (около 960 МБ), а
хранятся только последние 10 файлов. Создайте `.env` рядом с `compose.yaml`,
чтобы изменить параметры перед запуском:

```dotenv
RECORD_SEGMENT_SECONDS=30
MAX_RECORDINGS=4
HACKRF_LNA_GAIN=16
HACKRF_VGA_GAIN=20
HACKRF_AMP_ENABLE=0
```

Если записи должны лежать на подключённом SSD, сначала смонтируйте его и
создайте каталог на нём, затем добавьте в `.env` абсолютный путь, например
`RECORDINGS_HOST_DIR=/mnt/adsb/recordings`. Без этой настройки файлы
сохраняются в `./recordings` внутри каталога проекта.

`MAX_RECORDINGS=0` отключает удаление старых файлов; тогда свободное место
нужно контролировать самостоятельно. Частоту задаёт `HACKRF_FREQUENCY_HZ`
(по умолчанию `1090000000`), а нужное устройство при нескольких HackRF —
`HACKRF_SERIAL`.

## 4. Запустите приём и запись

```sh
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs -f
```

Откройте `http://<IP_RPI>:8080` с другого устройства в той же сети. Порт
`30002` отдаёт сырые сообщения, `30003` — поток SBS1. Проверьте появление
файлов командой `sudo docker compose exec dump1090 ls -lh /recordings`.

HackRF захватывает 8 млн комплексных отсчётов в секунду. Файлы `.cs8` содержат
чередующиеся знаковые 8-битные I/Q-отсчёты; поток для `dump1090`
преобразуется в 2 МГц и беззнаковый 8-битный формат. Такой выбор частоты
захвата соответствует [рекомендации HackRF](https://hackrf.readthedocs.io/en/stable/sampling_rate.html).

## Остановка и проверка записи

```sh
sudo docker compose down
```

`down` останавливает контейнер, но не удаляет файлы из каталога записи. Для
проверки сохранённого файла без HackRF запустите из каталога проекта, заменив
`FILE.cs8` на имя файла:

```sh
sudo docker compose run --rm --no-deps --entrypoint bash dump1090 -lc \
  'ffmpeg -nostdin -hide_banner -loglevel error -f s8 -ar 8000000 -ac 2 -i /recordings/FILE.cs8 -ar 2000000 -ac 2 -f u8 pipe:1 | /app/dump1090 --ifile - --stats'
```

Если карта пуста, сначала проверьте логи, размер файлов и антенну. Наличие
файлов подтверждает получение IQ-потока, но само по себе не гарантирует приём
сообщений ADS-B.
