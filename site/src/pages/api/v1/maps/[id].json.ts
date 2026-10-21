import type { APIRoute, GetStaticPaths } from "astro";
import { mapDetail } from "../../../../lib/api";
import { monsterName, json } from "../../../../lib/api-data";
import { maps, spawnsByMap } from "../../../../lib/data";

// Um mapa, com os spawns (spots: monstro e coordenadas).
export const getStaticPaths: GetStaticPaths = () => maps.map((map) => ({ params: { id: map.id }, props: { map } }));

export const GET: APIRoute = ({ props }) =>
  json(mapDetail(props.map, (spawnsByMap.get(props.map.id) ?? []) as never[], monsterName));
