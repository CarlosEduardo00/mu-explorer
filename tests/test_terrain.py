"""Mapas vetoriais a partir do terreno (.att): camadas, contornos, simplificação e `d` do SVG."""
from scrapers.terrain import SIZE, contours, layer_masks, path_data, read_grid, simplify


def grid_with(cells: dict[tuple[int, int], int], fill: int = 8) -> bytes:
    data = bytearray([fill] * (SIZE * SIZE))
    for (x, y), v in cells.items():
        data[y * SIZE + x] = v
    return bytes(data)


def test_camadas_pelas_flags_e_orientacao():
    grid = grid_with({(10, 20): 0, (11, 20): 4, (12, 20): 1})   # chão, bloqueado, zona segura
    m = layer_masks(grid)
    # linha = x (vertical), coluna = y (horizontal)
    assert m["land"][10][20] and m["land"][11][20] and not m["land"][0][0]
    assert m["walk"][10][20] and not m["walk"][11][20] and m["walk"][12][20]
    assert m["safe"][12][20] and not m["safe"][10][20]


def test_quadrado_vira_um_poligono_de_quatro_cantos():
    mask = [[2 <= r < 5 and 3 <= c < 6 for c in range(10)] for r in range(10)]
    loops = contours(mask)
    assert len(loops) == 1
    assert sorted(simplify([(float(x), float(y)) for x, y in loops[0]])) == [(3, 2), (3, 5), (6, 2), (6, 5)]
    assert path_data(loops).startswith("M") and path_data(loops).endswith("Z")


def test_buraco_vira_segundo_contorno_e_area_minima_some():
    mask = [[1 <= r < 8 and 1 <= c < 8 and not (r == 4 and c == 4) for c in range(10)] for r in range(10)]
    assert len(contours(mask)) == 2
    assert path_data(contours(mask)).count("M") == 1   # o buraco de 1 casa fica abaixo da área mínima


def test_cabecalho_variavel_usa_os_ultimos_65536_bytes(tmp_path):
    f = tmp_path / "x.att"
    f.write_bytes(b"\x00\xff\xff\xaa\xbb" + bytes(SIZE * SIZE))
    assert len(read_grid(f)) == SIZE * SIZE and read_grid(f)[0] == 0
