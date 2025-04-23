# scraper_sentencias_main.py
from helpers import (
    init_driver,
    navigate_to_sentencias,
    go_to_page,
    parse_cards,
    extract_card_info,
    wait_for_new_page,
    extract_radicado,
    download_pdf
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import json
import time
import os


def main():
    # 1) Creamos carpeta raíz y pasamos a init_driver
    carpeta_raiz = "descargas_tsauro"
    os.makedirs(carpeta_raiz, exist_ok=True)

    driver = init_driver(headless=True, download_dir=carpeta_raiz)
    wait = WebDriverWait(driver, 30, poll_frequency=3)
    driver.get("https://tesauro.supersociedades.gov.co/results#/")

    navigate_to_sentencias(driver, wait)

   
    results = []
    for page in range(1, 3):
        if page > 1:
            cards_before = parse_cards(driver)
            old_first = None
            if cards_before:
                try:
                    old_first = extract_card_info(cards_before[0], wait)[1]
                except Exception:
                    old_first = None

            go_to_page(driver, wait, page)

            if old_first:
                try:
                    wait_for_new_page(driver, wait, old_first)
                except TimeoutException as e:
                    print(f"Advertencia: {e}")
            else:
                wait.until(lambda d: len(parse_cards(d)) >= 5)

        cards = parse_cards(driver)
        print(f"Página {page} - Tarjetas encontradas: {len(cards)}")

        for idx, card in enumerate(cards, start=1):
            try:
                 # Extrae datos básicos
                title, process, date, theme = extract_card_info(card, wait)

                # 1) click en la tarjeta para abrir el panel lateral
                card.click()

                # 2) extrae el número de radicado
                numero_radicado = extract_radicado(wait)

                # 3) Crear carpeta dónde se guardarán los respectivos PDF
                ruta_pdf = os.path.join(carpeta_raiz, theme)
                os.makedirs(ruta_pdf, exist_ok=True)

                # 4) Nombre de archivo
                nombre_pdf = f"Superintendencia de Sociedades-Sentencia nro {numero_radicado} del {date}.pdf"

                # 5) Descargar el PDF
                download_pdf(driver, wait, ruta_pdf, nombre_pdf)


            except Exception as e:
                print(f"Error tarjeta {idx} página {page}: {e}")
                continue

            record = {
                "page": page,
                "card": idx,
                "title": title,
                "process_number": process,
                "date": date,
                "theme": theme,
                "numero_radicado": numero_radicado,
                "name_PDF": nombre_pdf
            }
            results.append(record)
            with open("results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(1)

    driver.quit()


if __name__ == "__main__":
    main()