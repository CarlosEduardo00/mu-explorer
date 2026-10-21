import type { APIRoute, GetStaticPaths } from "astro";
import { itemDetail } from "../../../../lib/api";
import { monsterName, json } from "../../../../lib/api-data";
import { sourceItems as items, dropsByItem } from "../../../../lib/data";

// Um item, com os monstros que o dropam.
export const getStaticPaths: GetStaticPaths = () => items.map((item) => ({ params: { id: item.id }, props: { item } }));

export const GET: APIRoute = ({ props }) =>
  json(itemDetail(props.item, (dropsByItem.get(props.item.id) ?? []) as never[], monsterName));
