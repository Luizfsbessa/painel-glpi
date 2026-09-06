import os
import requests
import urllib3
import pandas as pd
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = "http://192.168.16.67/ssi/apirest.php"
APP_TOKEN = "DSO6AA2eAcsutCL6biwksMVbFWKW7XIOSqZcZmLy"
USER_TOKEN = "09OCfWZmZIhkbp37vbXfLHF2ktSuTCiokXgrtfpS"
EXCEL_PATH = "relatorio glpi.xlsx"
SHEET_NAME = "Chamados"

MAPA_STATUS = {
    1: "Novo",
    2: "Em atendimento (atribuído)",
    3: "Em atendimento (planejado)",
    4: "Pendente",
    5: "Solucionado",
    6: "Fechado"
}

MAPA_PRIORIDADE = {
    1: "Muito baixa",
    2: "Baixa",
    3: "Média",
    4: "Alta",
    5: "Muito alta",
    6: "Urgente"
}

# Regra de SLA em horas por prioridade solicitada
LIMITES_SLA_HORAS = {
    "Muito baixa": 24,    # Fallback caso não especificado
    "Baixa": 10,
    "Média": 6,
    "Media": 6,
    "Alta": 4,
    "Muito alta": 2,
    "Muito Alta": 2,
    "Urgente": 2
}

def obter_nome_relacional(headers, endpoint, item_id):
    if not item_id or item_id == 0:
        return None
    try:
        resp = requests.get(f"{URL}/{endpoint}/{item_id}", headers=headers, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("completename") or data.get("name")
    except:
        pass
    return None

def obter_nome_usuario(headers, user_id):
    if not user_id or user_id == 0:
        return None
    try:
        resp = requests.get(f"{URL}/User/{user_id}", headers=headers, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            nome = data.get("firstname", "")
            sobrenome = data.get("realname", "")
            completo = f"{nome} {sobrenome}".strip()
            return completo if completo else data.get("name")
    except:
        pass
    return None

def obter_nome_grupo(headers, group_id):
    if not group_id or group_id == 0:
        return None
    try:
        resp = requests.get(f"{URL}/Group/{group_id}", headers=headers, verify=False)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("completename") or data.get("name")
    except:
        pass
    return None

def buscar_atores_ticket(headers, ticket_id):
    requerente, tecnico, grupo_req, grupo_tec = None, None, None, None
    
    try:
        resp = requests.get(f"{URL}/Ticket/{ticket_id}/Ticket_User/", headers=headers, verify=False)
        if resp.status_code == 200:
            for rel in resp.json():
                tipo = rel.get("type")
                uid = rel.get("users_id")
                nome_u = obter_nome_usuario(headers, uid)
                if tipo == 1 and not requerente:
                    requerente = nome_u
                elif tipo == 2 and not tecnico:
                    tecnico = nome_u
    except:
        pass

    try:
        resp = requests.get(f"{URL}/Ticket/{ticket_id}/Group_Ticket/", headers=headers, verify=False)
        if resp.status_code == 200:
            for rel in resp.json():
                tipo = rel.get("type")
                gid = rel.get("groups_id")
                nome_g = obter_nome_grupo(headers, gid)
                if tipo == 1 and not grupo_req:
                    grupo_req = nome_g
                elif tipo == 2 and not grupo_tec:
                    grupo_tec = nome_g
    except:
        pass

    return requerente, tecnico, grupo_req, grupo_tec

def calcular_sla_excedido(data_abertura, data_solucao, prioridade):
    """
    Calcula se o SLA foi excedido com base nas horas limite da criticidade:
    - Muito alta: 2h
    - Alta: 4h
    - Média: 6h
    - Baixa: 10h
    """
    if not data_abertura:
        return "Não"
    
    try:
        dt_ini = pd.to_datetime(data_abertura)
        dt_fim = pd.to_datetime(data_solucao) if pd.notnull(data_solucao) else datetime.now()
        
        horas_decorridas = (dt_fim - dt_ini).total_seconds() / 3600.0
        limite_horas = LIMITES_SLA_HORAS.get(str(prioridade).strip(), 24)
        
        if horas_decorridas > limite_horas:
            return "Sim"
    except:
        pass
    return "Não"

def atualizar():
    if not os.path.exists(EXCEL_PATH):
        print("Arquivo Excel não encontrado.")
        return

    print(f"Lendo a aba '{SHEET_NAME}' do arquivo Excel...")
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    
    sess = requests.get(
        f"{URL}/initSession", 
        headers={"App-Token": APP_TOKEN}, 
        params={"user_token": USER_TOKEN}, 
        verify=False
    )
    if sess.status_code != 200:
        print(f"Erro de autenticação: {sess.status_code}")
        return
    st_token = sess.json().get("session_token")

    headers = {
        "App-Token": APP_TOKEN,
        "Session-Token": st_token,
        "Content-Type": "application/json"
    }

    todos_dados = []
    lote_tamanho = 1000
    limite_total = 10000

    print("Buscando chamados do GLPI em lotes...")
    for inicio in range(0, limite_total, lote_tamanho):
        fim = inicio + lote_tamanho - 1
        params = {
            "range": f"{inicio}-{fim}",
            "sort": "id",
            "order": "DESC"
        }
        
        resp = requests.get(f"{URL}/Ticket/", headers=headers, params=params, verify=False)
        if resp.status_code in [200, 206]:
            dados_lote = resp.json()
            if isinstance(dados_lote, dict):
                dados_lote = list(dados_lote.values())
            if not dados_lote:
                break
            todos_dados.extend(dados_lote)
            if len(dados_lote) < lote_tamanho:
                break
        else:
            break

    col_id = 'ID'
    col_status = 'Status'
    col_sol = 'Data da solução'
    col_prio = 'Prioridade'
    col_sla = 'Tempo para resolver excedido'
    col_abertura = 'Data de abertura'

    if col_id not in df.columns:
        print("Coluna 'ID' não encontrada na aba Chamados.")
        requests.get(f"{URL}/killSession", headers=headers, verify=False)
        return

    api_dict = {}
    for item in todos_dados:
        if isinstance(item, dict):
            tid = item.get("id")
            st_num = item.get("status")
            st_texto = MAPA_STATUS.get(int(st_num), str(st_num)) if st_num is not None else "Novo"
            prio_num = item.get("priority", 2)
            prio_texto = MAPA_PRIORIDADE.get(int(prio_num), "Baixa")
            
            if tid is not None:
                api_dict[str(tid).strip()] = {
                    "id": tid,
                    "status": st_texto,
                    "solvedate": item.get("solvedate"),
                    "priority": prio_texto,
                    "date": item.get("date")
                }

    df['id_limpo'] = df[col_id].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    ids_existentes_planilha = set(df['id_limpo'])

    for col in [col_status, col_sol, col_sla]:
        if col in df.columns:
            df[col] = df[col].astype(object)

    atualizados = 0
    # 1. Atualiza chamados existentes (inclusive recalculando o SLA se necessário)
    for idx, row in df.iterrows():
        tid_str = row['id_limpo']
        if tid_str in api_dict:
            novo_status = api_dict[tid_str]["status"]
            nova_sol = api_dict[tid_str]["solvedate"]
            prio_atual = row[col_prio] if col_prio in df.columns and pd.notnull(row[col_prio]) else api_dict[tid_str]["priority"]
            dt_abertura = row[col_abertura] if col_abertura in df.columns else api_dict[tid_str]["date"]
            
            if col_status in df.columns and novo_status is not None:
                df.at[idx, col_status] = str(novo_status)
            if col_sol in df.columns and nova_sol is not None:
                df.at[idx, col_sol] = nova_sol
            
            # Recalcula o SLA baseado na regra nova
            if col_sla in df.columns:
                df.at[idx, col_sla] = calcular_sla_excedido(dt_abertura, nova_sol, prio_atual)
                
            atualizados += 1

    df.drop(columns=['id_limpo'], inplace=True)

    # 2. Identifica e busca novos chamados
    novos_ids = [tid for tid in api_dict.keys() if tid not in ids_existentes_planilha]
    novos_registros = []

    if novos_ids:
        print(f"Encontrados {len(novos_ids)} novos chamados. Coletando dados completos...")
        for tid in novos_ids:
            det_resp = requests.get(f"{URL}/Ticket/{tid}", headers=headers, verify=False)
            if det_resp.status_code == 200:
                t_info = det_resp.json()
                
                st_num = t_info.get("status")
                st_texto = MAPA_STATUS.get(int(st_num), "Novo") if st_num is not None else "Novo"
                prio_num = t_info.get("priority", 2)
                prio_texto = MAPA_PRIORIDADE.get(int(prio_num), "Baixa")
                
                entidade_nome = obter_nome_relacional(headers, "Entity", t_info.get("entities_id"))
                categoria_nome = obter_nome_relacional(headers, "ITILCategory", t_info.get("itilcategories_id"))
                localizacao_nome = obter_nome_relacional(headers, "Location", t_info.get("locations_id"))

                requerente_nome, tecnico_nome, grupo_req, grupo_tec = buscar_atores_ticket(headers, tid)

                solvedate = t_info.get("solvedate")
                dt_abertura = t_info.get("date")
                
                # Aplica a nova regra de SLA por criticidade
                sla_excedido = calcular_sla_excedido(dt_abertura, solvedate, prio_texto)

                novo_row = {
                    col_id: t_info.get("id"),
                    'Título': t_info.get("name"),
                    'Entidade': entidade_nome,
                    'Categoria': categoria_nome,
                    'Tipo': "Incidente" if t_info.get("type") == 1 else "Requisição",
                    'Prioridade': prio_texto,
                    'Requerente - Requerente': requerente_nome,
                    'Atribuído - Técnico': tecnico_nome,
                    'Data de abertura': dt_abertura,
                    col_status: st_texto,
                    col_sol: solvedate,
                    'Atribuído - Grupo técnico': grupo_tec,
                    'Requerente - Grupo requerente': grupo_req,
                    'Última atualização': t_info.get("date_mod"),
                    'Localização': localizacao_nome,
                    'Tempo para resolver excedido': sla_excedido,
                    'Tarefas - Número de tarefas': 0,
                    'Tarefas - Duração': "0 segundo"
                }
                novos_registros.append(novo_row)

    requests.get(f"{URL}/killSession", headers=headers, verify=False)

    if novos_registros:
        df_novos = pd.DataFrame(novos_registros)
        for col in df.columns:
            if col not in df_novos.columns:
                df_novos[col] = None
        df_novos = df_novos[df.columns]
        
        df = pd.concat([df, df_novos], ignore_index=True)
        print(f"Inseridos {len(novos_registros)} novos chamados.")

    if col_status in df.columns:
        df[col_status] = df[col_status].fillna("Desconhecido").astype(str)

    # Padronização final de todas as colunas de data para datetime real
    colunas_data = ['Data de abertura', 'Última atualização', 'Data da solução']
    for c_data in colunas_data:
        if c_data in df.columns:
            df[c_data] = pd.to_datetime(df[c_data], errors='coerce')

    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

    print(f"Sucesso! {atualizados} chamados atualizados, SLA recalculado por criticidade e datas padronizadas na aba '{SHEET_NAME}'.")

if __name__ == "__main__":
    atualizar()