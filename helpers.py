# helpers.py
import json
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException


def init_driver(headless=True, download_dir=None):
    """
    Inicializa el WebDriver de Chrome en modo headless,
    configurando la carpeta de descargas si se proporciona.
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")  # Headless+descarga
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Si se quiere forzar descarga de PDF en lugar de abrirlos
    if download_dir:
        prefs = {
            "download.default_directory": os.path.abspath(download_dir),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(options=options)
    return driver


def navigate_to_sentencias(driver, wait):
    """
    Hace clic en la pestaña 'SENTENCIAS ESCRITAS' y espera a que carguen las tarjetas.
    """
    tab_xpath = "//label[contains(@class,'by-results') and normalize-space(text())='SENTENCIAS ESCRITAS']"
    sentencias_tab = wait.until(EC.element_to_be_clickable((By.XPATH, tab_xpath)))
    sentencias_tab.click()
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.result_card")))


def go_to_page(driver, wait, page):
    """
    Navega a la página indicada usando la paginación.
    """
    btn_xpath = f"//button[contains(@aria-label,'Go to page {page}')]"
    pagination_btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
    pagination_btn.click()
    selected_xpath = f"//button[@aria-current='true' and @aria-label='page {page}']"
    wait.until(EC.presence_of_element_located((By.XPATH, selected_xpath)))


def parse_cards(driver):
    """
    Devuelve la lista de elementos de tarjeta en la página actual.
    """
    return driver.find_elements(By.CSS_SELECTOR, "div.result_card")


def extract_card_info(card, wait, retries=3):
    """
    Extrae título, número de proceso, fecha y tema de una tarjeta WebElement.
    Maneja stale elements con reintentos.
    """
    for attempt in range(retries):
        try:
            title = card.find_element(By.CSS_SELECTOR, "span.card__title").text.strip()
            process = card.find_element(
                By.XPATH,
                ".//div[@class='card__info-title' and normalize-space(text())='Número de proceso:']"
                "/following-sibling::div[@class='card__info-value']"
            ).text.strip()
            date = card.find_element(
                By.XPATH,
                ".//div[@class='card__info-title' and normalize-space(text())='Fecha:']"
                "/following-sibling::div[@class='card__info-value']"
            ).text.strip()
            theme = card.find_element(
                By.XPATH,
                ".//div[@class='card__info-title' and normalize-space(text())='Tema:']"
                "/following-sibling::div[@class='card__info-value']"
            ).text.strip()
            return title, process, date, theme
        except StaleElementReferenceException:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            else:
                raise
        except NoSuchElementException:
            # Si falta algún campo, devolver valores vacíos
            return title, process, '', ''
    # Por defecto
    raise Exception("No se pudo extraer información de la tarjeta")


def wait_for_new_page(driver, wait, old_first_process, min_cards=5, timeout=30):
    """
    Espera a que la nueva página cargue completamente: suficientes tarjetas y proceso distinto al anterior.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            cards = parse_cards(driver)
            if len(cards) >= min_cards:
                _, process, _, _ = extract_card_info(cards[0], wait)
                if process != old_first_process:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutException(f"La página no cargó correctamente (primer proceso sigue {old_first_process})")

def extract_radicado(wait, retries=3):
    """
    Espera a que el panel lateral muestre 'Número de radicado' 
    y devuelve su valor. Retorna cadena vacía si falla.
    """
    for attempt in range(retries):
        try:
            # esperamos el contenedor de detalles
            panel = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.side-detail__actors"))
            )
            # buscamos la etiqueta y su valor
            radicado_elem = panel.find_element(
                By.XPATH,
                ".//span[@class='side-detail__label' and contains(normalize-space(),'Número de radicado')]/span[@class='side-detail__value']"
            )
            return radicado_elem.text.strip()
        except (TimeoutException, StaleElementReferenceException, NoSuchElementException):
            time.sleep(1)
    return ""

def download_pdf(driver, wait, target_dir, nombre_pdf, timeout=30):
    import os, time, requests, shutil
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    # 1) Abrir "VER ANÁLISIS" en pestaña nueva
    link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "VER ANÁLISIS")))
    href = link.get_attribute("href")
    original = driver.current_window_handle
    driver.execute_script("window.open(arguments[0], '_blank');", href)
    for h in driver.window_handles:
        if h != original:
            driver.switch_to.window(h)
            break

    # 2) Esperar a que cargue el panel de acciones (página lista)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.actions")))
    time.sleep(8)  # tiempo extra para asegurar carga completa

    # 3) Preparar monitor de carpeta de descargas temporales
    temp_dir = os.path.abspath(os.path.join(target_dir, os.pardir))
    before = set(f for f in os.listdir(temp_dir) if f.lower().endswith((".pdf", ".crdownload")))

    # 4) Click en botón DESCARGAR cuando esté listo
    btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.actions button.btn_primary")))
    btn.click()

    # 5) Esperar descarga o redirección a .pdf
    start = time.time()
    while time.time() - start < timeout:
        current = driver.current_url
        if current.lower().endswith(".pdf"):
            # caída a PDF directo: bajar con requests
            r = requests.get(current)
            path = os.path.join(target_dir, nombre_pdf)
            with open(path, "wb") as f:
                f.write(r.content)
            break

        # o detectar nuevo archivo en temp_dir
        after = set(f for f in os.listdir(temp_dir) if f.lower().endswith((".pdf", ".crdownload")))
        new = after - before
        if new:
            # identificar el .pdf completo (no .crdownload)
            pdfs = [f for f in new if f.lower().endswith(".pdf")]
            if pdfs:
                src = os.path.join(temp_dir, pdfs[0])
                dst = os.path.join(target_dir, nombre_pdf)
                shutil.move(src, dst)
                break

        time.sleep(1)
    else:
        raise TimeoutException("No se completó la descarga del PDF en el tiempo esperado")

    # 6) Cerrar pestaña y volver a la original
    driver.close()
    driver.switch_to.window(original)

