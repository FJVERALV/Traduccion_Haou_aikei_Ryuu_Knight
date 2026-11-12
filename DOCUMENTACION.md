# Documentación técnica — *Haou Taikei Ryuu Knight – Lord of Paladin* (SNES) en español

La traducción parte del **parche inglés de Game Translate (v1.0)**: su texto está en
ASCII, ya trae fuente de ancho variable y tiene espacio de sobra, así que solo hay que
reemplazar el inglés por el español. El guion japonés original va comprimido y con
otra codificación, por eso no se usa directamente.

## Requisitos

- Python 3.10 o superior y Pillow (`pip install pillow`).
- En esta carpeta: la ROM japonesa *Rev 1* sin cabecera (CRC32 `2740560B`) y el parche
  inglés `.bps`. La ROM inglesa ya parcheada es opcional: si falta, se genera.

## Regenerar el parche publicado

El repositorio no incluye nada del juego: ni ROMs, ni el texto inglés, ni gráficos
extraídos. `traduccion/dialogos.txt` y `traduccion/graficos/` se crean desde tu ROM.
Con la ROM japonesa y el parche inglés en la carpeta del proyecto:

```bash
python tools/reconstruir.py
```
Extrae lo que falte, aplica todos los lotes de `traduccion/lotes/` (ahí están los 1227
mensajes en español), crea la ROM en `salida/` y copia el parche a `RyuuKnight_ES.bps`.
El resultado es idéntico byte a byte al parche publicado.

## Flujo de trabajo

```bash
python tools/extraer.py
```
Crea `extraido/` (el inglés de referencia, se regenera siempre) y `traduccion/`
(tu copia de trabajo; si ya existe no se toca, salvo con `--forzar`).

Traduce los archivos de `traduccion/` y luego ejecuta:

```bash
python tools/insertar.py
```
Esto genera `salida/Haou Taikei Ryuu Knight (ES).sfc` y el parche
`salida/Haou Taikei Ryuu Knight (ES).bps`, que se aplica sobre la ROM japonesa Rev 1.
También muestra **avisos** cuando una línea es demasiado larga para la ventana
(más de 236 px, unas 33 letras).

Para traducir por lotes: `python tools/aplicar_lote.py lote.txt --comprobar` mide las
líneas de un lote y, sin `--comprobar`, lo copia en `dialogos.txt`.

## Archivos que se traducen (`traduccion/`)

| Archivo | Contenido |
|---|---|
| `dialogos.txt` | Los 1227 mensajes del juego. Cada uno empieza con `@NNNN`; las líneas `#` llevan el inglés de referencia. No está en el repositorio: se genera desde la ROM y se rellena con `lotes/`. |
| `lotes/lote_NNNN.txt` | La traducción de los diálogos, de 100 en 100 mensajes, solo en español. |
| `nombres.txt` | 163 nombres: objetos, magias, los 12 títulos de episodio (116–127) y los lugares. `NNN \| inglés \| TRADUCCIÓN`. |
| `personajes.txt` | Nombres por defecto de los 6 personajes (máx. 8 letras, sin acentos). |
| `menus.txt` | 56 textos de menú y opciones (ver abajo). |
| `graficos/celdas_31_fuente_y_menus.png` | Fuente 16x16 (con las letras españolas ya añadidas) y los menús, que están dibujados como imagen (Yes/No, Save, Load, opciones de tienda…). |
| `graficos/anchos_fuente.txt` | Ancho en píxeles de cada letra. |
| `graficos/celdas_38_titulos_teclado.png` | Incluye el teclado de la pantalla de cambio de nombre. |
| `graficos/fuente8x8.png` | Fuente pequeña 8x8 (no la usan los diálogos), con las letras españolas. |
| `titulo.txt` | Textos de la pantalla de título ("NUEVO JUEGO" / "CONTINUAR") y, en la 3.ª línea, el crédito que sustituye a la URL del parche inglés ("Traducido por FVERALV"). Al escribirlo se recomprime todo el banco $25 para que quepa. |
| `graficos/titulo_4bpp.png` | Resto de gráficos de la pantalla de título (créditos). PNG indexado de 16 colores. |

**Letras disponibles:** á é í ó ú ü ñ Á É Í Ó Ñ ¿ ¡. Usan huecos libres de la fuente
(`{`=á, `|`=é, `}`=í, `DEL`=ó, `^`=ú, `_`=ü, `` ` ``=ñ, `#`=Á, `$`=É, `=`=Í, `@`=Ó,
`\`=Ñ, `<`=¿, `>`=¡). En los archivos se escriben normalmente. La Ú no existe y se
sustituye por U.

**Etiquetas de los diálogos:** `{espera}` (esperar botón), `{ventana}` (limpiar
ventana), `{fin}` (fin), `{nombre:01}` (nombre de personaje), `{82}Nombre{82}` (quien
habla), `{88}…{89}` / `{84}…{85}` / `{86}…{87}` (resaltados), `{80}` (guion).

### Nombres de objetos y lugares

En los menús los nombres no se escriben letra a letra: el parche inglés los dibuja como
imágenes. `insertar.py` vuelve a dibujarlos **automáticamente** con la fuente del juego
a partir de `nombres.txt`. Por eso no hace falta editar a mano los nombres que aparecen
en `celdas_37_nombres.png` ni en la parte de nombres de `celdas_38`. El renderizado
reproduce píxel a píxel los 163 gráficos ingleses.

### Menús (`menus.txt`)

Los 56 textos de menú también son imágenes: Sí/No, opciones de tienda, taberna y
entrenamiento, menú de sistema, configuración, pestañas del teclado y avisos como
" obtenido." o "No puedes llevar más objetos.". `insertar.py` los redibuja a partir de
`menus.txt` con el mismo estilo que el parche inglés (comprobado píxel a píxel). Los
guarda en celdas nuevas (0xB00–0xCFF) y reescribe todas las referencias: las 122
elecciones dentro de los eventos comprimidos y las tablas fijas.

Cada texto tiene un hueco fijo, y `insertar.py` avisa si no cabe:
- opciones de tienda y eventos: 128 px (Sí/No: 48 px);
- menú de sistema: las mismas celdas que el inglés (Save/Load solo tienen 32 px, de
  ahí "Salv."/"Carg.");
- filas con ` / ` (dificultad, velocidad del texto): una palabra por cada hueco de 32 px.

Para dibujar a mano algún otro texto con la fuente del juego:
```bash
python tools/render_texto.py "¿Guardar partida?" guardar.png
```

## Mapa técnico (ROM inglesa, LoROM 2 MB)

| Dirección | Contenido |
|---|---|
| `0x0A0000–0x0B7FFF` | Eventos (LZSS). Cada texto japonés se cambió por `FE 18 lo hi` = mostrar el mensaje N. |
| `0x11CC87` | Banco $23 bloque 44 (LZSS): nombres por defecto. |
| `0x129F7C` / `0x12E279` | Banco $25 bloques 4 y 21 (LZSS): mapa y tiles del título. |
| `0x181000` | Punteros de 3 bytes a los 1227 mensajes. |
| `0x184000` | Anchos de la fuente 16x16 (menús y nombres dibujados). |
| `0x184100` | Anchos de la fuente 8x8. |
| `0x184200` | Fuente 8x8 1bpp (`c*8`). |
| `0x188000` | **Ancho de cada letra/celda en los diálogos** (una palabra por celda, el ancho va codificado como un bit). |
| `0x184C00` / `0x184E00` | Punteros y cadenas de los nombres (máx. 15 letras). |
| `0x18C000` | Fuente 16x16 1bpp (`c*32`) de **diálogos**, menús y nombres, y menús pre-renderizados. |
| `0x190000–` | Texto de los mensajes. |
| `0x1B0000` | Listas de celdas de cada nombre gráfico. |
| `0x1BC000`, `0x1C4000` | Celdas de nombres, títulos de episodio y teclado. |

- **Codificación del texto:** ASCII. `FF` = fin, `FE 09` = salto de línea,
  `FE 07` = espera, `FE 08` = ventana nueva, `FE FF` = fin de diálogo,
  `FE 00 nn` = nombre de personaje.
- **Compresión LZSS:** byte de banderas (bit 0 primero, 1 = literal). Una referencia
  ocupa 2 bytes: offset = `lo | (hi & 0x0F) << 8` y longitud = `(hi >> 4) * 2 + 3`.
  Cabecera de 16 bits: bit 15 indica comprimido y `(cabecera & 0x7FFF) + 1` es el
  tamaño. `tools/lzss.py` descomprime y recomprime los 629 bloques del juego sin errores.
- **Celdas:** índice `i`, con `a = i − 0x300`. Si `a < 0x200`, la celda está en
  `0x18C000 + a·32`. Si no, está en el banco `$37 + (a−0x200)/0x200`, posición
  `0xC000 + resto·32`.

## Herramientas

- `tools/extraer.py`, `tools/insertar.py`: el flujo principal.
- `tools/render_texto.py`: dibuja un texto con la fuente del juego.
- `tools/lzss.py`: compresor y descompresor.
- `tools/bps.py`: aplica y crea parches BPS (`python tools/bps.py origen.sfc parche.bps destino.sfc`).
- `tools/rk_common.py`, `tools/graficos.py`: código común.
