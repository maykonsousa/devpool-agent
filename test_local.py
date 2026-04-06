"""Teste local do pipeline: coleta 1 issue do GitHub → Claude Parser → print resultado."""
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Verificar env vars
missing = [k for k in ["ANTHROPIC_API_KEY"] if not os.environ.get(k)]
if missing:
    print(f"Faltam variáveis de ambiente: {', '.join(missing)}")
    sys.exit(1)

from lib.sources.github_collector import _collect_repo_issues
from lib.config import GITHUB_TOKEN

print("=== Teste Local devpool-agent ===\n")

# Testar coleta de 1 repo com limite de 3 issues
headers = {"Accept": "application/vnd.github.v3+json"}
if GITHUB_TOKEN:
    headers["Authorization"] = f"token {GITHUB_TOKEN}"

print("1. Coletando issues de frontendbr/vagas (max 3)...")

import httpx

url = "https://api.github.com/repos/frontendbr/vagas/issues"
params = {"state": "open", "sort": "created", "direction": "desc", "per_page": 3}

response = httpx.get(url, headers=headers, params=params, timeout=30)
issues = response.json()

if isinstance(issues, dict) and "message" in issues:
    print(f"   Erro GitHub API: {issues['message']}")
    sys.exit(1)

print(f"   {len(issues)} issues encontradas\n")

# Testar parser com a primeira issue
from lib.parser.claude_parser import parse_job_posting
from lib.config import generate_external_id

issue = issues[0]
title = issue.get("title", "")
body = issue.get("body", "")[:2000]
labels = [l["name"] for l in issue.get("labels", [])]

print(f"2. Parseando issue: '{title}'")
print(f"   Labels: {', '.join(labels)}")
print(f"   URL: {issue.get('html_url', '')}\n")

raw_text = f"Título: {title}\nLabels: {', '.join(labels)}\n\n{body}"

parsed = parse_job_posting(
    raw_text=raw_text,
    source="github-frontendbr-vagas",
    identifier=str(issue["number"]),
    source_url=issue.get("html_url", ""),
)

if parsed:
    print("3. Resultado do parsing:\n")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    print("\n=== Pipeline funcionando! ===")
else:
    print("3. Parser retornou None (vaga sem email ou dados inválidos)")
    print("   Isso é esperado se a issue não tiver email de candidatura.")
    print("\n=== Parser funciona, mas filtrou esta vaga (sem email) ===")
