import os
import hashlib

# --- API Keys ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEVPOOL_API_URL = os.environ.get("DEVPOOL_API_URL", "")
DEVPOOL_API_KEY = os.environ.get("DEVPOOL_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# --- Fontes RSS ---
RSS_FEEDS = [
    {
        "name": "programathor",
        "url": "https://programathor.com.br/feed",
        "type": "rss",
    },
    {
        "name": "remotive",
        "url": "https://remotive.com/api/remote-jobs?limit=20",
        "type": "json",
    },
]

# --- Repos GitHub (issues como vagas) ---
GITHUB_REPOS = [
    "frontendbr/vagas",
]

# --- Sites para scraping ---
SCRAPER_SOURCES = [
    {
        "name": "trampos",
        "url": "https://trampos.co/oportunidades",
        "selector": "article.job",
    },
]

# --- Mapeamento de enums para normalização ---
SENIORITY_MAP = {
    "junior": "junior",
    "júnior": "junior",
    "jr": "junior",
    "pleno": "pleno",
    "mid": "pleno",
    "middle": "pleno",
    "senior": "senior",
    "sênior": "senior",
    "sr": "senior",
    "especialista": "especialista",
    "specialist": "especialista",
    "lead": "especialista",
    "principal": "especialista",
    "estagio": "estagio",
    "estágio": "estagio",
    "intern": "estagio",
    "internship": "estagio",
    "trainee": "estagio",
}

MODEL_MAP = {
    "remoto": "remoto",
    "remote": "remoto",
    "home office": "remoto",
    "hibrido": "hibrido",
    "híbrido": "hibrido",
    "hybrid": "hibrido",
    "presencial": "presencial",
    "onsite": "presencial",
    "on-site": "presencial",
    "in-office": "presencial",
}

TYPE_MAP = {
    "clt": "clt",
    "pj": "pj",
    "pessoa jurídica": "pj",
    "freelancer": "freelancer",
    "freelance": "freelancer",
    "contractor": "pj",
    "estagio": "estagio",
    "estágio": "estagio",
    "internship": "estagio",
}

# --- Constantes ---
BATCH_SIZE = 10
MAX_ITEMS_PER_SOURCE = 5
REQUEST_TIMEOUT = 10


def generate_external_id(source: str, identifier: str) -> str:
    """Gera um externalId determinístico a partir da fonte e identificador."""
    raw = f"{source}:{identifier}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]
