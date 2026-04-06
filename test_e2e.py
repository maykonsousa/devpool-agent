"""Teste E2E: setup agent → lookups → coleta → parse → publica no DevPool local."""
import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

missing = [k for k in ["ANTHROPIC_API_KEY", "DEVPOOL_API_URL", "DEVPOOL_API_KEY"] if not os.environ.get(k)]
if missing:
    print(f"Faltam variáveis: {', '.join(missing)}")
    sys.exit(1)

import httpx
from lib.publisher.lookups_client import setup_agent_user, get_lookups
from lib.parser.claude_parser import parse_job_posting
from lib.config import DEVPOOL_API_URL, DEVPOOL_API_KEY

print("=== Teste E2E devpool-agent → DevPool ===\n")

# 1. Setup do agent user
print("1. Configurando usuário DevPool Agent...")
agent_id = setup_agent_user(DEVPOOL_API_URL)
if agent_id:
    print(f"   Agent user ID: {agent_id}\n")
else:
    print("   ERRO: Não foi possível criar o agent user\n")
    sys.exit(1)

# 2. Carregar lookups
print("2. Carregando lookups do DevPool...")
lookups = get_lookups(DEVPOOL_API_URL)
if lookups:
    print(f"   Roles: {len(lookups.get('roles', []))} — {lookups.get('roles', [])[:5]}...")
    print(f"   Technologies: {len(lookups.get('technologies', []))} — {lookups.get('technologies', [])[:5]}...")
    print(f"   Position Types: {lookups.get('positionTypes', [])}")
    print(f"   Position Models: {lookups.get('positionModels', [])}\n")
else:
    print("   AVISO: Lookups vazios, continuando sem validação\n")

# 3. Buscar 1 issue do GitHub
print("3. Buscando issue de frontendbr/vagas...")
headers = {"Accept": "application/vnd.github.v3+json"}
resp = httpx.get(
    "https://api.github.com/repos/frontendbr/vagas/issues",
    headers=headers,
    params={"state": "open", "sort": "created", "direction": "desc", "per_page": 1},
    timeout=30,
)
issues = resp.json()
issue = issues[0]
print(f"   Issue: {issue['title']}")
print(f"   URL: {issue['html_url']}\n")

# 4. Parsear com Claude + lookups
print("4. Parseando com Claude API (usando lookups)...")
raw_text = (
    f"Título: {issue['title']}\n"
    f"Labels: {', '.join(l['name'] for l in issue.get('labels', []))}\n\n"
    f"{issue.get('body', '')[:2000]}"
)
parsed = parse_job_posting(
    raw_text=raw_text,
    source="github-frontendbr-vagas",
    identifier=str(issue["number"]),
    source_url=issue.get("html_url", ""),
    lookups=lookups,
)

if not parsed:
    print("   Parser retornou None (vaga sem email, role/model/type inválido)")
    print("   Testando com dados mock...\n")
    # Usar valores reais dos lookups
    mock_role = lookups.get("roles", ["Desenvolvedor Frontend"])[0] if lookups else "Desenvolvedor Frontend"
    mock_type = lookups.get("positionTypes", ["pj"])[0] if lookups else "pj"
    mock_model = lookups.get("positionModels", ["remoto"])[0] if lookups else "remoto"
    mock_techs = lookups.get("technologies", ["React", "TypeScript"])[:2] if lookups else ["React", "TypeScript"]

    parsed = {
        "role": mock_role,
        "description": "Vaga de teste E2E para validar pipeline com lookups do DevPool.",
        "seniority": "pleno",
        "model": mock_model,
        "type": mock_type,
        "companyName": "DevPool Test Corp",
        "email": "teste@devpool.com.br",
        "sourceUrl": issue.get("html_url", "https://github.com/frontendbr/vagas"),
        "externalId": "e2e-test-lookups-001",
        "mandatory_techs": mock_techs,
        "desirable_techs": [],
    }
    print(f"   Mock com valores válidos: role={mock_role}, type={mock_type}, model={mock_model}\n")

print(f"   Resultado: {json.dumps(parsed, indent=2, ensure_ascii=False)}\n")

# 5. Publicar no DevPool
print("5. Publicando no DevPool...")
resp = httpx.post(
    DEVPOOL_API_URL,
    json=parsed,
    headers={
        "Authorization": f"Bearer {DEVPOOL_API_KEY}",
        "Content-Type": "application/json",
    },
    timeout=30,
)
print(f"   Status HTTP: {resp.status_code}")
body = resp.json()
print(f"   Resposta: {json.dumps(body, indent=2, ensure_ascii=False)}\n")

# 6. Testar deduplicação
print("6. Testando deduplicação...")
resp2 = httpx.post(
    DEVPOOL_API_URL,
    json=parsed,
    headers={
        "Authorization": f"Bearer {DEVPOOL_API_KEY}",
        "Content-Type": "application/json",
    },
    timeout=30,
)
body2 = resp2.json()
results = body2.get("results", [])
if results and results[0].get("status") == "skipped":
    print("   Deduplicação OK — vaga duplicada foi ignorada")
else:
    print(f"   Resposta: {json.dumps(body2, indent=2, ensure_ascii=False)}")

print("\n=== Teste E2E concluído! ===")
