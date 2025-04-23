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
    # Espera a que el botón se marque como seleccionado
    selected_xpath = f"//button[@aria-current='true' and @aria-label='page {page}']"
    wait.until(EC.presence_of_element_located((By.XPATH, selected_xpath)))


def parse_cards(driver):
    """
    Devuelve la lista de elementos de tarjeta en la página actual.
    """
    return driver.find_elements(By.CSS_SELECTOR, "div.result_card")


def extract_card_info(card, wait, retries=3):
    """
    Extrae el título y número de proceso de una tarjeta WebElement, gestionando stale elements.
    """
    for attempt in range(retries):
        try:
            title = card.find_element(By.CSS_SELECTOR, "span.card__title").text.strip()
            process = card.find_element(
                By.XPATH,
                ".//div[@class='card__info-title' and normalize-space(text())='Número de proceso:']"
                "/following-sibling::div[@class='card__info-value']"
            ).text.strip()
            return title, process
        except StaleElementReferenceException:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            else:
                raise
        except NoSuchElementException as e:
            raise


def wait_for_new_page(driver, wait, old_first_process, min_cards=5, timeout=30):
    """
    Espera a que la nueva página cargue completamente: suficientes tarjetas y proceso distinto al anterior.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            cards = parse_cards(driver)
            if len(cards) >= min_cards:
                _, process = extract_card_info(cards[0], wait)
                if process != old_first_process:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise TimeoutException(f"La página no cargó correctamente (primer proceso sigue {old_first_process})")