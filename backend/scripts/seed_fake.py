"""Popula o banco com dados ficticios para testes.

Uso:  make seed-fake     (ou)  python -m scripts.seed_fake

Cria 5 usuarios de teste e uma serie de 12 meses de medicoes para
cada indicador. Idempotente: rodar de novo nao duplica registros.
"""
import random
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Permite rodar o script direto, sem instalar o pacote.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_senha  # noqa: E402
from app.models.indicador import Indicador, Medicao, MelhorDirecao  # noqa: E402
from app.models.usuario import Perfil, Usuario  # noqa: E402

# A senha dos usuarios de teste vem de backend/.env (SEED_SENHA_PADRAO) e
# nao do codigo, para nao ficar versionada. Lida em main(), via Settings.

USUARIOS = [
    ("Administrador", "admin@kamico.com.br", Perfil.ADMIN),
    ("Maria Silva", "maria@kamico.com.br", Perfil.USER),
    ("Joao Souza", "joao@kamico.com.br", Perfil.USER),
    ("Ana Costa", "ana@kamico.com.br", Perfil.READ_ONLY),
    ("Carlos Pereira", "carlos@kamico.com.br", Perfil.USER),
]

INDICADORES = [
    ("FAT_MENSAL", "Faturamento mensal", "BRL", "COMERCIAL",
     MelhorDirecao.MAIOR, 4_200_000, 0.08),
    ("MARGEM_BRUTA", "Margem bruta", "PCT", "FINANCEIRO",
     MelhorDirecao.MAIOR, 38, 0.05),
    ("INADIMPLENCIA", "Inadimplencia sobre carteira", "PCT", "FINANCEIRO",
     MelhorDirecao.MENOR, 3.2, 0.15),
    ("TICKET_MEDIO", "Ticket medio por pedido", "BRL", "COMERCIAL",
     MelhorDirecao.MAIOR, 1_850, 0.06),
    ("PRAZO_ENTREGA", "Prazo medio de entrega", "DIAS", "OPERACOES",
     MelhorDirecao.MENOR, 4.5, 0.10),
    ("GIRO_ESTOQUE", "Giro de estoque", "NUM", "OPERACOES",
     MelhorDirecao.MAIOR, 6.2, 0.07),
    ("NPS", "Net Promoter Score", "NUM", "COMERCIAL",
     MelhorDirecao.MAIOR, 62, 0.06),
    ("TURNOVER", "Turnover mensal", "PCT", "RH",
     MelhorDirecao.MENOR, 2.1, 0.20),
]

MESES = 12


def _competencias(qtd: int) -> list[date]:
    """Os `qtd` meses encerrados mais recentes, do mais antigo ao mais novo."""
    hoje = date.today()
    ref = date(hoje.year, hoje.month, 1)
    saida = []
    for i in range(qtd, 0, -1):
        ano, mes = divmod((ref.year * 12 + ref.month - 1) - i, 12)
        saida.append(date(ano, mes + 1, 1))
    return saida


def main() -> int:
    settings = get_settings()
    if settings.is_production:
        print("ABORTADO: seed de dados ficticios nao roda em producao.")
        return 1

    senha_padrao = settings.SEED_SENHA_PADRAO
    if not senha_padrao:
        print(
            "ABORTADO: defina SEED_SENHA_PADRAO em backend/.env "
            "(veja .env.example)."
        )
        return 1

    # Semente fixa: rodadas diferentes geram os mesmos numeros.
    rng = random.Random(20260824)
    db = SessionLocal()
    criados_u = criados_i = criados_m = 0

    try:
        senha_hash = hash_senha(senha_padrao)
        for nome, email, perfil in USUARIOS:
            if db.scalar(select(Usuario).where(Usuario.email == email)):
                continue
            db.add(
                Usuario(
                    nome=nome, email=email, senha_hash=senha_hash, perfil=perfil
                )
            )
            criados_u += 1
        db.commit()

        for codigo, nome, unidade, area, direcao, base, vol in INDICADORES:
            ind = db.scalar(select(Indicador).where(Indicador.codigo == codigo))
            if ind is None:
                ind = Indicador(
                    codigo=codigo,
                    nome=nome,
                    descricao=f"Indicador de {area.lower()} — dados ficticios.",
                    unidade=unidade,
                    area=area,
                    melhor_direcao=direcao,
                )
                db.add(ind)
                db.flush()
                criados_i += 1

            valor = float(base)
            for comp in _competencias(MESES):
                existe = db.scalar(
                    select(Medicao).where(
                        Medicao.indicador_id == ind.id,
                        Medicao.competencia == comp,
                    )
                )
                if existe is not None:
                    continue

                # Caminhada aleatoria com leve tendencia na direcao boa.
                tendencia = 0.004 if direcao is MelhorDirecao.MAIOR else -0.004
                valor *= 1 + tendencia + rng.uniform(-vol, vol)
                meta = float(base) * (1.05 if direcao is MelhorDirecao.MAIOR else 0.95)

                db.add(
                    Medicao(
                        indicador_id=ind.id,
                        competencia=comp,
                        valor=Decimal(f"{valor:.4f}"),
                        meta=Decimal(f"{meta:.4f}"),
                    )
                )
                criados_m += 1
        db.commit()
    finally:
        db.close()

    print(
        f"Seed concluido: {criados_u} usuarios, {criados_i} indicadores, "
        f"{criados_m} medicoes."
    )
    if criados_u:
        print(f"Senha de todos os usuarios de teste: {senha_padrao}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
