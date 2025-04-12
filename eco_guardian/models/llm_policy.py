
from openai import OpenAI
import pdfplumber
import json
import os
from pathlib import Path
from dotenv import load_dotenv

class PolicyAnalyzer:
    def __init__(self):
        # Configuração inicial e autenticação
        env_path = Path(__file__).resolve().parent.parent.parent / '.env'
        load_dotenv(dotenv_path=env_path)
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("Chave da API OpenAI não encontrada no arquivo .env")
            
        self.client = OpenAI(api_key=api_key)
        
    def generate_resumo_executivo(self, text: str) -> str:
        prompt = f"""
        Você é um especialista em políticas e programas ambientais. Leia o texto abaixo de maneira crítica e gere um resumo executivo com aproximadamente 300 palavras,
        explicando os principais objetivos, ações e contexto político-institucional da política pública ambiental descrita.
        
        Inicie o texto identificando claramente o estado ou ente federativo responsável pela política. Caso o nome do estado
        não esteja claro, use o máximo de evidência disponível no texto para inferir e mencionar isso no início do resumo.

        TEXTO:
        {text[:10000]}
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=3000
        )
        return response.choices[0].message.content.strip()

    def generate_analise_ocde(self, text: str) -> dict:
        prompt = f"""
        Você é um analista ambiental.

        A partir do texto abaixo, escreva uma análise crítica e técnica com **aproximadamente 100 palavras para cada um dos critérios da OCDE** utilizados na avaliação de políticas ambientais públicas.

        ⚠️É obrigatório extrair **dados quantitativos** sempre que estiverem presentes no texto ou tabelas — como número de unidades produzidas, percentuais, metas, valores financeiros, prazos, públicos atendidos, etc.

        Se não houver dados disponíveis, declare isso explicitamente no trecho analisado.

        Critérios:
        - **Relevância**: O público-alvo entende a política como benéfica, importante e útil?
        - **Efetividade**: A política atingiu ou tende a atingir seus objetivos/resultados? Apresente **dados de execução** como volume de produção, áreas restauradas, ou outros indicadores claros de entrega.
        - **Eficiência**: A intervenção respeita cronogramas, orçamento e entrega planejada? Use números de custo, tempo, entregas previstas x realizadas.
        - **Sustentabilidade**: Há capacidade institucional, econômica, social e ambiental de sustentação da política?
        - **Coerência**: A política é compatível com outras intervenções no setor, país ou instituição?
        - **Impacto**: Há evidências quantitativas ou qualitativas de efeitos positivos/negativos no meio ambiente e na sociedade? Ex: redução de desmatamento, aumento de cobertura vegetal, mudança na qualidade do solo, etc.

        TEXTO:
        {text[:120000]}   # Mínimo seguro# ≈ 30.000 tokens (25 a 30 páginas de texto)

        Formato esperado (JSON):
        {{
            "relevancia": "...",
            "eficacia": "...",
            "eficiencia": "...",
            "sustentabilidade": "...",
            "coerencia": "...",
            "impacto": "..."
        }}
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=5000,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def analyze_policy(self, pdf_path: str) -> dict:
        result = {
            "resumo_executivo": "",
            "resumo_ocde": {},
            "error": None,
            "texto_analisado": ""
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = "\n".join([page.extract_text() or '' for page in pdf.pages])

            result["texto_analisado"] = text[:2500] + "[...]" if len(text) > 2500 else text

            # Etapa 1: resumo executivo
            resumo = self.generate_resumo_executivo(text)
            result["resumo_executivo"] = resumo

            # Etapa 2: análise OCDE
            analise_ocde = self.generate_analise_ocde(text)
            result["resumo_ocde"] = analise_ocde

        except json.JSONDecodeError as e:
            result["error"] = f"Erro de formatação: {str(e)}"
        except Exception as e:
            result["error"] = f"Erro crítico: {str(e)}"

        return result
