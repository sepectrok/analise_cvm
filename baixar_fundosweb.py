import os
import pandas as pd
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Pastas e Arquivos
repositorio_salvar = r"Documentos_CVM"
caminho_excel = os.path.join(repositorio_salvar, "Relatorio_Regulamentos_CVM.xlsx")

print("Carregando o Excel...")
try:
    df = pd.read_excel(caminho_excel)
except FileNotFoundError:
    print(f"Erro: Arquivo Excel não encontrado em {caminho_excel}")
    exit()

# 2. Filtrar os fundos que falharam
mask_nao_encontrados = df['Status'].str.contains('Nenhum Regulamento Encontrado|Erro', na=False, case=False)
fundos_pendentes = df[mask_nao_encontrados]['CNPJ Fundo'].dropna().unique()

print(f"Total de fundos pendentes para buscar na CVM (FundosWeb): {len(fundos_pendentes)}")

if len(fundos_pendentes) == 0:
    print("Nenhum fundo pendente. Todos já foram baixados pela FNET.")
    exit()

# 3. Configurar o WebDriver
options = webdriver.ChromeOptions()
options.add_argument('--log-level=3')
# Forçar download para nossa pasta sem perguntar
prefs = {
    "download.default_directory": repositorio_salvar,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

print("Iniciando varredura na CVM FundosWeb...")

def obter_arquivo_mais_recente(diretorio):
    """Retorna o caminho absoluto do arquivo PDF mais recente na pasta."""
    arquivos_pdf = [os.path.join(diretorio, f) for f in os.listdir(diretorio) if f.endswith('.pdf')]
    if not arquivos_pdf:
        return None
    return max(arquivos_pdf, key=os.path.getctime)

# 4. Iterar sobre fundos pendentes
for cnpj in fundos_pendentes:
    cnpj_str = str(cnpj).zfill(14)
    # Formatar CNPJ para o site da CVM (se necessário, o site costuma aceitar com ou sem pontuação)
    # Vou enviar limpo, o Angular deles formata automaticamente.
    cnpj_clean = re.sub(r'\D', '', cnpj_str)
    print(f"\n--- Buscando CNPJ: {cnpj_clean} ---")
    
    try:
        driver.get("https://web.cvm.gov.br/app/fundosweb/#/fundos/consultar")
        time.sleep(3) # Aguardar Angular instanciar a página
        
        # Ocultar div de loading se estiver travando a tela (Angular blockUI)
        driver.execute_script("var els = document.getElementsByClassName('block-ui-overlay'); for(var i=0; i<els.length; i++){els[i].style.display='none';}")
        
        # Input de CNPJ (id=txtCnpj)
        input_cnpj = wait.until(EC.presence_of_element_located((By.ID, "txtCnpj")))
        input_cnpj.clear()
        input_cnpj.send_keys(cnpj_clean)
        # Forçar o Angular a reconhecer a mudança (essencial para SPAs)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", input_cnpj)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", input_cnpj)
        time.sleep(1)
        
        # Botão Pesquisar
        btn_pesquisar = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@title='Pesquisar'] | //button[contains(text(), 'Pesquisar')]")))
        driver.execute_script("arguments[0].click();", btn_pesquisar)
        
        time.sleep(4) # Aguardar busca na tabela carregar
        
        # Clicar na Lupa (Visualizar detalhe)
        try:
            # Aguarda a tabela renderizar
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Visualizar detalhe do Fundo']")))
            
            # Buscar as linhas que contêm a lupa
            linhas = driver.find_elements(By.XPATH, "//tr[.//a[@title='Visualizar detalhe do Fundo']]")
            lupa = None
            
            # Procurar uma linha que não contenha a situação 'CANCELAD' (Cancelado/Cancelada)
            for linha in linhas:
                if "CANCELAD" not in linha.text.upper():
                    lupa = linha.find_element(By.CSS_SELECTOR, "a[title='Visualizar detalhe do Fundo']")
                    break
            
            # Se todas as linhas estiverem canceladas (ou não encontrou), pega a primeira disponível
            if not lupa and linhas:
                lupa = linhas[0].find_element(By.CSS_SELECTOR, "a[title='Visualizar detalhe do Fundo']")
                
            driver.execute_script("arguments[0].click();", lupa)
        except Exception as e:
            print(f"[{cnpj_clean}] Fundo não retornado na pesquisa da CVM.")
            df.loc[df['CNPJ Fundo'] == cnpj, 'Status'] = "Fundo inexistente no FundosWeb CVM"
            continue
            
        time.sleep(4) # Carregando abas do fundo
        
        # Clicar na aba Regulamento
        aba_regulamento = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Regulamento')] | //a[contains(text(), 'Regulamento')]")))
        driver.execute_script("arguments[0].click();", aba_regulamento)
        
        time.sleep(3)
        
        # Clicar no botão Download (Pegamos o primeiro da tabela, que geralmente é o mais recente ativo)
        btn_download = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[title='Download do Arquivo']")))
        
        # Como o nome do arquivo que vem do servidor é aleatório, vamos ver qual era o pdf mais recente ANTES do clique
        arquivo_recente_antes = obter_arquivo_mais_recente(repositorio_salvar)
        
        # Clicamos via JS para evitar sobreposição
        driver.execute_script("arguments[0].click();", btn_download)
        print(f"[{cnpj_clean}] Comando de download disparado.")
        
        # Esperar até que um arquivo novo apareça e não termine com '.crdownload'
        novo_arquivo = None
        tentativas = 0
        while tentativas < 30:
            time.sleep(1)
            arquivo_recente_depois = obter_arquivo_mais_recente(repositorio_salvar)
            if arquivo_recente_depois != arquivo_recente_antes and not arquivo_recente_depois.endswith('.crdownload'):
                novo_arquivo = arquivo_recente_depois
                break
            tentativas += 1
            
        if novo_arquivo:
            # Temos que usar uma data no nome, caso a CVM nao informe, usamos YYYYMMDD de hoje
            hoje = time.strftime("%Y%m%d")
            nome_final = f"Regulamento_{cnpj_clean}_{hoje}_CVM.pdf"
            caminho_final = os.path.join(repositorio_salvar, nome_final)
            
            # Se já existir um igual, deleta
            if os.path.exists(caminho_final):
                os.remove(caminho_final)
                
            os.rename(novo_arquivo, caminho_final)
            print(f"[{cnpj_clean}] Regulamento salvo e renomeado: {nome_final}")
            
            # Atualizar o dataframe
            linhas_alvo = df['CNPJ Fundo'] == cnpj
            df.loc[linhas_alvo, 'Status'] = "Encontrado via CVM portal novo"
            df.loc[linhas_alvo, 'Caminho Arquivo'] = caminho_final
            df.loc[linhas_alvo, 'Link Download API'] = "Portal CVM FundosWeb"
        else:
            print(f"[{cnpj_clean}] Falha no download (timeout).")
            
    except Exception as e:
        print(f"[{cnpj_clean}] Erro ao buscar na CVM: {str(e)[:100]}")

driver.quit()

print("\nSalvando alterações no Excel...")
df.to_excel(caminho_excel, index=False)
print("Planilha atualizada com sucesso!")
