import logging
from typing import Any, Optional

import anthropic

from lib.config import ANTHROPIC_API_KEY, generate_external_id

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_tool(lookups: dict[str, Any]) -> dict:
    """Constrói a tool de extração dinamicamente com os valores válidos do DevPool."""
    roles = lookups.get("roles", [])
    techs = lookups.get("technologies", [])
    position_types = lookups.get("positionTypes", [])
    position_models = lookups.get("positionModels", [])

    return {
        "name": "register_position",
        "description": "Registra uma vaga de emprego extraída com dados estruturados e normalizados.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role": {
                    "type": "string",
                    "enum": roles,
                    "description": "Cargo da vaga. DEVE ser um dos valores listados no enum.",
                } if roles else {
                    "type": "string",
                    "description": "Cargo da vaga",
                },
                "description": {
                    "type": "string",
                    "description": "Descrição completa da vaga, incluindo responsabilidades e requisitos",
                },
                "seniority": {
                    "type": "string",
                    "description": "Nível de senioridade inferido do texto da vaga",
                },
                "model": {
                    "type": "string",
                    "enum": position_models,
                    "description": "Modelo de trabalho. DEVE ser um dos valores listados no enum.",
                } if position_models else {
                    "type": "string",
                    "description": "Modelo de trabalho",
                },
                "type": {
                    "type": "string",
                    "enum": position_types,
                    "description": "Tipo de contrato. DEVE ser um dos valores listados no enum.",
                } if position_types else {
                    "type": "string",
                    "description": "Tipo de contrato",
                },
                "companyName": {
                    "type": "string",
                    "description": "Nome da empresa que está contratando",
                },
                "email": {
                    "type": "string",
                    "description": "Email para envio de candidatura. Se não encontrar, retorne string vazia.",
                },
                "mandatory_techs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tecnologias obrigatórias. Use SOMENTE nomes desta lista: " + ", ".join(techs[:200]) if techs else "Tecnologias obrigatórias mencionadas como requisitos",
                },
                "desirable_techs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tecnologias desejáveis. Use SOMENTE nomes desta lista: " + ", ".join(techs[:200]) if techs else "Tecnologias desejáveis ou diferenciais",
                },
                "city": {
                    "type": "string",
                    "description": "Cidade, se mencionada. Vazio se remoto sem cidade.",
                },
                "state": {
                    "type": "string",
                    "description": "Estado (sigla UF), se mencionado.",
                },
            },
            "required": [
                "role",
                "description",
                "seniority",
                "model",
                "type",
                "companyName",
                "email",
                "mandatory_techs",
                "desirable_techs",
            ],
        },
    }


def _build_system_prompt(lookups: dict[str, Any]) -> str:
    """Constrói o system prompt com os valores válidos do DevPool."""
    roles = lookups.get("roles", [])
    position_types = lookups.get("positionTypes", [])
    position_models = lookups.get("positionModels", [])
    techs = lookups.get("technologies", [])

    sections = [
        "Você é um extrator de dados de vagas de emprego em tecnologia.",
        "Sua tarefa é analisar o texto de uma vaga e extrair dados estruturados usando a tool register_position.",
        "",
        "REGRAS IMPORTANTES:",
        "- Extraia TODOS os dados que conseguir identificar no texto.",
        "- Se não encontrar email de candidatura, retorne string vazia no campo email.",
        "- Mantenha a descrição em português, traduzindo se necessário.",
        "- SEMPRE use a tool register_position para retornar os dados.",
    ]

    if roles:
        sections.append(f"\nCARGOS VÁLIDOS (use exatamente um destes): {', '.join(roles)}")
        sections.append("- Escolha o cargo mais próximo do título da vaga. Se nenhum corresponder exatamente, escolha o mais similar.")

    if position_models:
        sections.append(f"\nMODELOS DE TRABALHO VÁLIDOS: {', '.join(position_models)}")
        sections.append("- Se não mencionado, assuma o primeiro da lista.")

    if position_types:
        sections.append(f"\nTIPOS DE CONTRATO VÁLIDOS: {', '.join(position_types)}")
        sections.append("- Se não mencionado, assuma o primeiro da lista.")

    if techs:
        sections.append(f"\nTECNOLOGIAS VÁLIDAS (use SOMENTE nomes desta lista): {', '.join(techs[:300])}")
        sections.append("- Apenas inclua tecnologias que existam nesta lista. Ignore tecnologias mencionadas na vaga que não estejam aqui.")

    sections.append("\nSENIORIDADE: infira do contexto (ex: '5+ anos' → senior, 'estágio' → estagio). Valores comuns: junior, pleno, senior, especialista, estagio.")

    return "\n".join(sections)


def parse_job_posting(
    raw_text: str,
    source: str,
    identifier: str,
    source_url: str,
    lookups: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Usa Claude para extrair dados estruturados de uma vaga."""
    if lookups is None:
        lookups = {}

    tool = _build_tool(lookups)
    system_prompt = _build_system_prompt(lookups)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": "register_position"},
            messages=[
                {
                    "role": "user",
                    "content": f"Extraia os dados desta vaga:\n\n{raw_text[:4000]}",
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "register_position":
                extracted = block.input
                return _enrich(extracted, source, identifier, source_url, lookups)

        logger.warning("Claude não retornou tool_use para: %s", identifier)
        return None

    except anthropic.APIError as e:
        logger.error("Erro na API Claude: %s", str(e))
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

    tool = _build_tool(lookups)
    system_prompt = _build_system_prompt(lookups)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            tools=[tool],
            tool_choice={"type": "tool", "name": "register_position"},
            messages=[
                {
                    "role": "user",
                    "content": f"Extraia os dados desta vaga:\n\n{raw_text[:4000]}",
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "register_position":
                raw_extracted = block.input
                enriched = _enrich(raw_extracted, source, identifier, source_url, lookups)
                return {"raw": raw_extracted, "enriched": enriched}

        return {"error": "Claude não retornou tool_use"}

    except anthropic.APIError as e:
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

    # Filtrar techs para apenas as que existem no DevPool
    def filter_techs(tech_list):
        if not techs_set:
            return tech_list
        return [techs_name_map[t.lower()] for t in tech_list if t.lower() in techs_set]

    return {
        "role": role,
        "description": data["description"],
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
