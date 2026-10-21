import type { APIRoute, GetStaticPaths } from "astro";
import { monsterDetail } from "../../../../lib/api";
import { mapName, json } from "../../../../lib/api-data";
import { monsters, spawnsByMonster, dropsByMonster } from "../../../../lib/data";

// Um monstro, com onde aparece (spawns) e o que dropa.
export const getStaticPaths: GetStaticPaths = () =>
  monsters.map((monster) => ({ params: { id: monster.id }, props: { monster } }));

export const GET: APIRoute = ({ props }) =>
  json(monsterDetail(props.monster, (spawnsByMonster.get(props.monster.id) ?? []) as never[],
    (dropsByMonster.get(props.monster.id) ?? []) as never[], mapName));
