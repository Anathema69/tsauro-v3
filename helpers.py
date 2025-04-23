# helpers.py
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException


def init_driver(headless=True):
    """
    Inicializa el WebDriver de Chrome en modo headless.
    """
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
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
