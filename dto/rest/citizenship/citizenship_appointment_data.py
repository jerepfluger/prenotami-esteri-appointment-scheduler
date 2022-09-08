from dto.rest.citizenship.citizenship_client_appointment_data import CitizenshipData
from dto.rest.login_credentials import LoginCredentials


class CitizenshipAppointmentData:
    def __init__(self, client_login: LoginCredentials, appointment_data: CitizenshipData, unlimited_wait=False):
        self.client_login = client_login
        self.appointment_data = appointment_data
        self.unlimited_wait = unlimited_wait
