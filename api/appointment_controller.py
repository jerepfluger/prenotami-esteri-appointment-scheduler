import json
import time

from flask import request
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from config.config import settings as config_file
from helpers.retry_function import retry_on_exception
from webdrivers.webdriver import WebDriver
from . import routes


@routes.route("/prenotami-esteri/schedule_appointment", methods=["POST"])
def schedule_appointment_controller():
    appointment_data = json.loads(request.data)
    # FIXME: Sanitize data here
    try:
        driver = WebDriver().acquire(config_file.crawling.appointment_controller.webdriver_type)
        driver.maximize_window()
        driver.get('https://prenotami.esteri.it/')
        # Waiting for login page to be fully loaded
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'login-email')))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # Complete username field
        username_input = driver.find_element(By.ID, 'login-email')
        username_input.send_keys(appointment_data['user'])
        # Complete password field
        password_input = driver.find_element(By.ID, 'login-password')
        password_input.send_keys(appointment_data['pass'])
        password_input.send_keys(Keys.ENTER)

        # Waiting for user area page to be fully loaded
        # FIXME: I should set here a retry system
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'advanced')))
        get_appointment_with_retry(appointment_data, driver)

        search_appointment_or_raise_exception(driver)

        # Accept appointment
        accept_appointment_button = driver.find_element(By.ID, 'btnPrenotaNoOtp')
        driver.execute_script("arguments[0].click();", accept_appointment_button)

        # Accept and close
        # WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'btnStampa')))

        # TODO: We need to save this to send it to the client
        # driver.save_full_page_screenshot()

    except Exception as ex:
        print(ex)
        try:
            driver.close()
            driver.quit()
        except NameError:
            pass


@retry_on_exception(max_attempts=5)
def get_appointment_with_retry(appointment_data, driver):
    driver.get('https://prenotami.esteri.it/Language/ChangeLanguage?lang=13')
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'advanced')))
    driver.get('https://prenotami.esteri.it/Services')

    # Waiting for prenotami tab to be fully loaded
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, 'dataTableServices')))
    select_appointment(driver, appointment_data['appointment_type'])

    complete_appointment_details(driver, appointment_data)

    privacy_check_box = driver.find_element(By.ID, 'PrivacyCheck')
    driver.execute_script("arguments[0].click();", privacy_check_box)

    next_button = driver.find_element(By.ID, 'btnAvanti')
    driver.execute_script("arguments[0].click();", next_button)

    driver.switch_to.alert.accept()

    check_calendar_or_raise_exception(driver)


def search_appointment_or_raise_exception(driver):
    loop = 0
    while True:
        if loop > 11:
            raise Exception('No appointments for next year')
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, './/td[@class="day availableDay"]')))
            available_date = driver.find_element(By.XPATH, './/td[@class="day availableDay"]')
            driver.execute_script("arguments[0].click();", available_date)
            break
        except TimeoutException:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, './/span[@title="Next Month"]')))
                next_month_button = driver.find_element(By.XPATH, './/span[@title="Next Month"]')
                driver.execute_script("arguments[0].click();", next_month_button)
                loop += 1
            except NoSuchElementException:
                raise NeedsRetryException('Unable to pick appointment')


def check_calendar_or_raise_exception(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, './/section[@class="calendario"]')))
    except NoSuchElementException:
        raise NeedsRetryException('No available appointments')


# TODO: Maybe we could add new appointment types
# FIXME: There needs to be an appointment validator. Not every appointment is available for any city
def select_appointment(driver, APPOINTMENT):
    if APPOINTMENT == 'PASAPORTE':
        return driver.get('https://prenotami.esteri.it/Services/Booking/104')
    if APPOINTMENT == 'CIUDADANIA DESCENDENCIA':
        return driver.get('https://prenotami.esteri.it/Services/Booking/340')
    if APPOINTMENT == 'CIUDADANIA PADRES':
        return driver.get('https://prenotami.esteri.it/Services/Booking/339')
    if APPOINTMENT == 'VISADOS':
        return driver.get('https://prenotami.esteri.it/Services/Booking/753')
    if APPOINTMENT == 'CARTA DE IDENTIDAD':
        return driver.get('https://prenotami.esteri.it/Services/Booking/645')
    raise Exception('Unknown appointment type')


def return_full_marital_status(marital_status):
    marital_status = marital_status.upper()
    if marital_status == 'CASADO' or marital_status == 'CASADA' or marital_status == 'CASADO/A':
        return 'Casado/a'
    if marital_status == 'DIVORCIADO' or marital_status == 'DIVORCIADA' or marital_status == 'DIVORCIADO/A':
        return 'Divorciado/a'
    if marital_status == 'VIUDO' or marital_status == 'VIUDA' or marital_status == 'VIUDO/A':
        return 'Viudo/a'
    if marital_status == 'SOLTERO' or marital_status == 'SOLTERA' or marital_status == 'SOLTERO/A':
        return 'Soltero/a'
    if marital_status == 'SEPARADO' or marital_status == 'SEPARADA' or marital_status == 'SEPARADO/A':
        return 'Separado/a'
    if marital_status == 'UNION CIVIL':
        return 'Unido/a civilmente'
    if marital_status == 'SEPARADO U/C' or marital_status == 'SEPARADA U/C' or marital_status == 'SEPARADO/A U/C':
        return 'Separado/a de Un. Civ.'
    if marital_status == 'DIVORCIADO U/C' or marital_status == 'DIVORCIADA U/C' or marital_status == 'DIVORCIADO/A U/C':
        return 'Divorciado/a de Un. Civ.'
    if marital_status == 'VIUDO U/C' or marital_status == 'VIUDA U/C' or marital_status == 'VIUDO/A U/C':
        return 'Viudo/a de Un. Civ.'
    raise Exception('Marital status not present in Prenotami availability list')


def return_full_parental_relationship(parental_relationship):
    if parental_relationship == 'Concubino':
        return 'Concubino'
    if parental_relationship == 'Conyuge':
        return 'Conyuge'
    if parental_relationship == 'Conyuge divorciado':
        return 'Conyuge divorciado'
    if parental_relationship == 'Conyuge separado':
        return 'Conyuge separado'
    if parental_relationship == 'Hermano' or parental_relationship == 'Hermana' or parental_relationship == 'Hermano/Hermana':
        return 'Hermano/Hermana'
    if parental_relationship == 'Hijo de otro conyuge':
        return 'Hijo de otro conyuge'
    if parental_relationship == 'Hijo' or parental_relationship == 'Hija' or parental_relationship == 'Hijo/a':
        return 'Hijo/a'
    if parental_relationship == 'Menor en tenencia':
        return 'Menor en tenencia'
    if parental_relationship == 'Nieto':
        return 'Nieto'
    if parental_relationship == 'Padre' or parental_relationship == 'Madre' or parental_relationship == 'Padre/Madre':
        return 'Padre/Madre'
    if parental_relationship == 'Suegro' or parental_relationship == 'Suegra' or parental_relationship == 'Suegro/Suegra':
        return 'Suegro/Suegra'
    if parental_relationship == 'Yerno' or parental_relationship == 'Nuera' or parental_relationship == 'Yerno/Nuera':
        return 'Yerno/Nuera'
    raise Exception('Parental relationship not present in Prenotami availability list')


def complete_passport_appointment_data(driver, appointment_data):
    # Waiting for appointment page to be fully loaded
    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.XPATH, './/select[@id="typeofbookingddl"]/option[text()="Reserva multiple"]')))

    if appointment_data.get('multiple_appointment'):
        multiple_appointment_select = driver.find_element(By.ID, 'typeofbookingddl')
        driver.execute_script("arguments[0].click();", multiple_appointment_select)
        multiple_appointment_select.send_keys('Reserva multiple')

        if appointment_data['additional_people_amount'] > 4:
            raise Exception('Additional people amount cannot be greater than 4')
        additional_people_input = driver.find_element(By.ID, 'ddlnumberofcompanions')
        driver.execute_script("arguments[0].click();", additional_people_input)
        additional_people_input = Select(driver.find_element(By.ID, 'ddlnumberofcompanions'))
        additional_people_input.select_by_visible_text(str(appointment_data['additional_people_amount']))

    address_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_0___testo')
    address_input.send_keys(appointment_data['address'])

    # FIXME: We need to set a validator for this option
    have_kids_select = driver.find_element(By.ID, 'ddls_1')
    driver.execute_script("arguments[0].click();", have_kids_select)
    have_kids_select.send_keys(appointment_data['have_kids'].capitalize())

    marital_status = driver.find_element(By.ID, 'ddls_2')
    driver.execute_script("arguments[0].click();", marital_status)
    marital_status.send_keys(return_full_marital_status(appointment_data['marital_status']))

    have_expired_passport = driver.find_element(By.ID, 'ddls_3')
    driver.execute_script("arguments[0].click();", have_expired_passport)
    have_expired_passport.send_keys(appointment_data['is_passport_expired'].capitalize())

    amount_minor_kids_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_4___testo')
    amount_minor_kids_input.send_keys(appointment_data['amount_minor_kids'])

    if appointment_data.get('multiple_appointment'):
        for index, companion_data in enumerate(appointment_data['additional_people_data']):
            last_name_input = driver.find_element(By.ID, 'Accompagnatori_{}__CognomeAccompagnatore'.format(index))
            last_name_input.send_keys(companion_data['last_name'])

            first_name_input = driver.find_element(By.ID, 'Accompagnatori_{}__NomeAccompagnatore'.format(index))
            first_name_input.send_keys(companion_data['first_name'])

            birthdate_input = driver.find_element(By.ID, 'Accompagnatori_{}__DataNascitaAccompagnatore'.format(index))
            birthdate_input.send_keys(companion_data['birthdate'])

            parental_relationship_select = driver.find_element(By.ID, 'TypeOfRelationDDL{}'.format(index))
            parental_relationship_select.send_keys(return_full_parental_relationship(companion_data['relationship']))

            have_kids_select = driver.find_element(By.ID, 'ddlsAcc_{}_0'.format(index))
            driver.execute_script("arguments[0].click();", have_kids_select)
            have_kids_select.send_keys(companion_data['have_kids'].capitalize())

            marital_status_select = driver.find_element(By.ID, 'ddlsAcc_{}_1'.format(index))
            driver.execute_script("arguments[0].click();", marital_status_select)
            marital_status_select.send_keys(return_full_marital_status(companion_data['marital_status']))

            address_input = driver.find_element(By.ID, 'Accompagnatori_{}__DatiAddizionaliAccompagnatore_2___testo'.format(index))
            address_input.send_keys(companion_data['address'])


def complete_family_citizenship_data(driver, appointment_data):
    marital_status = Select(driver.find_element(By.ID, 'ddls_0'))
    marital_status.select_by_visible_text(return_full_marital_status(appointment_data['marital_status']))

    address_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_1___testo')
    address_input.send_keys(appointment_data['address'])

    amount_minor_kids_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_2___testo')
    amount_minor_kids_input.send_keys(appointment_data['amount_minor_kids'])


def sanitize_appointment_reason(appointment_reason):
    valid_reasons = {'Negocios', 'Tratamientos médicos', 'Competencia deportiva', 'Trabajo independiente',
                     'Trabajo subordinado', 'Misión', 'Motivos religiosos', 'Investigación', 'Estudio', 'Tránsito',
                     'Transporte', 'Turismo', 'Turista - Visita familiares/amigos', 'Reingresso', 'Altro'}
    if appointment_reason not in valid_reasons:
        raise Exception('Invalid appointment reason')

    return appointment_reason


def complete_visa_appointment_data(driver, appointment_data):
    # FIXME: Need to add multiple appointment support
    passport_expiry_date_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_0___data')
    # Format need to be "yyyy-mm-dd"
    passport_expiry_date_input.send_keys(appointment_data['passport_expiry_date'])

    travel_reason = Select(driver.find_element(By.ID, 'ddls_1'))
    travel_reason.select_by_visible_text(sanitize_appointment_reason(appointment_data['travel_reason'].capitalize()))


def complete_id_card_data(driver, appointment_data):
    # FIXME: Need to add multiple appointment support
    address_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_0___testo')
    address_input.send_keys(appointment_data['address'])
    have_kids_select = Select(driver.find_element(By.ID, 'ddls_1'))
    time.sleep(0.1)
    have_kids_select.select_by_visible_text(appointment_data['have_kids'].capitalize())
    amount_minor_kids_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_2___testo')
    amount_minor_kids_input.send_keys(appointment_data['amount_minor_kids'])
    height_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_3___testo')
    height_input.send_keys(appointment_data['height'])
    zip_code_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_4___testo')
    zip_code_input.send_keys(appointment_data['zip_code'])
    other_citizenships_input = driver.find_element(By.ID, 'DatiAddizionaliPrenotante_5___testo')
    other_citizenships_input.send_keys(appointment_data['other_citizenships'].capitalize())
    marital_status_input = Select(driver.find_element(By.ID, 'ddls_6'))
    marital_status_input.select_by_visible_text(return_full_marital_status(appointment_data['marital_status']))


def complete_appointment_details(driver, appointment_data):
    if appointment_data['appointment_type'] == 'PASAPORTE':
        complete_passport_appointment_data(driver, appointment_data)
    if appointment_data['appointment_type'] == 'CIUDADANIA PADRES':
        complete_family_citizenship_data(driver, appointment_data)
    if appointment_data['appointment_type'] == 'VISADOS':
        complete_visa_appointment_data(driver, appointment_data)
    if appointment_data['appointment_type'] == 'CARTA DE IDENTIDAD':
        complete_id_card_data(driver, appointment_data)
    # There's no need for completing any data for descendent citizenship appointment


class NeedsRetryException(Exception):
    def __init__(self, message):
        self.message = message
