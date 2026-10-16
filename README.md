# door-helper

Ein kleines Info-Display für die Wohnungstür: Ein Raspberry Pi mit einem 2.13" Touch-E-Ink-Display von Waveshare zeigt auf einen Blick, ob man gleich los muss.

- **Abfahrten** – Live-Abfahrten einer Haltestelle in der Schweiz (OJP 2.0 / opentransportdata.swiss), inkl. Hinweis auf Störungen
- **Wetter** – aktuelle Temperatur, Tagesmaximum und Beschreibung (Open-Meteo, kein API-Key nötig)
- **Nextbike** – freie Velos an ausgewählten Stationen
- **Abfuhrkalender** – Hinweis „Morgen: Karton, Kehricht“ am Vortag der Abfuhr (aus einer `.ics`-Datei)

## Funktionsweise

Der Home-Screen ist in drei Felder geteilt (Abfahrten | Wetter | Nextbike). Im Hintergrund werden alle 60 Sekunden die Daten abgefragt; das Display wird nur neu gezeichnet, wenn sich etwas Sichtbares ändert (schont das E-Ink-Panel):

| Feld      | Anzeige auf dem Home-Screen                              |
|-----------|----------------------------------------------------------|
| Abfahrten | `!` bei einer aktuellen Störungsmeldung                  |
| Wetter    | Wetter-Symbol und Tagesmaximum                           |
| Nextbike  | `!` bei ≤ 2 Velos, `X` bei 0 Velos an der Heim-Station   |
| Leiste unten | Abfuhr-Hinweis, von 15 h vor bis 2 h nach der Abfuhr (einstellbar) |

Ein Tipp auf ein Feld öffnet die Detailansicht. Die Abfahrten werden dort alle 10 Sekunden aktualisiert. Nach 60 Sekunden ohne Berührung kehrt das Display automatisch zum Home-Screen zurück.

### Display-Aktualisierung

E-Ink-Panels kennen zwei Arten der Aktualisierung:

- **Voll** (~2 s, flackert): entfernt Geisterbilder. Wird für den Home-Screen und die statischen Ansichten (Wetter, Nextbike) verwendet; danach geht das Panel in den Tiefschlaf.
- **Teilweise** (~0.5 s, ohne Flackern): für die Live-Abfahrten im 10-Sekunden-Takt. Das Panel bleibt dabei wach; nach spätestens 20 Teil-Aktualisierungen und beim Zurückkehren zum Home-Screen folgt wieder eine volle.

## Hardware

- Raspberry Pi (getestet mit Raspberry Pi OS, Python 3.9)
- [Waveshare 2.13inch Touch e-Paper HAT](https://www.waveshare.com/wiki/2.13inch_Touch_e-Paper_HAT_Manual) (Panel `epd2in13_V4`, Touch-Controller GT1151)

## Installation

1. **SPI und I²C aktivieren**

   ```bash
   sudo raspi-config   # Interface Options → SPI und I2C aktivieren
   ```

2. **Systempakete und Waveshare-Bibliothek installieren**

   ```bash
   sudo apt install python3-pip python3-gpiozero python3-spidev python3-smbus fonts-dejavu-core
   git clone https://github.com/waveshare/Touch_e-Paper_HAT.git ~/Touch_e-Paper_HAT
   ```

3. **Projekt klonen und Python-Abhängigkeiten installieren**

   ```bash
   git clone https://github.com/<user>/door-helper.git
   cd door-helper/pi
   pip3 install -r requirements.txt
   ```

4. **Konfiguration anlegen**

   ```bash
   cp .env.example .env
   nano .env
   ```

## Konfiguration

Alle Einstellungen stehen in `pi/.env` (Vorlage: [`pi/.env.example`](pi/.env.example)).

| Variable                 | Pflicht | Beschreibung                                                                 |
|--------------------------|:-------:|------------------------------------------------------------------------------|
| `OJP_API_KEY`            | ✔       | API-Key von [opentransportdata.swiss](https://api-manager.opentransportdata.swiss/) |
| `OJP_STOP_POINT_REF`     | ✔       | Haltestellen-Nummer (DiDok/BPUIC), z. B. `8503000` für Zürich HB             |
| `OJP_STOP_NAME`          |         | Name der Haltestelle (nur informativ in der Anfrage)                         |
| `WEATHER_LAT`, `WEATHER_LON` | ✔   | Koordinaten für das Wetter                                                   |
| `NEXTBIKE_STATIONS`      |         | Stationen als `uid:Name`, kommagetrennt                                      |
| `NEXTBIKE_HOME_STATION`  |         | UID der Station, deren Verfügbarkeit auf dem Home-Screen angezeigt wird      |
| `NEXTBIKE_DOMAIN`        |         | Nextbike-Domain, Standard `ch`                                               |
| `WASTE_CALENDAR_FILES`   |         | `.ics`-Datei(en) des Entsorgers, kommagetrennt; relativ zu `pi/`             |
| `WASTE_LOOKAHEAD_HOURS`  |         | Stunden vor der Abfuhr, ab denen der Hinweis erscheint, Standard `15`        |
| `WASTE_AFTER_PICKUP_HOURS` |       | Stunden nach der Abfuhr, die der Hinweis sichtbar bleibt, Standard `2`       |
| `TIMEZONE`               |         | Standard `Europe/Zurich`                                                     |
| `WAVESHARE_LIB_PATH`     |         | Pfad zu `Touch_e-Paper_HAT/python/lib`, Standard `/home/pi/...`               |
| `FONT_PATH`              |         | TrueType-Schrift, Standard DejaVu Sans Bold                                   |
| `LOG_LEVEL`              |         | `DEBUG`, `INFO` (Standard), `WARNING` …                                       |

Intervalle und Timeouts (Abfrage alle 60 s, Timeout 60 s usw.) sind als Konstanten am Ende von [`pi/config.py`](pi/config.py) definiert.

Nextbike-Stations-UIDs findest du im Live-Feed: `https://maps2.nextbike.net/maps/nextbike-live.json?domains=ch` (nach dem Stationsnamen suchen, Feld `uid`).

### Abfuhrkalender

Viele Gemeinden bzw. Entsorger bieten den Abfuhrkalender als iCalendar-Datei (`.ics`) an, in Luzern z. B. [REAL](https://www.real-luzern.ch/). Lege die Datei unter `pi/data/` ab und trage sie in `WASTE_CALENDAR_FILES` ein. Für den Jahreswechsel können mehrere Dateien kommagetrennt angegeben werden; enthält der Kalender keine künftigen Termine mehr, erscheint eine Warnung im Log. `.ics`-Dateien sind in `.gitignore`, da sie Rückschlüsse auf die Wohnadresse erlauben.

## Starten

```bash
cd door-helper/pi
python3 main.py
```

Beenden mit `Strg+C`. Das Display wird dabei geleert, in den Tiefschlaf versetzt und die GPIO-Pins werden freigegeben.

### Autostart mit systemd

`/etc/systemd/system/door-helper.service`:

```ini
[Unit]
Description=door-helper E-Ink-Display
After=network-online.target
Wants=network-online.target

[Service]
User=pi
WorkingDirectory=/home/pi/door-helper/pi
ExecStart=/usr/bin/python3 -u main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload            # nach dem Anlegen/Ändern der .service-Datei
sudo systemctl enable --now door-helper # Autostart aktivieren und sofort starten
```

| Befehl                                   | Wirkung                                              |
|------------------------------------------|------------------------------------------------------|
| `sudo systemctl stop door-helper`        | Stoppen (bis zum nächsten Neustart des Pi)           |
| `sudo systemctl start door-helper`       | Wieder starten                                       |
| `sudo systemctl restart door-helper`     | Neu starten, z. B. nach Code- oder `.env`-Änderungen |
| `sudo systemctl disable --now door-helper` | Stoppen und Autostart deaktivieren                 |
| `systemctl status door-helper`           | Status anzeigen                                      |
| `journalctl -u door-helper -f`           | Logs live ansehen                                    |

> Bevor du `python3 main.py` manuell startest, den Dienst stoppen. Display und Touch-Controller können nicht von zwei Prozessen gleichzeitig verwendet werden.

## Projektstruktur

```
pi/
├── main.py              # Einstiegspunkt: Logging, Hardware-Setup, Start
├── app.py               # Zustandsautomat (Home, Abfahrten, Wetter, Nextbike)
├── config.py            # Konfiguration aus .env und Konstanten
├── sources/             # Datenquellen (ohne Hardware-Abhängigkeit)
│   ├── transport.py     #   Abfahrten und Störungen via OJP 2.0
│   ├── weather.py       #   Wetter via Open-Meteo (30 min gecacht)
│   ├── nextbike.py      #   Velo-Verfügbarkeit via Nextbike-Live-Feed
│   └── waste.py         #   Abfuhrtermine aus .ics-Dateien
├── ui/
│   ├── screens.py       #   Zeichnet die Ansichten als Bilder (ohne Hardware)
│   ├── epaper.py        #   E-Ink-Ansteuerung, volle/teilweise Aktualisierung
│   ├── touch.py         #   Touch-Eingabe (GT1151)
│   └── waveshare.py     #   Einbindung der Waveshare-Bibliothek
├── data/                # Eigene Abfuhrkalender (.ics, nicht im Repo)
└── .env.example         # Vorlage für die Konfiguration
tests/                   # pytest, läuft ohne Raspberry Pi
```

## Entwicklung

Die Tests und der Linter laufen auf jedem Rechner, ohne Display:

```bash
pip install -r requirements-dev.txt
pytest          # Tests
ruff check .    # Linter
ruff format .   # Formatierung
```

GitHub Actions führt beides bei jedem Push aus (Python 3.9 und 3.12). Die Bildschirm-Tests benötigen die Schrift aus `FONT_PATH` und werden sonst übersprungen.

## Datenquellen

- Fahrplandaten: [opentransportdata.swiss](https://opentransportdata.swiss/) (OJP 2.0)
- Wetter: [Open-Meteo](https://open-meteo.com/) (CC BY 4.0)
- Velos: [Nextbike](https://www.nextbike.ch/) Live-Feed
- Display-Treiber: [waveshare/Touch_e-Paper_HAT](https://github.com/waveshare/Touch_e-Paper_HAT) (MIT)
