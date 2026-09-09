import requests

def enviar_notificacao_teams(
    webhook_url, dt_inicio, dt_fim, tot_geral, tot_humanos, sla_taxa, 
    backlog_critico, tot_zabbix, tms_str="N/A", pct_resolv_24h="N/A", 
    prio_str="", areas_str=""
):
    """Envia um Adaptive Card executivo formatado para o Microsoft Teams com divisórias e link de acesso."""
    
    body_elements = [
        {
            "type": "TextBlock",
            "text": f"📅 **Período de Análise:** {dt_inicio} até {dt_fim}",
            "weight": "Bolder",
            "size": "Medium"
        },
        {
            "type": "TextBlock",
            "text": "---------------------------------------------------------------------------------",
            "spacing": "Small"
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "Total Volumetria:", "value": str(tot_geral)},
                {"title": "Atendimento:", "value": str(tot_humanos)},
                {"title": "Alertas Zabbix:", "value": str(tot_zabbix)},
                {"title": "SLA de Incidentes:", "value": str(sla_taxa)},
                {"title": "Backlog de Incidentes Crítico (>3 dias):", "value": str(backlog_critico)},
                {"title": "Tempo Médio Solução (TMS):", "value": str(tms_str)},
                {"title": "Resolvidos em < 24h:", "value": str(pct_resolv_24h)}
            ]
        }
    ]

    if prio_str:
        body_elements.extend([
            {
                "type": "TextBlock",
                "text": "---------------------------------------------------------------------------------",
                "spacing": "Medium"
            },
            {"type": "TextBlock", "text": "🚨 **Incidentes por Prioridade:**", "weight": "Bolder", "spacing": "Small"},
            {"type": "TextBlock", "text": prio_str, "wrap": True, "size": "Small"}
        ])

    if areas_str:
        body_elements.extend([
            {
                "type": "TextBlock",
                "text": "---------------------------------------------------------------------------------",
                "spacing": "Medium"
            },
            {"type": "TextBlock", "text": "🏢 **Volume por Área (Incidente / Requisição):**", "weight": "Bolder", "spacing": "Small"},
            {"type": "TextBlock", "text": areas_str, "wrap": True, "size": "Small"}
        ])

    # Bloco com o Link de Acesso Rápido ao Painel no Streamlit
    body_elements.extend([
        {
            "type": "TextBlock",
            "text": "---------------------------------------------------------------------------------",
            "spacing": "Medium"
        },
        {
            "type": "TextBlock",
            "text": "🌐 [Abrir Painel no Streamlit](https://painel-glpi-opzwskebbjksedrb4v8aew.streamlit.app)",
            "size": "Medium",
            "weight": "Bolder",
            "wrap": True
        },
        {
            "type": "TextBlock",
            "text": "⚠️ *Notificação enviada automaticamente via Painel Gerencial Streamlit.*",
            "size": "Small",
            "isSubtle": True,
            "italic": True,
            "spacing": "Small"
        }
    ])

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptivecard.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": body_elements
                }
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=payload, headers={'Content-Type': 'application/json'}, timeout=10)
        return response.status_code in [200, 202]
    except Exception:
        return False