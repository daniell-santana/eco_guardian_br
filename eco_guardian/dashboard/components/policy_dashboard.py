# eco_guardian/dashboard/components/policy_dashboard.py
import streamlit as st
import os
import tempfile
import uuid
from eco_guardian.models.llm_policy import PolicyAnalyzer

def show_policy_dashboard():
    """Dashboard principal para análise de políticas ambientais (OCDE)"""
    st.header("📑 Análise de Políticas Ambientais - Critérios OCDE")

    # Adicionando a nota explicativa
    st.markdown("""
    <div style='
        background-color: #1a1a1a;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        margin-bottom: 1.5rem;
    '>
        <p style='color: #ffffff; font-size: 14px;'>
        <strong>ℹ️ Como usar esta análise:</strong> Este painel avalia documentos de políticas ambientais com base nos critérios da 
        <a href="https://www.oecd.org/en/topics/sub-issues/development-co-operation-evaluation-and-effectiveness/evaluation-criteria.html" target="_blank" style="color: #4CAF50;">OCDE</a> para monitoramento e avaliação de políticas públicas.
        </p>
        <p style='color: #e0e0e0; font-size: 13px; margin-top: 8px;'>
        <strong>Recomendamos enviar:</strong> Planos de ação, relatórios de implementação, projetos de lei ambiental, ou qualquer documento que contenha:
        <ul style='color: #e0e0e0; font-size: 13px; margin-top: 4px;'>
            <li>Objetivos e metas quantificáveis</li>
            <li>Indicadores de desempenho</li>
            <li>Dados orçamentários</li>
            <li>Resultados alcançados</li>
        </ul>
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown("📎 **Upload do arquivo** — • Tamanho máximo: 20 MB")

        uploaded_file = st.file_uploader(
            label="",
            type=["pdf","docx"],
            key="policy_upload"
        )
        
        if uploaded_file:
            # ✅ Limite de 20 MB
            if uploaded_file.size > 20 * 1024 * 1024:
                st.error("❌ O arquivo excede o limite de 20 MB. Por favor, envie um documento menor.")
                return
            analyzer = PolicyAnalyzer()
            
            with st.spinner("Analisando documento com inteligência artificial..."):
                try:
                    # Cria arquivo temporário
                    temp_path = os.path.join(tempfile.gettempdir(), f"temp_policy_{uuid.uuid4().hex}.pdf")
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    # Executa análise
                    analysis = analyzer.analyze_policy(temp_path)
                    st.session_state.policy_analysis = analysis
                    
                    if analysis.get('error'):
                        st.error("❌ Falha na análise do documento")
                        st.error(analysis['error'])  
                        return
                    
                    st.success("✅ Análise concluída com sucesso!")
                    
                    # Nova seção de resumo
                    render_policy_overview(analysis)
                    
                    # Seção OCDE
                    render_ocde_analysis(analysis)

                except Exception as e:
                    st.error("Erro crítico durante o processamento")
                    analysis = {
                        "resumo_executivo": "Erro na análise",
                        "resumo_ocde": {k: "Erro" for k in ["relevancia", "eficacia", "eficiencia", "impacto", "sustentabilidade", "coerencia"]},
                        "error": str(e)
                    }
                    st.session_state.policy_analysis = analysis
                    render_policy_overview(analysis)
                    render_ocde_analysis(analysis)
                
                finally:
                    if 'temp_path' in locals():
                        try: os.remove(temp_path)
                        except: pass

def render_policy_overview(analysis: dict):
    """Renderização com verificação de chaves"""
    st.markdown("---")
    st.subheader("📌 Visão Geral da Política")
    
    # Resumo Executivo
    with st.expander("Resumo Executivo", expanded=True):
        resumo = analysis.get('resumo_executivo', 'Resumo não disponível')
        word_count = len(resumo.split()) if resumo else 0
        st.caption(f"Extensão do Resumo: {word_count} palavras")
        st.markdown(f"""
        <div style='
            text-align: justify;
            color: #fff9f9;
            font-size: 14pt;
            line-height: 1.0;
        '>
            {resumo}
        </div>
        """, unsafe_allow_html=True)

def render_ocde_analysis(analysis: dict):
    """Seção OCDE com formatação revisada"""
    st.markdown("---")
    st.subheader("📋 Análise Detalhada por Critérios OCDE")
    
    if 'resumo_ocde' not in analysis:
        st.warning("⚠️ Dados da análise não encontrados")
        return
    
    criterios = {
        "relevancia": ("🎯 Relevância", "A política aborda problemas reais?"),
        "eficacia": ("📈 Eficácia", "Mecanismos para atingir objetivos?"),
        "eficiencia": ("💰 Eficiência", "Custo-benefício adequado?"),
        "impacto": ("🌍 Impacto", "Efeitos diretos e indiretos"),
        "sustentabilidade": ("🔄 Sustentabilidade", "Continuidade dos benefícios"),
        "coerencia": ("⚖️ Coerência", "Alinhamento com outras políticas")
    }

    col1, col2 = st.columns(2)

    with col1:
        for key in ['relevancia', 'eficacia', 'eficiencia']:
            render_ocde_card(
                title=criterios[key][0],
                content=analysis['resumo_ocde'].get(key, "Texto não disponível"),
                subtitle=criterios[key][1]
            )

    with col2:
        for key in ['impacto', 'sustentabilidade', 'coerencia']:
            render_ocde_card(
                title=criterios[key][0],
                content=analysis['resumo_ocde'].get(key, "Texto não disponível"),
                subtitle=criterios[key][1]
            )

def render_ocde_card(title: str, content: str, subtitle: str):
    """Componente com verificação de qualidade"""
    with st.expander(f"{title} - *{subtitle}*", expanded=True):
        if len(content.split()) < 50:
            st.warning("Análise abaixo do padrão mínimo de qualidade")
            st.code(content)
        else:
            st.markdown(f"""
            <div style='
                padding: 1rem;
                border-radius: 0.5rem;
                background: #f8f9fa;
                border-left: 4px solid #2e8b57;
                margin-bottom: 1rem;
                color: #000;
                font-size: 12pt;
                line-height: 1.4;
                text-align: justify;
            '>
                {content}
            </div>
            """, unsafe_allow_html=True)
        st.caption(f"Critério: {subtitle}")

if __name__ == "__main__":
    show_policy_dashboard()