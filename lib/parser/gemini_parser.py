import json
import logging
from typing import Any, Optional

import httpx

from lib.config import GEMINI_API_KEY, generate_external_id

logger = logging.getLogger(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"


def _build_prompt(raw_text: str, lookups: dict[str, Any]) -> str:
    """Constrói o prompt com os valores válidos do DevPool."""
    roles = lookups.get("roles", [])
    position_types = lookups.get("positionTypes", [])
    position_models = lookups.get("positionModels", [])
    techs = lookups.get("technologies", [])

    prompt = f"""Você é um extrator de dados de vagas de emprego em tecnologia.
Analise o texto abaixo e extraia dados estruturados da vaga.

REGRAS:
- Retorne SOMENTE um JSON válido, sem markdown, sem explicações.
- Se não encontrar email, use string vazia no campo email.
- A descrição DEVE seguir o padrão estrutural abaixo.
- A descrição NÃO PODE conter nenhum tipo de contato: emails, telefones, links, redes sociais, nomes de recrutadores.
- Remova hashtags, emojis e formatações especiais da descrição.
- Se o modelo de trabalho for "Remoto", NÃO preencha city e state (retorne strings vazias).
- Só preencha city e state se o modelo for "Presencial" ou "Híbrido".
- Separe CLARAMENTE as tecnologias entre obrigatórias e desejáveis:
  - mandatory_techs: tecnologias listadas como "requisitos", "obrigatório", "necessário", "experiência com", "conhecimento em"
  - desirable_techs: tecnologias listadas como "diferencial", "desejável", "nice to have", "bônus", "será um plus"
  - Se não houver distinção clara no texto, considere TODAS como obrigatórias.

PADRÃO DA DESCRIÇÃO (siga esta estrutura exata):
"Sobre a vaga:\\n[Resumo breve da posição e da empresa em 2-3 frases]\\n\\nResponsabilidades:\\n- [responsabilidade 1]\\n- [responsabilidade 2]\\n- [...]\\n\\nRequisitos obrigatórios:\\n- [requisito 1]\\n- [requisito 2]\\n- [...]\\n\\nDiferenciais:\\n- [diferencial 1]\\n- [diferencial 2]\\n- [...]\\n\\nBenefícios:\\n- [benefício 1, se mencionado]\\n- [...]"

Se alguma seção não tiver informações no texto original, omita essa seção.

CARGOS VÁLIDOS (use exatamente um destes): {', '.join(roles)}
MODELOS DE TRABALHO VÁLIDOS: {', '.join(position_models)}
TIPOS DE CONTRATO VÁLIDOS: {', '.join(position_types)}
TECNOLOGIAS VÁLIDAS (use SOMENTE desta lista): {', '.join(techs[:200])}
SENIORIDADE: junior, pleno, senior, especialista, estagio

Retorne este JSON:
{{
  "role": "cargo da lista acima",
  "description": "descrição estruturada conforme padrão acima, SEM contatos",
  "seniority": "nível de senioridade",
  "model": "modelo da lista acima",
  "type": "tipo da lista acima",
  "companyName": "nome da empresa",
  "email": "email para candidatura extraído do texto original, ou vazio",
  "mandatory_techs": ["tech1", "tech2"],
  "desirable_techs": ["tech1", "tech2"],
  "city": "cidade ou vazio",
  "state": "UF ou vazio"
}}

TEXTO DA VAGA:
{raw_text[:4000]}"""

    return prompt


def parse_job_posting(
    raw_text: str,
    source: str,
    identifier: str,
    source_url: str,
    lookups: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Usa Gemini Flash para extrair dados estruturados de uma vaga."""
    if lookups is None:
        lookups = {}

    if not GEMINI_API_KEY:
        logger.error("GOOGLE_GENERATIVE_AI_API_KEY não configurada")
        return None

    prompt = _build_prompt(raw_text, lookups)

    try:
        response = httpx.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1,
                },
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        text_response = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        if not text_response:
            logger.warning("Gemini retornou resposta vazia para: %s", identifier)
            return None

        extracted = json.loads(text_response)
        return _enrich(extracted, source, identifier, source_url, lookups)

    except json.JSONDecodeError as e:
        logger.error("Gemini retornou JSON inválido para %s: %s", identifier, str(e))
        return None
    except httpx.HTTPError as e:
        logger.error("Erro HTTP Gemini: %s", str(e))
        return None


def parse_job_posting_debug(
    raw_text: str,
    source: str,
    identifier: str,
    source_url: str,
    lookups: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Versão debug que retorna raw + enriched para diagnóstico."""
    if lookups is None:
        lookups = {}

    if not GEMINI_API_KEY:
        return {"error": "GOOGLE_GENERATIVE_AI_API_KEY não configurada"}

    prompt = _build_prompt(raw_text, lookups)

    try:
        response = httpx.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.1,
                },
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        text_response = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        raw_extracted = json.loads(text_response)
        enriched = _enrich(raw_extracted, source, identifier, source_url, lookups)
        return {"raw": raw_extracted, "enriched": enriched}

    except Exception as e:
        return {"error": str(e)}


def _enrich(
    data: dict[str, Any],
    source: str,
    identifier: str,
    source_url: str,
    lookups: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Valida contra lookups e adiciona campos de rastreamento."""
    roles = lookups.get("roles", [])
    position_types = lookups.get("positionTypes", [])
    position_models = lookups.get("positionModels", [])
    techs_set = set(t.lower() for t in lookups.get("technologies", []))
    techs_name_map = {t.lower(): t for t in lookups.get("technologies", [])}

    role = data.get("role", "")
    if roles and role not in roles:
        logger.warning("Role '%s' não está na lista válida, descartando", role)
        return None

    model = data.get("model", "")
    if position_models and model not in position_models:
        logger.warning("Model '%s' não está na lista válida, descartando", model)
        return None

    contract_type = data.get("type", "")
    if position_types and contract_type not in position_types:
        logger.warning("Type '%s' não está na lista válida, descartando", contract_type)
        return None

    email = data.get("email", "") or "sem-email@pendente.devpool.com.br"

    def filter_techs(tech_list):
        if not techs_set or not tech_list:
            return tech_list or []
        return [techs_name_map[t.lower()] for t in tech_list if t.lower() in techs_set]

    return {
        "role": role,
        "description": data.get("description", ""),
        "seniority": data.get("seniority", "pleno"),
        "model": model,
        "type": contract_type,
        "companyName": data.get("companyName", "Não informado"),
        "email": email,
        "sourceUrl": source_url,
        "externalId": generate_external_id(source, identifier),
        "mandatory_techs": filter_techs(data.get("mandatory_techs", [])),
        "desirable_techs": filter_techs(data.get("desirable_techs", [])),
        "city": data.get("city"),
        "state": data.get("state"),
    }
