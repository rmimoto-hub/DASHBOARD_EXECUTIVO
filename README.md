# dir-dashboard

Painel de Gestão Executiva — KAMI CO.

Indicadores gerenciais consolidados por área, com metas, variação mês a mês e
percentual de atingimento.

---

## Stack

| Camada    | Tecnologia                          |
|-----------|-------------------------------------|
| Frontend  | React 19 + Next.js 16 + Tailwind CSS |
| Backend   | Python 3.12 + FastAPI               |
| Banco     | MySQL 8.0                           |
| Auth      | JWT (PyJWT) + bcrypt                |
| Produção  | AWS EC2 + RDS (gerenciado pela TI)  |

> **Nota sobre a versão do Next.js:** o template base da KAMI CO. especifica
> Next.js 14. Esta versão foi elevada para 16 porque a linha 14 acumula 30
> vulnerabilidades conhecidas (uma crítica), sem correção disponível dentro da
> própria linha 14.x — incluindo *authorization bypass* em middleware e SSRF.
> Manter o 14 reprovaria no `make security-check` exigido pelo próprio processo.
> Ver [docs/decisoes.md](docs/decisoes.md).

---

## Ambiente local

Esta máquina não tem privilégios de administrador, então todo o ferramental vive
em espaço de usuário, via conda (Miniforge) — sem `sudo`, sem Homebrew.

O ambiente `dir-dashboard-80` reúne Python 3.12, Node 20, MySQL 8.0.33 e o `gh`.

```bash
source ~/miniforge3/etc/profile.d/conda.sh && conda activate dir-dashboard-80
```

Confira o estado do ambiente a qualquer momento:

```bash
make status
```

---

## Primeiros passos

```bash
make mysql-start     # sobe o MySQL local
make install         # dependências de backend e frontend
make db-schema       # cria o banco e aplica o schema
make seed-fake       # carrega dados fictícios
make dev             # sobe backend e frontend
```

- Backend: http://localhost:8000 — documentação em http://localhost:8000/docs
- Frontend: http://localhost:3000

### Usuários de teste

Criados por `make seed-fake`. A senha de todos vem de
`SEED_SENHA_PADRAO` em `backend/.env` — use o padrão interno da KAMI CO.
para ambientes de teste (consulte o guia de onboarding ou a TI).

| E-mail                | Perfil    | Pode                          |
|-----------------------|-----------|-------------------------------|
| admin@kamico.com.br   | ADMIN     | tudo, inclusive criar indicador |
| maria@kamico.com.br   | USER      | ler e registrar medições      |
| joao@kamico.com.br    | USER      | ler e registrar medições      |
| ana@kamico.com.br     | READ_ONLY | apenas ler                    |
| carlos@kamico.com.br  | USER      | ler e registrar medições      |

---

## Comandos

Rode `make help` para a lista completa. Os principais:

| Comando               | O que faz                                      |
|-----------------------|------------------------------------------------|
| `make dev`            | sobe backend e frontend juntos                 |
| `make dev-backend`    | sobe só a API                                  |
| `make dev-frontend`   | sobe só o painel                               |
| `make seed-fake`      | carrega dados fictícios (idempotente)          |
| `make db-schema`      | aplica `database/schema.sql`                   |
| `make db-reset`       | **apaga** e recria o banco (pede confirmação)  |
| `make test`           | testes do backend (58 testes, sem MySQL)       |
| `make check`          | testes + lint + verificação de segurança       |
| `make security-check` | verificação obrigatória antes do push          |
| `make build`          | build de produção do frontend                  |
| `make status`         | versões e estado do MySQL                      |

---

## Testes

```bash
make test
```

Rodam contra SQLite em memória — não precisam de MySQL de pé e não tocam o banco
de desenvolvimento. Cobrem autenticação, controle por perfil, os cálculos do
painel e o módulo de senha/JWT.

## Antes de enviar para o GitHub

```bash
make check
```

Roda testes, lint e a verificação de segurança de uma vez. Para só a segurança:

```bash
make security-check
```

`PROBLEMA` bloqueia o envio — corrija antes de continuar.
`AVISO` pode ser revisado com a TI no `#suporte-ti`.

O verificador cobre: `.env` versionado, segredos no código, chaves privadas,
força da `SECRET_KEY`, CORS aberto, `/docs` exposto em produção, hash de senha,
algoritmo do JWT, SQL por interpolação, segredo sob `NEXT_PUBLIC_` e CVEs nas
dependências — `npm audit` no frontend e `pip-audit` no backend, ambos
bloqueando o push.

Quando um achado for legítimo e intencional, anote a linha com
`security-check: ok` e a justificativa — nada é ignorado em silêncio.

Depois:

```bash
git add .
git commit -m "v1.0 descricao-do-que-foi-feito"
git push origin main
```

E avise a TI no canal `#deploys` do Teams: nome do sistema, o que mudou, e se
precisa de novo deploy.

---

## Estrutura

```
backend/
  app/
    api/          rotas (auth, indicadores) e dependências de permissão
    core/         config, conexão com o banco, senha e JWT
    models/       tabelas via SQLAlchemy
    schemas/      contratos de entrada e saída (Pydantic)
    services/     regra de negócio do painel
  scripts/        seed de dados fictícios
  tests/          testes (pytest, SQLite em memória)
database/
  schema.sql      DDL completo
frontend/
  app/            páginas (App Router)
  components/     componentes de UI
  lib/            cliente da API e formatação pt-BR
scripts/
  security_check.sh
docs/
  decisoes.md     decisões técnicas e seus motivos
```

---

## Dúvidas

- Técnicas: converse com o Claude Code
- Infraestrutura: `#suporte-ti` no Teams
- Deploy: `#deploys` no Teams
