"""Motor de KPI: atingimento, ritmo esperado e semaforo.

Reproduz a regra do comite executivo da KAMI CO.:

  1. Quanto ja realizamos?   -> consolidar()
  2. Quanto isso representa da meta?  -> atingimento()
  3. Estamos no ritmo?  -> esperado_na_semana() + semaforo()

O ponto sutil e o passo 3. O semaforo nao compara o atingimento com
100% da meta do mes, mas com o que se espera ter atingido NAQUELA
semana — que depende da classe do indicador:

  ACUMULA  soma ao longo do mes. Na semana 3 de 4 espera-se 75%.
  TAXA     razao valida a qualquer momento. Espera-se 100% sempre.

Sem essa distincao, faturamento a 66% na semana 3 pareceria uma falha
grave, quando esta a 9 p.p. do ritmo; e margem a 99% pareceria bem,
quando ja perdeu a meta do mes.
"""
from __future__ import annotations

import enum
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.models.cadastro import MelhorDirecao, TipoAcumulacao


class Semaforo(str, enum.Enum):
    """Como o atingimento se compara ao ritmo esperado da semana."""

    VERDE = "VERDE"        # no ritmo ou acima
    AMBAR = "AMBAR"        # abaixo, dentro da tolerancia
    VERMELHO = "VERMELHO"  # abaixo da tolerancia
    SEM_DADO = "SEM_DADO"  # falta medicao ou meta


# Tolerancia, em pontos percentuais de atingimento, entre o esperado e o
# limite do ambar. E politica do comite, nao lei da natureza: fica
# parametrizado para o comite poder apertar ou afrouxar.
TOLERANCIA_AMBAR_PP = Decimal("10")

CEM = Decimal("100")


@dataclass(frozen=True)
class ValorMedido:
    """Um numero medido, com o denominador quando for taxa."""

    numerador: Decimal
    denominador: Decimal | None = None

    @property
    def valor(self) -> Decimal | None:
        """O valor legivel: a razao, se houver denominador."""
        if self.denominador is None:
            return self.numerador
        if self.denominador == 0:
            return None
        return self.numerador / self.denominador


def esperado_na_semana(
    tipo: TipoAcumulacao, semana: int, semanas_total: int
) -> Decimal:
    """Atingimento esperado, em %, na semana informada.

    ACUMULA cresce linearmente ao longo do mes; TAXA e exigida por
    inteiro em qualquer semana.

    >>> esperado_na_semana(TipoAcumulacao.ACUMULA, 3, 4)
    Decimal('75')
    >>> esperado_na_semana(TipoAcumulacao.TAXA, 3, 4)
    Decimal('100')
    """
    if semanas_total <= 0:
        raise ValueError("semanas_total deve ser positivo")
    if not 1 <= semana <= semanas_total:
        raise ValueError(
            f"semana {semana} fora do ciclo de {semanas_total} semanas"
        )

    if tipo is TipoAcumulacao.TAXA:
        return CEM
    return CEM * Decimal(semana) / Decimal(semanas_total)


def consolidar(medidos: Iterable[ValorMedido]) -> ValorMedido | None:
    """Junta as medicoes das regionais em um valor consolidado.

    Para taxa, soma numeradores e denominadores separadamente — o
    consolidado e soma(num)/soma(den), nunca a media das regionais.

    Com os numeros do comite: OTIF de SP 95,7%, RJ 91,1% e RS 81,9%
    consolida em 92,3% ponderado pelo volume; a media simples daria
    89,5%, um erro de 2,8 p.p.
    """
    itens = list(medidos)
    if not itens:
        return None

    tem_denominador = [i for i in itens if i.denominador is not None]
    if tem_denominador and len(tem_denominador) != len(itens):
        raise ValueError(
            "nao e possivel consolidar medicoes com e sem denominador na "
            "mesma serie — o indicador precisa ser todo taxa ou todo valor"
        )

    numerador = sum((i.numerador for i in itens), Decimal(0))
    if not tem_denominador:
        return ValorMedido(numerador)

    denominador = sum((i.denominador for i in itens), Decimal(0))  # type: ignore[misc]
    return ValorMedido(numerador, denominador)


def acumular(medidos: Sequence[ValorMedido], tipo: TipoAcumulacao) -> ValorMedido | None:
    """Reduz uma serie semanal ao valor do mes ate aqui.

    ACUMULA soma as semanas. TAXA toma a semana mais recente — a serie
    e uma sequencia de retratos, nao de fluxos, e somar percentuais nao
    significa nada.

    A ordem da sequencia importa para TAXA: espera-se da semana mais
    antiga para a mais recente.
    """
    if not medidos:
        return None
    if tipo is TipoAcumulacao.TAXA:
        return medidos[-1]
    return consolidar(medidos)


def atingimento(
    realizado: Decimal | None,
    meta: Decimal | None,
    melhor_direcao: MelhorDirecao,
) -> Decimal | None:
    """Atingimento da meta em %, sempre na leitura "acima de 100 e bom".

    Para indicadores em que menor e melhor (inadimplencia, tempo de
    entrega, obsolescencia) a razao e invertida: ficar abaixo da meta e
    o resultado desejado. Sem isso, inadimplencia de 6,8% contra meta de
    4,0% apareceria como 170% de atingimento.
    """
    if realizado is None or meta is None or meta == 0:
        return None

    if melhor_direcao is MelhorDirecao.MAIOR:
        return realizado / meta * CEM

    if realizado == 0:
        # Zerou um indicador em que menor e melhor: meta batida com
        # folga. Nao ha razao definida, entao devolve o teto da escala.
        return CEM * 2
    return meta / realizado * CEM


def semaforo(
    atingido: Decimal | None,
    esperado: Decimal,
    tolerancia_pp: Decimal = TOLERANCIA_AMBAR_PP,
) -> Semaforo:
    """Compara o atingimento com o ritmo esperado da semana.

    verde     no ritmo ou acima
    ambar     abaixo, mas dentro da tolerancia
    vermelho  abaixo da tolerancia
    """
    if atingido is None:
        return Semaforo.SEM_DADO
    if atingido >= esperado:
        return Semaforo.VERDE
    if atingido >= esperado - tolerancia_pp:
        return Semaforo.AMBAR
    return Semaforo.VERMELHO


def desvio_do_ritmo(atingido: Decimal | None, esperado: Decimal) -> Decimal | None:
    """Distancia, em pontos percentuais, entre o atingido e o esperado.

    Negativo significa atraso. E o numero que ordena a pauta da reuniao:
    o mais negativo primeiro.
    """
    if atingido is None:
        return None
    return atingido - esperado


# =====================================================================
# Projecao de fechamento
#
# O comite ja faz esta conta a mao no slide de faturamento: "necessario
# na semana 4: R$ 1,26 mi, vs R$ 0,77 mi realizado na S3". Formalizada,
# ela responde a pergunta que decide a reuniao na semana 3 — no ritmo
# atual, o mes fecha em quanto?
#
# Deliberadamente simples: extrapola o ritmo medio realizado. Nao e
# previsao estatistica, e aritmetica que o comite pode conferir de
# cabeca. Um modelo mais elaborado seria menos auditavel e nao mais
# confiavel com 3 pontos de dados.
# =====================================================================


@dataclass(frozen=True)
class Projecao:
    """Fechamento estimado do mes mantido o ritmo atual."""

    valor_projetado: Decimal | None
    atingimento_projetado_pct: Decimal | None
    # Quanto falta para a meta, em valor.
    gap: Decimal | None
    # Quanto precisa sair por semana no tempo restante.
    necessario_por_semana: Decimal | None
    # Razao entre o necessario e o ritmo realizado. 1,0 = manter o ritmo;
    # 1,6 = precisa render 60% mais do que vem rendendo.
    esforco_vs_ritmo: Decimal | None
    semanas_restantes: int
    alcancavel: bool | None


def projetar_fechamento(
    tipo: TipoAcumulacao,
    realizado: Decimal | None,
    meta: Decimal | None,
    melhor_direcao: MelhorDirecao,
    semana: int,
    semanas_total: int,
) -> Projecao:
    """Projeta o fechamento do mes a partir do ritmo realizado.

    ACUMULA extrapola: media semanal x semanas_total.
    TAXA nao extrapola — a posicao atual e a melhor estimativa do
    fechamento, porque nao ha acumulo a completar.
    """
    restantes = max(semanas_total - semana, 0)

    if realizado is None or meta is None or meta == 0:
        return Projecao(None, None, None, None, None, restantes, None)

    if tipo is TipoAcumulacao.TAXA:
        # A taxa de hoje e a projecao de fechamento.
        ating = atingimento(realizado, meta, melhor_direcao)
        return Projecao(
            valor_projetado=realizado,
            atingimento_projetado_pct=ating,
            gap=meta - realizado,
            necessario_por_semana=None,
            esforco_vs_ritmo=None,
            semanas_restantes=restantes,
            alcancavel=None if ating is None else ating >= CEM,
        )

    ritmo_semanal = realizado / Decimal(semana)
    projetado = ritmo_semanal * Decimal(semanas_total)
    gap = meta - realizado

    if restantes == 0:
        # Mes encerrado: nao ha esforco futuro a calcular.
        return Projecao(
            valor_projetado=realizado,
            atingimento_projetado_pct=atingimento(realizado, meta, melhor_direcao),
            gap=gap,
            necessario_por_semana=None,
            esforco_vs_ritmo=None,
            semanas_restantes=0,
            alcancavel=realizado >= meta,
        )

    necessario = gap / Decimal(restantes)
    esforco = (
        necessario / ritmo_semanal if ritmo_semanal > 0 else None
    )

    return Projecao(
        valor_projetado=projetado,
        atingimento_projetado_pct=atingimento(projetado, meta, melhor_direcao),
        gap=gap,
        necessario_por_semana=necessario if gap > 0 else Decimal(0),
        esforco_vs_ritmo=esforco if gap > 0 else Decimal(0),
        semanas_restantes=restantes,
        # Dobrar o ritmo numa semana e retorica, nao plano. O corte em 2x
        # separa "apertado" de "nao vai acontecer".
        alcancavel=None if esforco is None else esforco <= Decimal(2),
    )
