# Piff & Puff – Degu-flykten

Ett 3D-spel i Python (Ursina). Degusarna **Piff** och **Puff** har smitit ut i
trädgården. Katten **Pixi** jagar dem! Få in båda i buren (inne i huset) utan
att bli uppäten.

## Ladda ner färdigt spel (utan Python)

Under **Releases** på GitHub finns färdiga versioner att ladda ner:

- **Windows:** packa upp `Degu-flykten-windows.zip` och dubbelklicka på
  `Degu-flykten.exe`. Visar Windows "Datorn skyddades av Windows"? Klicka på
  **Mer information** → **Kör ändå**.
- **Mac:** packa upp `Degu-flykten-mac.zip`. Första gången: högerklicka på
  `Degu-flykten.app` och välj **Öppna**. (Fungerar på Mac med Apple-chip, M1
  eller nyare.)
- **Linux:** packa upp `Degu-flykten-linux.tar.gz` och kör
  `Degu-flykten/Degu-flykten`.

### Bygga en ny version

Skapa och pusha en tagg, så bygger GitHub alla tre versionerna och lägger upp
dem som en release:

```bash
git tag v1.0
git push origin v1.0
```

Du kan också bygga utan release: fliken **Actions** → **Bygg spelet** →
**Run workflow**. Filerna hamnar då under "Artifacts" på körningens sida.

## Starta från källkoden

Du behöver **Python 3.10 eller nyare** (3.12 rekommenderas). Ladda ner det från
[python.org/downloads](https://www.python.org/downloads/) om du inte redan har det.

Installationen (steg 1–2) behöver bara göras en gång. Sedan räcker steg 3 för
att spela.

### Windows

1. Installera Python från python.org. **Kryssa i "Add python.exe to PATH"** i
   första rutan i installationsprogrammet.
2. Öppna mappen med spelet i Utforskaren, klicka i adressfältet, skriv
   `powershell` och tryck Enter. Kör sedan:

   ```powershell
   py -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```

3. Starta spelet:

   ```powershell
   .venv\Scripts\python degu_flykten.py
   ```

### Mac

1. Installera Python från python.org (eller med `brew install python`).
2. Öppna **Terminal**, skriv `cd ` (med mellanslag), dra in spelmappen i
   fönstret och tryck Enter. Kör sedan:

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. Starta spelet:

   ```bash
   .venv/bin/python degu_flykten.py
   ```

### Linux / WSL

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python degu_flykten.py
```

(Saknas `venv`? Installera det med t.ex. `sudo apt install python3-venv`.)

## Kontroller

| Tangent | Gör |
|---|---|
| WASD / piltangenter | Spring |
| Shift | Spurta (kostar ork) |
| Mus eller Q / E | Vrid kameran |
| Mushjul | Zooma |
| Tab | Byt mellan Piff och Puff (den andra följer efter) |
| Esc | Paus |

## Tips

- Följ det **gröna ljuset** – där står buren.
- Göm dig i **buskar**, under **sängen** eller **soffan** – då ser Pixi dig inte.
- Pixi gör ett **språng** när hon kommer nära, och måste sedan pusta ut. Spring då!
- **Solrosfrön** ger ny ork.
