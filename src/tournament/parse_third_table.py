"""Parsea la tabla de 495 escenarios desde el TXT y la guarda como JSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "raw" / "third_place_table_raw.txt"
OUT = ROOT / "data" / "processed" / "third_place_table.json"


def parse() -> list[dict[str, str]]:
    """Lee el TXT, devuelve lista de 495 dicts {1A: 3X, 1B: 3X, ...}."""
    lines = [l.strip() for l in RAW.read_text().splitlines() if l.strip()]

    # Cabecera: 8 lineas con los nombres de columna 1A, 1B, ...
    headers = lines[:8]
    assert headers == ["1A", "1B", "1D", "1E", "1G", "1I", "1K", "1L"], \
        f"Cabecera inesperada: {headers}"

    body = lines[8:]
    # Cada fila: 1 numero + 8 valores = 9 lineas
    rows: list[dict[str, str]] = []
    i = 0
    while i < len(body):
        row_num = body[i]
        if not row_num.isdigit():
            raise ValueError(f"Esperaba numero en linea {8+i}, vi {row_num!r}")
        values = body[i+1:i+9]
        if len(values) < 8:
            raise ValueError(f"Fila {row_num} incompleta: {values}")
        rows.append({h: v for h, v in zip(headers, values)})
        i += 9
    return rows


def validate(rows: list[dict[str, str]]) -> None:
    """Verifica que cada fila represente los 8 mejores terceros de 8 grupos distintos."""
    for idx, row in enumerate(rows, 1):
        groups = [v[1:] for v in row.values()]  # 'C' de '3C'
        if len(set(groups)) != 8:
            raise ValueError(f"Fila {idx} tiene grupos repetidos: {groups}")
        all_valid = all(v[0] == "3" and v[1] in "ABCDEFGHIJKL" for v in row.values())
        if not all_valid:
            raise ValueError(f"Fila {idx} tiene formato invalido: {row}")
    print(f"OK: {len(rows)} filas validas, todas con 8 grupos distintos.")


def main():
    rows = parse()
    validate(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"Guardado en {OUT}")
    # Cuantos conjuntos unicos de 8 grupos cubren?
    unique_sets = {frozenset(v[1:] for v in r.values()) for r in rows}
    print(f"Conjuntos unicos de 8 grupos cubiertos: {len(unique_sets)}")
    from math import comb
    print(f"Total combinaciones C(12,8) = {comb(12,8)}")


if __name__ == "__main__":
    main()
