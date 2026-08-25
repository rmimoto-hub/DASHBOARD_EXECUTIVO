# Decisões técnicas

Registro das escolhas que se afastam do template base da KAMI CO., ou que não
são óbvias pelo código. Serve para a TI revisar e para quem pegar o projeto
depois entender o porquê.

Data de referência: 24/08/2026.

---

## 1. Next.js 16 em vez de 14

**O template pede:** Next.js 14.

**O que foi feito:** Next.js 16.3.2 + React 19.

**Por quê:** `npm audit` na versão 14.2.21 apontou 30 vulnerabilidades — 1
crítica e 4 de severidade alta nos pacotes. Entre elas:

- Authorization Bypass in Next.js Middleware
- Múltiplos SSRF (Server Actions, rewrites, WebSocket upgrades)
- Cache poisoning em respostas de React Server Components
- XSS em App Router com nonce de CSP
- Path traversal no PostCSS (leitura arbitrária de arquivos `.map`)

Não existe versão corrigida na linha 14.x — o intervalo vulnerável cobre tudo
até `16.3.0-preview.10`. A correção disponível é a 16.3.2.

O README do template também exige `make security-check` e "corrigir todos os
PROBLEMAS antes de continuar". Permanecer no 14 significaria reprovar no próprio
portão de segurança do processo.

**Risco da migração:** baixo neste código. O frontend usa apenas o básico do App
Router — componentes cliente, `fetch`, `useRouter`. Não há middleware, Image
Optimization nem Server Actions, que são justamente as áreas afetadas. O build
passou sem nenhuma alteração de código.

**Depois da migração:** `npm audit` reporta 0 vulnerabilidades.

**Pendência:** comunicar à TI para alinhar o template base.

---

## 2. `bcrypt` direto, sem `passlib`

**O que foi feito:** `app/core/security.py` usa a biblioteca `bcrypt`
diretamente.

**Por quê:** a combinação usual `passlib[bcrypt]` emite
`AttributeError: module 'bcrypt' has no attribute '__about__'` com bcrypt 4.x.
O `passlib` está sem lançamento desde 2020 e não reconhece o novo formato de
versão. O erro é capturado internamente e o hash funciona, mas é uma dependência
morta na camada de autenticação — o pior lugar para carregar código sem
manutenção.

Usar `bcrypt` direto elimina a dependência e o aviso. A validação de limite de
72 bytes foi adicionada explicitamente: o bcrypt trunca silenciosamente acima
disso, o que aceitaria uma senha longa verificando apenas o começo dela.

---

## 3. Banco `dir_dashboard` com underscore

**O que foi feito:** o sistema chama-se `dir-dashboard` (padrão `area-funcao`),
mas o banco é `dir_dashboard`.

**Por quê:** hífen em nome de banco MySQL exige backtick em toda referência,
inclusive dentro da `DATABASE_URL`. Underscore evita uma classe inteira de erro
de sintaxe sem custo nenhum.

---

## 4. Atingimento invertido para indicadores "menor é melhor"

**O que foi feito:** em `services/painel.py`, o atingimento é `valor / meta`
para indicadores `MAIOR`, e `meta / valor` para `MENOR`.

**Por quê:** inadimplência de 4,3% contra meta de 3% dava 142% de atingimento
pela razão direta. Num painel de diretoria, 142% lê-se como desempenho acima do
esperado — quando é o oposto: a meta foi estourada.

Com a inversão, ">100% é bom" vale para todo indicador, sem o leitor precisar
saber a direção de cada um.

---

## 5. Ambiente em espaço de usuário (conda)

**O que foi feito:** Python, Node, MySQL e `gh` instalados via Miniforge em
`~/miniforge3/envs/dir-dashboard-80`. MySQL com dados em `~/mysql-data`.

**Por quê:** a máquina não tem senha de administrador nem Homebrew. Instalador
`.dmg` do MySQL, Homebrew em `/opt/homebrew` e qualquer `sudo` estão
indisponíveis.

Tentativa descartada: Homebrew clonado em `~/homebrew`. Funciona, mas não recebe
os binários pré-compilados (bottles são fixados a `/opt/homebrew`), então tenta
compilar o MySQL do código-fonte — o build falhou e não é configuração suportada
pelo projeto Homebrew.

O conda-forge fornece binários prontos para `osx-arm64`, sem compilação.

**Pendência:** informar a TI que a máquina não tem privilégios de administrador
— isso vai reaparecer em outras ferramentas.

---

## 6. MySQL 8.0.33 e não 9.7

O conda-forge oferece MySQL 9.7 como padrão. Fixado em 8.0.33 para alinhar com
o template e com o RDS de produção. Divergência de major entre desenvolvimento e
produção esconde diferenças de comportamento até o deploy.

**Pendência:** confirmar com a TI a versão exata do RDS.

---

## 7. Supressão explícita no `security-check`

**O que foi feito:** o detector de segredos casa amplamente e aceita o marcador
`security-check: ok` na mesma linha para suprimir um achado.

**Por quê:** a primeira versão usava fronteira de palavra para não confundir
`CHAVE_TOKEN` (nome de chave do localStorage) com um segredo. Isso eliminou o
falso positivo, mas criou um falso negativo: `SENHA_ADMIN = "..."` deixou de ser
detectado, porque o padrão exigia o `=` imediatamente após a palavra-chave.

Num verificador de segurança, falso negativo é pior que falso positivo. A regra
voltou a ser ampla, e a exceção passou a ser explícita e auditável — cada
supressão fica no código, com justificativa ao lado, como em qualquer linter.

Validado plantando 5 problemas reais (segredo literal, token de API, chave
privada, `SECRET_KEY` curta, segredo sob `NEXT_PUBLIC_`): todos detectados.

---

## 8. Senha de teste fora do repositório

**O que foi feito:** a senha dos usuários de `make seed-fake` vem de
`SEED_SENHA_PADRAO`, em `backend/.env`. Não aparece em nenhum arquivo
versionado — nem no código, nem no README, nem no `.env.example`. Sem a
variável definida, o seed aborta com instrução.

**Por quê:** o repositório `rmimoto-hub/DASHBOARD_EXECUTIVO` está público. A
senha literal no código revelaria o padrão de senha corporativo da KAMI CO.
(`Kamico@AAAA`) para qualquer pessoa na internet — e variações previsíveis do
mesmo padrão viram material de ataque contra outras contas da empresa.

E-mails de teste e estrutura da API são exposição arquitetural aceitável num
repositório aberto; um padrão de credencial não é.

**Nota sobre o histórico:** a primeira versão do commit inicial continha a senha.
Como esse commit nunca foi enviado, ele foi reescrito antes do push — a senha
não existe em nenhum histórico publicado. Se algum dia ela vazar num commit já
enviado, remover o arquivo não basta: é preciso reescrever o histórico e trocar
a senha.

---

## Pendências para a TI

1. Alinhar a versão do Next.js no template base (item 1).
2. Registrar `dir-dashboard` + usuário do GitHub (`#suporte-ti`).
3. Máquina sem privilégios de administrador (item 5).
4. Confirmar a versão do MySQL em produção (item 6).
5. O repositório `rmimoto-hub/DASHBOARD_EXECUTIVO` está vazio — não existe
   template base publicado. Toda a estrutura deste projeto foi construída a
   partir da especificação do README, não clonada de um template oficial.
