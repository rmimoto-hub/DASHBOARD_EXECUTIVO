#!/usr/bin/env bash
# =====================================================================
# dir-dashboard — verificacao de seguranca
#
# PROBLEMA = bloqueia o envio para o GitHub. Corrija antes de continuar.
# AVISO    = revise com a TI; nao bloqueia.
#
# Uso: make security-check
# =====================================================================
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

PROBLEMAS=0
AVISOS=0

vermelho() { printf '\033[31m%s\033[0m\n' "$1"; }
amarelo()  { printf '\033[33m%s\033[0m\n' "$1"; }
verde()    { printf '\033[32m%s\033[0m\n' "$1"; }

problema() { vermelho "  PROBLEMA: $1"; PROBLEMAS=$((PROBLEMAS + 1)); }
aviso()    { amarelo  "  AVISO:    $1"; AVISOS=$((AVISOS + 1)); }

titulo() { echo; echo "== $1"; }

# Arquivos versionaveis: exclui dependencias, builds e o proprio .git.
listar_fontes() {
  find . -type f \
    \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' \
       -o -name '*.jsx' -o -name '*.sql' -o -name '*.json' -o -name '*.yml' \
       -o -name '*.yaml' -o -name '*.env*' -o -name 'Makefile' -o -name '*.sh' \) \
    -not -path './.git/*' \
    -not -path './frontend/node_modules/*' \
    -not -path './frontend/.next/*' \
    -not -path './backend/.venv/*' \
    -not -path '*/__pycache__/*' \
    -not -path './.claude/*'
}

echo "======================================================"
echo " dir-dashboard — verificacao de seguranca"
echo "======================================================"

# ---------------------------------------------------------------------
titulo "1. Arquivos .env fora do controle de versao"

for f in backend/.env frontend/.env.local; do
  if [ -f "$f" ]; then
    if git -C . rev-parse --git-dir >/dev/null 2>&1 \
       && git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
      problema "$f esta versionado no git — remova com: git rm --cached $f"
    else
      verde "  ok: $f existe e nao esta versionado"
    fi
  fi
done

for f in backend/.gitignore frontend/.gitignore; do
  [ -f "$f" ] || aviso "$f nao existe"
done

if [ -f backend/.gitignore ] && ! grep -qx '\.env' backend/.gitignore; then
  problema "backend/.gitignore nao ignora .env"
fi
if [ -f frontend/.gitignore ] && ! grep -q '\.env\.local' frontend/.gitignore; then
  problema "frontend/.gitignore nao ignora .env.local"
fi

# ---------------------------------------------------------------------
titulo "2. Segredos escritos direto no codigo"

# Casa o termo em qualquer posicao do identificador — pega tanto
# SENHA_ADMIN= quanto MINHA_SENHA=. Falso negativo aqui e pior que falso
# positivo, entao a regra e ampla e o escape e explicito: marque a linha
# com "security-check: ok" (com a justificativa) para suprimir.
# A aspa e a virgula opcionais cobrem tambem as formas de chamada e de
# dicionario — {"SECRET_KEY": "x"} e setdefault("SECRET_KEY", "x") —, nao
# so a atribuicao direta SECRET_KEY="x".
# Aspa simples ou dupla, isolada numa variavel para nao embaralhar
# o escape do shell.
Q="[\"']"

# A aspa e a virgula opcionais cobrem tambem as formas de dicionario e
# de chamada — {"SECRET_KEY": "x"} e setdefault("SECRET_KEY", "x") —,
# nao so a atribuicao direta SECRET_KEY="x".
PADRAO_SEGREDO="(SECRET|PASSWORD|SENHA|API_?KEY|TOKEN|PRIVATE_KEY|CREDENCIAL)[A-Za-z0-9_]*$Q?[[:space:]]*[=:,][[:space:]]*$Q[^\"']{8,}"

while IFS= read -r arquivo; do
  case "$arquivo" in
    # .env.example guarda placeholders; .env/.env.local nao vao para o git;
    # este proprio script contem os padroes que procura.
    *.env.example|*/.env|*/.env.local|*/security_check.sh) continue ;;
  esac
  if achados=$(grep -nEI "$PADRAO_SEGREDO" "$arquivo" 2>/dev/null \
               | grep -v 'security-check: ok' \
               | grep -viE 'troque|exemplo|example|placeholder|seu-|sua-|xxx|<|settings\.'); then
    while IFS= read -r linha; do
      problema "possivel segredo em $arquivo:${linha%%:*}"
    done <<< "$achados"
  fi
done < <(listar_fontes)

# Chaves privadas em qualquer arquivo, nao so nos de codigo.
while IFS= read -r arquivo; do
  case "$arquivo" in */security_check.sh) continue ;; esac
  if grep -qI 'BEGIN[A-Z ]*PRIVATE KEY' "$arquivo" 2>/dev/null; then
    problema "chave privada embutida em $arquivo"
  fi
done < <(find . -type f \
  -not -path './.git/*' \
  -not -path './frontend/node_modules/*' \
  -not -path './frontend/.next/*' \
  -not -path '*/__pycache__/*' \
  -not -path './.claude/*' 2>/dev/null)

titulo "3. Configuracao do backend"

if [ -f backend/.env ]; then
  chave=$(grep '^SECRET_KEY=' backend/.env | cut -d= -f2-)
  if [ -z "$chave" ]; then
    problema "SECRET_KEY vazia em backend/.env"
  elif [ ${#chave} -lt 32 ]; then
    problema "SECRET_KEY tem ${#chave} caracteres — use ao menos 32"
  elif [[ "$chave" == *troque* ]]; then
    problema "SECRET_KEY ainda e o valor de exemplo — gere uma aleatoria"
  else
    verde "  ok: SECRET_KEY com ${#chave} caracteres"
  fi

  if grep -q '^ENVIRONMENT=production' backend/.env; then
    grep -q '^DATABASE_URL=.*root:@' backend/.env \
      && problema "producao configurada com root sem senha"
  fi
fi

# CORS aberto
if grep -rqI 'allow_origins=\["\*"\]' backend/ 2>/dev/null; then
  problema "CORS liberado para qualquer origem (allow_origins=[\"*\"])"
else
  verde "  ok: CORS restrito por configuracao"
fi

# Documentacao da API exposta em producao
if grep -qI 'is_production' backend/app/main.py 2>/dev/null; then
  verde "  ok: /docs fechado quando ENVIRONMENT=production"
else
  aviso "verifique se /docs fica fechado em producao"
fi

# ---------------------------------------------------------------------
titulo "4. Autenticacao"

if grep -rqI 'bcrypt' backend/app/core/security.py 2>/dev/null; then
  verde "  ok: senhas com bcrypt"
else
  problema "hash de senha com bcrypt nao encontrado"
fi

if grep -rqI 'algorithms=\[' backend/app/core/security.py 2>/dev/null; then
  verde "  ok: algoritmo do JWT fixado na validacao"
else
  problema "jwt.decode sem algorithms explicito aceita algoritmo arbitrario"
fi

# ---------------------------------------------------------------------
titulo "5. SQL"

if grep -rnI --include='*.py' -E 'execute\(\s*f["'\'']|execute\(\s*["'\''].*%[s]?["'\'']\s*%' backend/ 2>/dev/null; then
  problema "SQL montado com interpolacao de string — use parametros"
else
  verde "  ok: nenhuma query com interpolacao direta"
fi

# ---------------------------------------------------------------------
titulo "6. Segredo exposto ao navegador"

if [ -f frontend/.env.local ] || [ -f frontend/.env.example ]; then
  for f in frontend/.env.local frontend/.env.example; do
    [ -f "$f" ] || continue
    if grep -qE '^NEXT_PUBLIC_.*(SECRET|PASSWORD|SENHA|PRIVATE|TOKEN|KEY)=' "$f"; then
      problema "$f expoe segredo via NEXT_PUBLIC_ (vai para o navegador)"
    fi
  done
  verde "  ok: nenhum segredo sob NEXT_PUBLIC_"
fi

# ---------------------------------------------------------------------
titulo "7. Dependencias vulneraveis"

if command -v npm >/dev/null 2>&1 && [ -d frontend/node_modules ]; then
  saida=$(cd frontend && npm audit --audit-level=high 2>&1)
  if echo "$saida" | grep -q 'found 0 vulnerabilities'; then
    verde "  ok: npm audit sem vulnerabilidades altas ou criticas"
  else
    n=$(echo "$saida" | grep -oE '[0-9]+ (high|critical)' | head -1)
    problema "npm audit encontrou vulnerabilidades ($n) — rode: cd frontend && npm audit"
  fi
else
  aviso "npm audit nao executado (rode 'make install-frontend' primeiro)"
fi

# Backend: CVE conhecida e PROBLEMA, do mesmo jeito que no frontend.
# "Desatualizado" por si so nao bloqueia — vulneravel bloqueia.
if command -v pip-audit >/dev/null 2>&1; then
  if achados=$(pip-audit -r backend/requirements.txt --progress-spinner off \
               --format json 2>/dev/null); then
    n=$(echo "$achados" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print(-1); raise SystemExit
print(sum(len(dep.get('vulns', [])) for dep in d.get('dependencies', [])))
" 2>/dev/null)
    if [ "$n" = "0" ]; then
      verde "  ok: pip-audit sem vulnerabilidades no backend"
    elif [ "$n" = "-1" ] || [ -z "$n" ]; then
      aviso "nao foi possivel interpretar a saida do pip-audit"
    else
      problema "pip-audit encontrou $n vulnerabilidade(s) no backend — rode: pip-audit -r backend/requirements.txt"
    fi
  else
    aviso "pip-audit falhou (rede?) — rode manualmente antes do push"
  fi
else
  aviso "pip-audit nao instalado — rode: pip install pip-audit"
fi

# ---------------------------------------------------------------------
titulo "8. Arquivos que nao devem ir para o repositorio"

for padrao in '*.sqlite' '*.db' '*.dump' '*.sql.gz' '*.pem' '*.key' '*.p12' 'id_rsa*'; do
  while IFS= read -r encontrado; do
    aviso "arquivo sensivel por extensao: $encontrado"
  done < <(find . -name "$padrao" -not -path './.git/*' \
             -not -path './frontend/node_modules/*' 2>/dev/null)
done

if find . -name '.DS_Store' -not -path './.git/*' 2>/dev/null | grep -q .; then
  aviso ".DS_Store presente — adicione ao .gitignore"
fi

# ---------------------------------------------------------------------
echo
echo "======================================================"
if [ "$PROBLEMAS" -gt 0 ]; then
  vermelho " REPROVADO: $PROBLEMAS problema(s), $AVISOS aviso(s)"
  echo " Corrija os PROBLEMAS antes de enviar para o GitHub."
  echo "======================================================"
  exit 1
elif [ "$AVISOS" -gt 0 ]; then
  amarelo " APROVADO COM AVISOS: $AVISOS aviso(s)"
  echo " Revise os avisos com a TI (#suporte-ti)."
  echo "======================================================"
  exit 0
else
  verde " APROVADO: nenhum problema encontrado"
  echo "======================================================"
  exit 0
fi
