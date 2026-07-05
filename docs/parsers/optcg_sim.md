# Parser del log de OPTCG Sim — Documento de referencia

Los archivos son **texto plano** (extension `.log` o `.txt`, mismo contenido). Tienen **dos capas intercaladas**.

## 1. Capa humana (semantica)

Lineas con el jugador entre corchetes y referencias a cartas. **Dos formatos** de referencia a card_id (el parser debe manejar ambos):
- Variante A: `[<mark><link="OP16-079">OP16-079</link></mark>]`
- Variante B: `["OP16-079">OP16-079]`

Regex unificada: buscar `[A-Z]{2,4}-\d{3}` en cualquier linea (mas robusto que parsear el markup).

## 2. Capa maquina (estado) — lineas `RZ1`

Formato: `RZ1|<seq>|<player 1|2>|<card_id|"Don">|<action>|<c5>|<c6>|<c7>|<c8>|<c9>|<c10>|<c11>|<c12?>`
- Header: `RZ1|HDR|1.40a|1|RZ1`
- `action=0` -> robar del deck (c5=deck restante, c7=hand count antes de la robada)
- `action=1` -> jugar/desplegar/counter/return mulligan (contexto depende de la linea humana adyacente)
- `card="Don"` -> operacion de Don (c7 = instance ID del target: `9900+`=lider, `100+`=personajes)
- `c9` = flag `goes_first` (1/0)

## 3. Tipos de lineas humanas a reconocer

| Categoria | Patrones |
|---|---|
| Header | `Waiting for a Connection with Room ID:<id>`, `<user> Has Connected`, `Version is <v>`, `<user> Leader is <name> [<id>]`, `Chose to go Second`, `Will select turn order` |
| Robo | `Drew card from deck: <name> [<id>]`, `Draw 1 Card`, `Draw 2 Don`, `Draw 1 Don`, `Draw N Rested Don` |
| Mulligan | `Hand before Mulligan: [...]`, `Mulligan`, `Hand after Mulligan: [...]` |
| Estado | `Hand: [...]`, `Board: [...]`, `Trash: [...]`, `Life: <n>` |
| Jugar | `Deploy <name> [<id>]`, `Attach N Don to <name> [<id>] (N Total)` |
| Ataque | `<atk> [<id>] attacking <def> [<id>]` -> `<atk> [<id>][<pow>] vs <def> [<id>][<pow>]` -> `<def> hit for 1 damage` / `Attack Fails` / `<def> [<id>] Destroyed` |
| Counter | `Discard <name> [<id>] for Counter <1000\|2000>` |
| Efectos | `<source> [<id>]: <descripcion>` (Draw N Card, Trash X, Reveal and Draw Y, Buff Z +/-N for the Combat, Rest X, Give Rush, Deployed X from Trash, Minus N Don, etc.) |
| Trigger | `<card> [<id>]: Activate Trigger` |
| Fin | `End Turn`, `Concedes!`, `GameOver`, `Downloaded the Combat Log!` (ruido, ignorar) |

## 4. Estrategia del parser

- **Stateful, single-pass, linea por linea**.
- Mantener estado por jugador: `leader_id, life, hand: [card_id], board: [{instance_id, card_id, don_attached, rested, rush}], trash: [card_id], don_active, don_rested, deck_count`.
- **Cross-referenciar** cada RZ1 con la linea humana adyacente para saber el significado semantico (RZ1 no distingue deploy de counter de mulligan-return).
- **Instance IDs** (c7 en lineas Don, c12 en deploy con efecto) para trackear copias individuales en mesa.
- Los **snapshots** (`Hand/Board/Trash/Life`) son puntos de reconciliacion: si el estado reconstruido difiere, se corrige con el snapshot (ground truth).
- **Turno** = secuencia entre dos `End Turn`. Turno del jugador se infiere de `Draw N Don` y de las lineas `[user] ...` activas.
- **Resultado**: `Concedes!` (quien concede pierde) o `GameOver` (life 0 -> ultimo atacante gana).

## 5. Particularidades detectadas

- **Usernames con zero-width spaces**: `Player#1234` contiene caracteres invisibles. Normalizar al detectar `self_user`.
- **Dos formatos de markup**: el parser debe detectar automaticamente cual usa cada log (A o B) y manejar ambos.
- **eventcache**: binario de 792 bytes, ignorar (no es un log).
- **Logs en dos directorios**: `Datos/CombatLogs/` (7 logs) y `Datos/CombatLogs/AutoSaved/` (93 logs). Mismo formato.
