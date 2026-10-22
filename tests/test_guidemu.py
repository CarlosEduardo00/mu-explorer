"""Guide MU Online: leitura dos JS do site, parse de mapas/spots/monstros, correspondência com os mapas do site,
spots de farm, terreno a partir das imagens e guias (páginas renderizadas)."""
import json
import re
from pathlib import Path

from scrapers.guidemu.bundle import chunk_files, find_json, main_script, unescape_js
from scrapers.guidemu.parse import fit_transform, monster_record, parse_maps
from scrapers.guidemu.places import place, zone_label
from scrapers.spots import guide_groups, guide_spots

FIX = Path(__file__).parent / "fixtures" / "guidemu"
META = {"fetched_at": "2026-10-22T13:08:01Z"}


def fixture_data():
    maps = find_json((FIX / "chunk-maps.js").read_text(encoding="utf-8"), "cantidadmobs")
    monsters = find_json((FIX / "chunk-monsters.js").read_text(encoding="utf-8"), "minattack")
    return maps, monsters


def test_unescape_e_json_em_string_literal():
    assert unescape_js(r"a\x20b\x22é\'") == 'a b"é\''
    maps, monsters = fixture_data()
    assert [m["name"] for m in maps] == ["Lorencia", "Atlans", "Kalima"]
    assert {"name", "level", "hp", "minattack"} <= set(monsters[0])


def test_tabela_de_chunks_do_main_ofuscado():
    # Mesmo formato do main.js real: tabela de strings rotacionada e a função que monta a URL do chunk.
    strings = ["b0", "static/js/", "abc12345", ".chunk.js", "def67890", "x"]
    shift = 2   # o ofuscador gira a tabela: dec(i) = strings[(i - base + shift) % n]
    def idx(s):
        return hex((strings.index(s) - shift) % len(strings) + 0x10)
    main = ("function a1_0x10(_0x1,_0x2){const _0x3=a1_0x99();return a1_0x10=function(_0x4,_0x5){_0x4=_0x4-0x10;"
            "let _0x6=_0x3[_0x4];return _0x6;},a1_0x10(_0x1,_0x2);}"
            "function a1_0x99(){const _0x7=[" + ",".join(f"'{s}'" for s in strings) + "];a1_0x99=function(){return _0x7;};return a1_0x99();}"
            f"_0x8['u']=_0x9=>_0xa({idx('static/js/')})+_0x9+'.'+{{0x20dd:_0xa({idx('abc12345')}),0x136c:'ffff0000',"
            f"0x2043:_0xa({idx('def67890')})}}[_0x9]+_0xa({idx('.chunk.js')})")
    assert chunk_files(main) == {8413: "static/js/8413.abc12345.chunk.js", 4972: "static/js/4972.ffff0000.chunk.js",
                                 8259: "static/js/8259.def67890.chunk.js"}
    assert main_script('<script defer="defer" src="/static/js/main.ec0bf085.js"></script>') == "/static/js/main.ec0bf085.js"


def test_parse_de_mapas_spots_e_monstros():
    maps, monsters = fixture_data()
    groups, spots, images = parse_maps(maps, monsters, META)
    assert [g["name"] for g in groups] == ["Lorencia", "Atlans", "Kalima"]
    assert groups[1]["zones"] == ["Atlans 1", "Atlans 2", "Atlans 3"]
    first = spots[0]
    assert (first["map"], first["zone"], first["x"], first["y"], first["count"], first["heat"]) == ("Lorencia", None, 44, 57, 5, "hot")
    assert first["monsters"] and first["monster_ids"][0] == first["monsters"][0].lower().replace(" ", "-")
    assert {s["heat"] for s in spots} <= {"low", "mid", "hot"}
    lorencia = next(i for i in images if i["map"] == "Lorencia")
    assert lorencia["key"] == "lorencia" and lorencia["error"] < 2 and lorencia["points"] >= 5
    record = monster_record(monsters[0], META)
    assert record["source"] == "guidemu" and record["id"] == record["name"].lower().replace(" ", "-")


def test_transformacao_jogo_para_imagem_descarta_ponto_fora():
    # left = 0,2·(x + y), top = 0,2·(x − y) + 50 (o minimapa girado do jogo), com um spot errado no meio
    pts = [(x, y, 0.2 * (x + y), 0.2 * (x - y) + 50) for x, y in [(10, 20), (100, 40), (200, 220), (50, 150), (120, 130)]]
    pts.append((60, 60, 90.0, 10.0))
    matrix, err, used = fit_transform(pts)
    assert used == 5 and err < 0.01
    assert [round(v, 3) for v in matrix[0]] == [0.2, 0.2, 0] and [round(v, 3) for v in matrix[1]] == [0.2, -0.2, 50]


def test_zonas_do_guia_viram_mapa_ou_subcategoria():
    assert place("Lorencia", None) == ("lorencia", None)
    assert place("Elbeland", None) == ("elveland", None)
    assert place("Atlans", "Atlans 2") == ("atlans", "Atlans 2")
    assert place("Kalima", "Kalima 3") == ("kalima-3", None)
    assert place("Deep Dungeon", "2nd Floor") == ("deep-dungeon-2", None)
    assert place("Acheron", "Alkamar") == ("acheron", "Alkamar")
    assert place("Acheron", "Nars") == ("nars", None)
    assert place("Swamp of Peace", "Zone 3") == ("swamp-of-calmness", "Área 3")
    assert zone_label("4th Floor") == "Andar 4"


def test_spots_do_guia_e_barra_de_mapas():
    maps, monsters = fixture_data()
    groups, rows, _ = parse_maps(maps, monsters, META)
    site_monsters = [{"id": m["name"].lower().replace(" ", "-"), "name": m["name"], "level": m["level"]} for m in monsters]
    site_maps = [{"id": i, "name": n} for i, n in [("lorencia", "Lorencia"), ("atlans", "Atlans"), ("kalima", "Kalima"),
                                                    ("kalima-1", "Kalima 1"), ("kalima-2", "Kalima 2")]]
    spots = guide_spots(rows, monsters, site_monsters, site_maps)
    assert spots[0]["id"] == "lorencia-1" and spots[0]["zone"] is None and spots[0]["total"] == 5
    assert (spots[0]["x_min"], spots[0]["x_max"]) == (41, 47)
    atlans = [s for s in spots if s["map_id"] == "atlans"]
    assert atlans[0]["zone"] == "Atlans 1" and atlans[0]["id"] == "atlans-1"
    multi = next(s for s in spots if len(s["monsters"]) > 1)
    assert all(m["count"] is None for m in multi["monsters"])   # o guia só dá o total do spot
    assert {s["map_id"] for s in spots if s["map_id"].startswith("kalima")} == {"kalima-1", "kalima-2"}
    bar = guide_groups(groups, site_maps)
    assert [g["id"] for g in bar] == ["lorencia", "atlans", "kalima"]
    assert bar[1]["entries"][1] == {"label": "Atlans 2", "map_id": "atlans", "zone": "Atlans 2", "frame": None}
    assert [e["map_id"] for e in bar[2]["entries"]] == ["kalima-1", "kalima-2"]


def test_area_da_imagem_em_coordenadas_do_jogo():
    from PIL import Image
    from scrapers.guidemu.parse import image_frame
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for i in range(20, 41):
        for j in range(30, 51):
            img.putpixel((i, j), (90, 90, 100, 255))
    # left = y / 2,56 %, top = x / 2,56 %: o retângulo opaco left 20..40 %, top 30..50 % é x 76,8..128, y 51,2..102,4
    frame = image_frame(img, [[0, 1 / 2.56, 0], [1 / 2.56, 0, 0]])
    assert frame == [[76.8, 51.2], [76.8, 102.4], [128.0, 102.4], [128.0, 51.2]]


def test_mascara_do_terreno_pela_imagem(tmp_path):
    from PIL import Image
    from scrapers.terrain import image_mask
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for i in range(20, 40):          # quadrado opaco: left 20..40 %, top 20..40 %
        for j in range(20, 40):
            img.putpixel((i, j), (90, 90, 100, 255))
    # transformação simples: left = y / 2,56 %, top = x / 2,56 % (casa (x, y) -> pixel (y, x) / 2,56)
    m = image_mask(img, [[0, 1 / 2.56, 0], [1 / 2.56, 0, 0]])
    assert m[70, 70] and not m[10, 10] and not m[70, 120]
    assert 0.03 < m.mean() < 0.05


def _guide(name: str) -> dict:
    from scrapers.guidemu.guides import parse_guide
    html = (FIX / f"guide-{name}.html").read_text(encoding="utf-8")
    meta = json.loads((FIX / f"guide-{name}.meta.json").read_text(encoding="utf-8"))
    return parse_guide(html, meta)


def _texts(blocks: list[dict]):
    """Todos os textos ({t, m}) dos blocos, inclusive dentro de cartões, grades, abas e acordeões."""
    for b in blocks:
        for key in ("text", "title", "label"):
            if isinstance(b.get(key), dict):
                yield b[key]
        yield from b.get("items", []) if b["type"] == "list" else ()
        for row in ([b.get("head", [])] + b.get("rows", [])) if b["type"] == "table" else ():
            yield from (c for c in row if c)
        yield from _texts(b.get("blocks", []))
        yield from _texts(b.get("items", []) if b["type"] == "grid" else [])
        for part in b.get("tabs", []) + (b.get("items", []) if b["type"] == "accordion" else []):
            if part.get("label") or part.get("title"):
                yield part.get("label") or part.get("title")
            yield from _texts(part["blocks"])


def test_guia_de_quest_cartoes_e_termos_do_jogo():
    g = _guide("sebina")
    assert g["id"] == "quest-2nd-class-sebina-the-priest" and g["series"] == "class-change"
    assert g["title"] == {"t": "[Quest 2nd Class] Sebina The Priest"}
    assert [s["id"] for s in g["siblings"]][:2] == ["quest-2nd-class-sebina-the-priest", "quest-marlon"]
    first = g["blocks"][0]
    assert first["type"] == "card" and first["kind"] == "quest" and first["blocks"][0]["type"] == "image"
    assert first["blocks"][0]["src"] in g["image_urls"]
    # Nomes entre aspas simples viram termos (não se traduzem); "Muren Reksmilon's" não.
    intro = first["blocks"][2]["text"]
    assert intro["t"].startswith("NPC {0} is a great priestess of the {1}.")
    assert "'Scroll of the Emperor'" in intro["m"] and "Reksmilon's battle" in intro["t"]
    sections = [b["text"]["t"] for b in g["blocks"] if b["type"] == "heading" and b.get("style") == "section"]
    assert sections[0] == "[Part 1] FIND THE SCROLL OF THE EMPEROR"
    texts = list(_texts(g["blocks"]))
    assert len(texts) > 80 and all(t["t"].strip() for t in texts)


def test_guia_com_abas_guarda_o_conteudo_de_cada_aba():
    g = _guide("second-wings")
    assert g["id"] == "second-wings" and g["series"] == "wings"
    tabs = next(b for b in g["blocks"] if b["type"] == "tabs")["tabs"]
    assert [t["label"]["t"] for t in tabs] == ["Season 12 or below", "Season 13 or higher"]
    assert all(t["blocks"] for t in tabs)
    first = tabs[0]["blocks"][0]["items"][0]["blocks"]
    assert first[0] == {"type": "heading", "level": 2, "text": {"t": "Wings &amp; Cloaks"}}
    assert first[2]["text"] == {"t": "For the wings we will need the {0} and for the cloaks the {1}.",
                                "m": ["Loch's Feather", "Crest of Monarch"]}


def test_texto_com_termos_negrito_e_destaque():
    from selectolax.lexbor import LexborHTMLParser
    from scrapers.guidemu.guides import guide_id, is_term, rich
    node = LexborHTMLParser('<p>Find the <span class="text-accent">Ring of Honor</span> near <b>Tarkan</b> '
                            "(Giaon's revolt) &amp; give it to 'Marlon'. <span class=\"text-accent\">Successful "
                            'Result:</span> done</p>').css_first("p")
    assert rich(node) == {"t": 'Find the {0} near <b>Tarkan</b> (Giaon\'s revolt) &amp; give it to {1}. '
                               '<em class="accent">Successful Result:</em> done',
                          "m": ["Ring of Honor", "'Marlon'"]}
    assert is_term("Scroll of the Emperor") and not is_term("Successful Result:")
    assert guide_id("elemental-system/errtels-guide") == "errtels" and guide_id("artifact-system") == "artifact-system"


def test_traducao_dos_guias_mantem_termos_e_marcacao():
    """data/curated/translations/guides.pt-BR.json: mesmos {n}, <b>, <em> e <br> do original (senão o site ignora)."""
    path = Path(__file__).resolve().parents[1] / "data" / "curated" / "translations" / "guides.pt-BR.json"
    pt = json.loads(path.read_text(encoding="utf-8"))
    marks = lambda t: sorted(re.findall(r"\{\d+\}|</?(?:b|em)\b[^>]*>|<br>", t))
    bad = [k for k, v in pt.items() if marks(k) != marks(v) or not v.strip()]
    assert not bad, bad[:5]
    texts = [t["t"] for name in ("sebina", "second-wings") for t in _texts(_guide(name)["blocks"])]
    assert sum(t in pt for t in texts) / len(texts) > 0.6
