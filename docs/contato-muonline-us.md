# Pedido de acesso ao muonline.us (rascunho)

O muonline.us responde 403 com o desafio anti-bot da Cloudflare em todas as páginas, então não
coletamos de lá (ver CLAUDE.md). Este é o pedido de acesso para mandar pelo canal de contato do site
(no navegador, a página abre normalmente para pessoas).

---

**Subject:** Data access request for a non-commercial MU Online fan database

Hi,

We are two developers building MU Explorer, a non-commercial fan site with an item, monster and
drop-location database for MU Online (https://github.com/CarlosEduardo00/mu-explorer).

Your drop database (/drop/item/... and /drop/location/...) is the best source we found for item
group/index codes and drops by map. We would like to use it, with clear credit and a link back to
muonline.us on every page that shows the data.

Would you be willing to either:

1. share an export of the item/drop data (CSV/JSON, any format is fine), or
2. allow our crawler through Cloudflare (User-Agent `mu-explorer-bot/0.1`), which follows
   robots.txt and makes at most one request per second?

We will not do anything you are not comfortable with, and we are happy to follow any conditions.

Thanks!
Carlos — MU Explorer
