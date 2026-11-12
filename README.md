# Haou Taikei Ryuu Knight – Lord of Paladin (SNES) — Traducción al español

Traducción no oficial apoyada con IA (fan-translation) de **Haou Taikei Ryuu Knight – Lord of
Paladin** (Super Nintendo, Bandai 1994) al español, junto con las herramientas usadas para crearla.

Web del proyecto: https://fjveralv.github.io/Traduccion_Haou_aikei_Ryuu_Knight/

La traducción parte del parche inglés de [Game Translate](https://gametranslate.us/translations/haou-taikei-ryuu-knight-english-patch/)
(v1.0), que ya trae fuente de ancho variable y el texto en ASCII.

Este repositorio **no incluye ninguna ROM ni datos del juego**. Contiene:

- `RyuuKnight_ES.v1.0.bps` — el parche de traducción, en formato **BPS**.
  `RyuuKnight_ES.bps` es siempre la última versión; las anteriores se conservan con su número.
- `tools/` — las herramientas (Python) con las que se ha hecho la traducción: extraer, insertar,
  comprimir/descomprimir LZSS, redibujar menús y nombres, crear el parche BPS.
- `traduccion/` — la traducción: diálogos por lotes (`lotes/`, solo en español), nombres de
  objetos y lugares, menús, personajes y textos de la pantalla de título.
- `DOCUMENTACION.md` — documentación técnica: mapa de la ROM, formato del texto, punteros,
  compresión, fuente y tablas de anchos, gráficos de menú y guía de las herramientas.

## Cómo aplicar el parche

Necesitas tu propia copia legal del juego **japonés**, revisión 1, sin cabecera:

- `Haou Taikei Ryuu Knight - Lord of Paladin (Japan) (Rev 1).sfc`
- CRC32 `2740560B`

1. Abre un programa que aplique parches BPS, por ejemplo **[Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/)**,
   **Floating IPS (Flips)** o **MultiPatch**.
2. Selecciona tu ROM japonesa (haz antes una copia).
3. Selecciona `RyuuKnight_ES.v1.0.bps` como parche.
4. Aplica. El formato BPS comprueba que la ROM es la correcta y que el resultado es exacto.
5. Juega la ROM resultante en tu emulador (Snes9x, bsnes, Mesen…).

No hace falta aplicar antes el parche inglés: el BPS español se aplica directamente sobre la ROM
japonesa.

## Novedades de la 1.0

- Primera versión completa.
- Los 1227 mensajes de diálogo traducidos.
- Nombres de objetos, magias, lugares y los 12 títulos de episodio, redibujados con la fuente
  del juego.
- Menús e interfaz: menú de sistema, configuración, tiendas, Sí/No y avisos.
- Pantalla de título: «NUEVO JUEGO / CONTINUAR» con el estilo original.
- Acentos, eñe y signos de apertura: `á é í ó ú ü ñ Á É Í Ó Ñ ¿ ¡`.

## Estado de la traducción

- Diálogos: traducidos (1227/1227).
- Nombres de objetos, magias y lugares: traducidos (163).
- Menús e interfaz: traducidos (56 textos).
- Pantalla de título: traducida.
- Logo del juego (リューナイト / ロード オブ パラディン): se deja el original japonés, igual que en el
  parche inglés.
- Teclado para cambiar el nombre: sin ñ ni acentos.

## Las herramientas (`tools/`)

Scripts en Python 3.10 o superior; solo necesitan Pillow (`pip install pillow`).

| Script | Qué hace |
|---|---|
| `extraer.py` | Exporta textos, nombres, menús y gráficos de la ROM. |
| `insertar.py` | Inserta la traducción, comprueba que cada línea cabe en la ventana y crea la ROM y el BPS. |
| `aplicar_lote.py` | Mide y aplica un lote de diálogos (`--comprobar` solo mide). |
| `reconstruir.py` | Hace todo el proceso de una vez y genera `RyuuKnight_ES.bps`. |
| `menus.py`, `titulo.py` | Redibujan los menús y la pantalla de título con el estilo del juego. |
| `lzss.py`, `bps.py` | Compresión del juego y formato de parche BPS. |

Para regenerar el parche publicado, pon en la carpeta del proyecto tu ROM japonesa y el parche
inglés `Haou Taikei Ryuu Knight - Lord of Paladin (English) v1.0.bps` (de Game Translate) y ejecuta:

```bash
python tools/reconstruir.py
```

El resultado es idéntico byte a byte al parche publicado. Detalles técnicos en
[DOCUMENTACION.md](DOCUMENTACION.md).

## Créditos y licencia

- Traducción al español y herramientas: Fveralv.
- Parche inglés del que parte esta traducción: [Game Translate](https://gametranslate.us/translations/haou-taikei-ryuu-knight-english-patch/).
- Herramientas bajo licencia GPLv3 (ver `LICENSE`).
- Este proyecto no está afiliado a Bandai, Sunrise ni Game Translate. Haou Taikei Ryuu Knight es
  marca registrada de sus respectivos propietarios. Se distribuye únicamente el parche de
  diferencias, la traducción y el código de las herramientas, nunca datos del juego original.
