import os
import pandas as pd
import re
import urllib
from sqlalchemy import create_engine
import base64
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By

# 1. Configurar o acesso ao banco de dados e obter CNPJs
quem_esta_usando = os.getlogin()
credenciais = pd.read_csv(fr"C:\Users\{quem_esta_usando}\Documents\acesso_banco.txt",header=None)
server = '10.175.84.61'
database = 'Solis'
username = re.search(r'username:\s*(.*)', credenciais.iloc[0,0]).group(1)
password = re.search(r'password:\s*(.*)' ,credenciais.iloc[1,0]).group(1)
connection_string = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password
params = urllib.parse.quote_plus(connection_string)
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

query_cnpjs = '''SELECT DISTINCT(ID_CNPJ_Fundo)
FROM CVM.Informe_Mensal.inf_mensal_fidc_tab_I
WHERE Data_Posicao = '2026-03-31' '''

print("Consultando os CNPJs no banco de dados...")
df_cnpj_cvm = pd.read_sql(query_cnpjs, engine)
fundos_a_buscar = df_cnpj_cvm['ID_CNPJ_Fundo'].dropna().unique()
print(f"Total de fundos distintos encontrados: {len(fundos_a_buscar)}")

# 2. Configurar pastas
repositorio_salvar = r"C:\Users\marcos.chaves\Documents\Python\CVM\CVM_Analise_Mercado\Documentos_CVM"
if not os.path.exists(repositorio_salvar):
    os.makedirs(repositorio_salvar)

# Lista para armazenar as informações para o Excel
registros_excel = []

# 3. Configurar Selenium WebDriver
print("Iniciando o navegador...")
options = webdriver.ChromeOptions()
options.add_argument('--log-level=3') 
driver = webdriver.Chrome(options=options)

# Aumentamos o tempo limite para scripts assíncronos (fetch)
driver.set_script_timeout(60)

print("Iniciando a busca de regulamentos via Selenium...")
for cnpj in fundos_a_buscar:
    cnpj_clean = re.sub(r'\D', '', str(cnpj))
    if len(cnpj_clean) != 14:
        continue
        
    url_pesquisa = f"https://fnet.bmfbovespa.com.br/fnet/publico/pesquisarGerenciadorDocumentosDados?d=0&s=0&l=200&cnpjFundo={cnpj_clean}"
    
    try:
        driver.get(url_pesquisa)
        texto = driver.execute_script("return document.body.innerText;")
        
        try:
            dados = json.loads(texto)
        except json.JSONDecodeError:
            print(f"[{cnpj_clean}] Erro ao interpretar JSON. Resposta inesperada.")
            registros_excel.append({
                "CNPJ Fundo": cnpj_clean,
                "Data Referência": "-",
                "Link Download API": "-",
                "Caminho Arquivo": "-",
                "Status": "Erro ao ler dados FNET"
            })
            continue
            
        documentos = dados.get('data', [])
        regulamentos = [d for d in documentos if d.get('categoriaDocumento') == 'Regulamento' and d.get('status') == 'AC']
        
        if regulamentos:
            # Ordenar os regulamentos pela dataReferencia para garantir que pegamos o mais recente
            def get_data(doc):
                data_str = doc.get('dataReferencia', '01/01/1900')[:10]
                try:
                    return datetime.strptime(data_str, '%d/%m/%Y')
                except:
                    return datetime(1900, 1, 1)
                    
            regulamentos.sort(key=get_data, reverse=True)
            doc_recente = regulamentos[0]
            doc_id = doc_recente['id']
            data_ref = doc_recente.get('dataReferencia', '').replace('/', '')
            
            nome_arquivo = f"Regulamento_{cnpj_clean}_{data_ref}.pdf"
            caminho_arquivo = os.path.join(repositorio_salvar, nome_arquivo)
            url_download = f"https://fnet.bmfbovespa.com.br/fnet/publico/downloadDocumento?id={doc_id}"
            
            # Registramos no Excel independente de precisar baixar ou já existir localmente
            registros_excel.append({
                "CNPJ Fundo": cnpj_clean,
                "Data Referência": doc_recente.get('dataReferencia', ''),
                "Link Download API": url_download,
                "Caminho Arquivo": caminho_arquivo,
                "Status": "Encontrado"
            })
            
            if not os.path.exists(caminho_arquivo):
                # Usamos fetch por debaixo dos panos para que o Chrome NÃO force o download para a pasta Downloads padrão do Windows.
                # Assim conseguimos interceptar a string JSON e processar o Base64, e nós mesmos salvamos na pasta certa.
                texto_pdf = driver.execute_async_script("""
                    var uri = arguments[0];
                    var callback = arguments[1];
                    fetch(uri)
                      .then(response => response.text())
                      .then(text => callback(text))
                      .catch(err => callback(null));
                """, url_download)
                
                if texto_pdf:
                    try:
                        # O FNET devolve JSON com as aspas (ex: '"JVBERi0x..."')
                        conteudo_b64 = json.loads(texto_pdf)
                        conteudo_pdf = base64.b64decode(conteudo_b64)
                        
                        # Salvando o arquivo de fato usando o python, diretamente na nossa pasta "Documentos_CVM"
                        with open(caminho_arquivo, 'wb') as f:
                            f.write(conteudo_pdf)
                        print(f"[{cnpj_clean}] Download concluído e corrigido: {nome_arquivo}")
                    except Exception as ex:
                        print(f"[{cnpj_clean}] Falha na conversão base64. Erro: {ex}")
                else:
                    print(f"[{cnpj_clean}] O fetch não retornou nada para o arquivo.")
            else:
                print(f"[{cnpj_clean}] Arquivo já existente na pasta: {nome_arquivo}")
        else:
            print(f"[{cnpj_clean}] Nenhum regulamento encontrado no FNET.")
            registros_excel.append({
                "CNPJ Fundo": cnpj_clean,
                "Data Referência": "-",
                "Link Download API": "-",
                "Caminho Arquivo": "-",
                "Status": "Nenhum Regulamento Encontrado"
            })
            
    except Exception as e:
        print(f"[{cnpj_clean}] Erro ao processar via Selenium: {e}")
        registros_excel.append({
            "CNPJ Fundo": cnpj_clean,
            "Data Referência": "-",
            "Link Download API": "-",
            "Caminho Arquivo": "-",
            "Status": f"Erro no Processamento: {str(e)}"
        })

# Fechar o navegador ao final
print("Finalizando e fechando o navegador...")
driver.quit()

# 4. Gerar relatório Excel
print("Gerando relatório Excel...")
df_relatorio = pd.DataFrame(registros_excel)
caminho_excel = os.path.join(repositorio_salvar, "Relatorio_Regulamentos_CVM.xlsx")
df_relatorio.to_excel(caminho_excel, index=False)
print(f"Relatório gerado com sucesso em: {caminho_excel}")
