from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from playwright.async_api import async_playwright
import pandas as pd
import asyncio
import time
from bs4 import BeautifulSoup
import unicodedata
import os
import aiofiles
import json
from datetime import datetime

# Configuración
URL_BASE = "https://www.snieg.mx/cni/indicadores.aspx?idOrden=1.1"
ARCHIVO_URLS = "metadatos_links.txt"
MAX_CONCURRENT_PAGES = 10
REQUEST_TIMEOUT = 60000
RETRY_ATTEMPTS = 3

# Columnas para el CSV
columnas = [
    "Índice",
    "URL",
    "Nombre del Indicador",
    "Tema/Subsistema", 
    "Objetivo", 
    "Definición", 
    "Unidad de medida",
    "Cobertura geográfica", 
    "Periodicidad", 
    "Periodo de referencia",
    "Oportunidad", 
    "Cobertura temporal",
    "Estándares o recomendaciones nacionales y/o internacionales",
    "Observaciones", 
    "Fuente/Proyecto", 
    "Variable", 
    "IIN"
]

# Mapeo de etiquetas HTML a nombres de columnas
etiquetas = {
    "Tema/subtema": "Tema/Subsistema",
    "Objetivo": "Objetivo",
    "Definición": "Definición",
    "Unidad de medida": "Unidad de medida",
    "Cobertura geográfica": "Cobertura geográfica",
    "Periodicidad": "Periodicidad",
    "Periodo de referencia": "Periodo de referencia",
    "Año base": "Año base",
    "Oportunidad": "Oportunidad",
    "Cobertura temporal": "Cobertura temporal",
    "Estándares o recomendaciones nacionales y/o internacionales": "Estándares o recomendaciones nacionales y/o internacionales",
    "Observaciones": "Observaciones",
    "Fuente/Proyecto": "Fuente/Proyecto",
    "Variable": "Variable",
    "Información de Interés Nacional": "IIN"
}

def extraer_urls_metadatos():
    """Extrae las URLs de metadatos usando Selenium"""
    print("🚀 Iniciando extracción de URLs de metadatos...")
    
    start_time = time.perf_counter()
    
    # Configurar Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        driver.get(URL_BASE)
        time.sleep(5)  # Espera carga inicial

        # Abrir todos los temas cerrados
        closed = driver.find_elements(By.CSS_SELECTOR, "img[alt='Abrir']")
        for img in closed:
            driver.execute_script("arguments[0].scrollIntoView();", img)
            driver.execute_script("arguments[0].click();", img)
            time.sleep(0.5)

        # Extraer links de metadatos
        links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='infometadato']") if a.get_attribute("href")]

        # Guardar
        with open(ARCHIVO_URLS, "w", encoding="utf-8") as f:
            for link in sorted(set(links)):
                f.write(link + "\n")

        elapsed = time.perf_counter() - start_time
        print(f"✔ {len(links)} enlaces guardados en {ARCHIVO_URLS}")
        print(f"⏱ Tiempo extracción URLs: {elapsed:.2f} segundos")
        return len(links)
        
    finally:
        driver.quit()

def leer_urls_desde_archivo(nombre_archivo):
    """Lee las URLs desde un archivo de texto"""
    urls = []
    try:
        with open(nombre_archivo, 'r', encoding='utf-8') as archivo:
            for linea in archivo:
                url = linea.strip()
                if url and url.startswith('http'):
                    urls.append(url)
        print(f"Se leyeron {len(urls)} URLs desde {nombre_archivo}")
        return urls
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {nombre_archivo}")
        return []
    except Exception as e:
        print(f"Error al leer el archivo: {str(e)}")
        return []

def normalizar_texto(texto):
    """Normaliza el texto eliminando acentos y caracteres especiales para comparación"""
    if not texto:
        return ""
    texto = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.lower().strip()

async def extraer_nombre_indicador(page):
    """Extrae el nombre del indicador usando Playwright"""
    try:
        await page.wait_for_selector("body", timeout=10000)
        
        selectores = [
            "#m_treenomIndicador",
            "#lbNombreInd",
            "td.SizeGralTitulo:has(b)",
            "b:has-text('Nombre del Indicador Clave:')"
        ]
        
        for selector in selectores:
            try:
                nombre_element = await page.query_selector(selector)
                if nombre_element:
                    nombre = await nombre_element.inner_text()
                    nombre = nombre.strip()
                    if nombre:
                        if "Nombre del Indicador Clave:" in nombre:
                            nombre = nombre.split(":", 1)[1].strip()
                        return nombre
            except:
                continue
        
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        
        elementos = soup.find_all(string=lambda t: t and "Nombre del Indicador" in t)
        for elemento in elementos:
            if ":" in elemento:
                return elemento.split(":", 1)[1].strip()
        
        return "No se pudo extraer el nombre del indicador"
    
    except Exception as e:
        return f"Error al extraer el nombre: {str(e)}"

async def extraer_estandares_recomendaciones(page):
    """Extrae el contenido de 'Estándares o recomendaciones nacionales y/o internacionales'"""
    try:
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        
        elementos = soup.find_all("b")
        for elemento in elementos:
            if elemento.text and "Estándares o recomendaciones nacionales y/o internacionales" in elemento.text:
                tr_sig = elemento.find_parent("tr").find_next_sibling("tr")
                if tr_sig:
                    textos = []
                    for a in tr_sig.find_all("a"):
                        textos.append(a.get_text(strip=True))
                    
                    if not textos:
                        return tr_sig.get_text(" ", strip=True).replace("\xa0", "")
                    
                    return "\n".join(textos)
        
        return "No se encontró la sección de estándares"
    
    except Exception as e:
        return f"Error al extraer estándares: {str(e)}"

async def extraer_metadato(soup, etiqueta_buscada):
    """Extrae el valor de un metadato específico basado en su etiqueta"""
    try:
        elementos = soup.find_all(["b", "td", "tr"], string=lambda t: t and etiqueta_buscada.lower() in str(t).lower())
        
        for elemento in elementos:
            if etiqueta_buscada.lower() in elemento.get_text().lower():
                padre = elemento.find_parent("tr")
                if padre:
                    siguiente = padre.find_next_sibling("tr")
                    if siguiente:
                        td_valor = siguiente.find("td", class_="SizeGralApartado")
                        if td_valor:
                            return td_valor.get_text(" ", strip=True).replace("\xa0", "")
                        
                        td_valor = siguiente.find("td")
                        if td_valor:
                            return td_valor.get_text(" ", strip=True).replace("\xa0", "")
        
        return None
    except Exception as e:
        print(f"Error al extraer {etiqueta_buscada}: {str(e)}")
        return None

async def extraer_todos_metadatos(soup):
    """Extrae todos los metadatos de la página"""
    metadatos = {}
    
    for etiqueta_html, etiqueta_csv in etiquetas.items():
        if etiqueta_html == "Estándares o recomendaciones nacionales y/o internacionales":
            continue
        
        valor = await extraer_metadato(soup, etiqueta_html)
        metadatos[etiqueta_csv] = valor
    
    return metadatos

async def procesar_url(browser, url, indice, semaphore):
    """Procesa una URL individual con control de concurrencia"""
    async with semaphore:
        page = None
        for attempt in range(RETRY_ATTEMPTS):
            try:
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1280, "height": 720})
                page.set_default_timeout(REQUEST_TIMEOUT)
                
                await page.goto(url, wait_until="networkidle", timeout=45000)
                
                nombre_indicador = await extraer_nombre_indicador(page)
                content = await page.content()
                soup = BeautifulSoup(content, "lxml")
                estandares = await extraer_estandares_recomendaciones(page)
                metadatos = await extraer_todos_metadatos(soup)
                
                fila = [
                    indice,
                    url,
                    nombre_indicador,
                    metadatos.get("Tema/Subsistema"),
                    metadatos.get("Objetivo"),
                    metadatos.get("Definición"),
                    metadatos.get("Unidad de medida"),
                    metadatos.get("Cobertura geográfica"),
                    metadatos.get("Periodicidad"),
                    metadatos.get("Periodo de referencia"),
                    metadatos.get("Oportunidad"),
                    metadatos.get("Cobertura temporal"),
                    estandares,
                    metadatos.get("Observaciones"),
                    metadatos.get("Fuente/Proyecto"),
                    metadatos.get("Variable"),
                    metadatos.get("IIN")
                ]
                
                print(f"✅ Procesada URL {indice}: {nombre_indicador[:50]}...")
                return fila
                
            except Exception as e:
                print(f"❌ Intento {attempt+1} fallido para URL {indice}: {str(e)}")
                if attempt == RETRY_ATTEMPTS - 1:
                    error_msg = f"Error después de {RETRY_ATTEMPTS} intentos: {str(e)}"
                    print(f"❌ Error procesando {url}: {error_msg}")
                    return [indice, url, error_msg] + [None] * (len(columnas) - 3)
                await asyncio.sleep(5)
            finally:
                if page:
                    await page.close()
        
        return [indice, url, "Error: No se pudo procesar después de múltiples intentos"] + [None] * (len(columnas) - 3)

async def guardar_progreso_parcial(filas, filename):
    """Guarda el progreso actual en un archivo CSV (se mantiene CSV para progreso por eficiencia)"""
    df_temp = pd.DataFrame(filas, columns=columnas)
    df_temp.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"💾 Progreso guardado: {filename}")

async def cargar_progreso_previo(filename):
    """Carga el progreso previo si existe"""
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            print(f"📂 Cargando progreso previo: {len(df)} URLs procesadas")
            return df.values.tolist()
        except Exception as e:
            print(f"Error al cargar progreso previo: {str(e)}")
    return []

async def extraer_metadatos_indicadores():
    """Extrae metadatos de todos los indicadores usando Playwright"""
    print("🚀 Iniciando extracción de metadatos de indicadores...")
    
    start = time.perf_counter()
    
    # Leer URLs desde el archivo
    urls = leer_urls_desde_archivo(ARCHIVO_URLS)
    
    if not urls:
        print("❌ No hay URLs para procesar. Ejecuta primero la extracción de URLs.")
        return
    
    print(f"Total de URLs a procesar: {len(urls)}")
    
    # Crear directorio de resultados si no existe
    os.makedirs("resultados", exist_ok=True)
    
    # Cargar progreso previo si existe
    progreso_archivo = "resultados/progreso_parcial.csv"
    filas_completadas = await cargar_progreso_previo(progreso_archivo)
    
    # Identificar URLs ya procesadas
    urls_procesadas = {fila[1] for fila in filas_completadas}
    urls_restantes = [url for i, url in enumerate(urls, 1) if url not in urls_procesadas]
    
    print(f"🔄 URLs ya procesadas: {len(urls_procesadas)}")
    print(f"📋 URLs por procesar: {len(urls_restantes)}")
    
    if not urls_restantes:
        print("✅ Todas las URLs ya han sido procesadas.")
        return
    
    # Configurar semáforo para limitar concurrencia
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # Procesar URLs restantes
        tareas = []
        for i, url in enumerate(urls_restantes, len(filas_completadas) + 1):
            tarea = asyncio.create_task(procesar_url(browser, url, i, semaphore))
            tareas.append(tarea)
        
        # Recolectar resultados
        filas_nuevas = []
        for i, tarea_completada in enumerate(asyncio.as_completed(tareas), 1):
            try:
                fila = await tarea_completada
                filas_nuevas.append(fila)
                filas_completadas.append(fila)
                
                # Guardar progreso cada 10 URLs
                if i % 10 == 0:
                    await guardar_progreso_parcial(filas_completadas, progreso_archivo)
                    
            except Exception as e:
                print(f"Error inesperado procesando tarea: {str(e)}")
        
        await browser.close()

    # Combinar resultados y guardar
    todas_las_filas = filas_completadas
    
    # Crear DataFrame y guardar en CSV
    df = pd.DataFrame(todas_las_filas, columns=columnas)
    
    # Guardar en XLSX con marca de tiempo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"resultados/metadatos_indicadores_{timestamp}.xlsx"
    df.to_excel(nombre_archivo, index=False, engine='openpyxl')
    
    # También guardar una copia sin timestamp
    df.to_excel("resultados/metadatos_indicadores_completo.xlsx", index=False, engine='openpyxl')
    
    # Eliminar archivo de progreso parcial si existe
    if os.path.exists(progreso_archivo):
        os.remove(progreso_archivo)
    
    print(f"✔ XLSX '{nombre_archivo}' creado exitosamente.")
    print(f"⏱ Tiempo total: {time.perf_counter() - start:.2f} segundos")
    
    # Mostrar resumen
    exitos = sum(1 for fila in todas_las_filas if not str(fila[2]).startswith("Error"))
    print(f"\nResumen de la extracción:")
    print(f"URLs procesadas exitosamente: {exitos}/{len(urls)}")
    print(f"URLs con errores: {len(urls) - exitos}/{len(urls)}")
    
    # Mostrar primeros resultados
    print("\nPrimeros resultados:")
    print(df[["Índice", "Nombre del Indicador"]].head(10).to_string(index=False))

async def main():
    """Función principal que ejecuta todo el proceso"""
    print("=" * 60)
    print("SCRAPING COMPLETO - SISTEMA NACIONAL DE INDICADORES")
    print("=" * 60)
    
    # Paso 1: Extraer URLs de metadatos
    total_urls = extraer_urls_metadatos()
    
    if total_urls > 0:
        # Paso 2: Extraer metadatos de los indicadores
        await extraer_metadatos_indicadores()
    else:
        print("❌ No se pudieron extraer URLs. Verifica la conexión a internet.")

if __name__ == "__main__":
    # Configurar el bucle de eventos para Windows si es necesario
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())