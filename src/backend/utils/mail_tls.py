"""Verifizierende Mail-TLS-Kontexte ohne Abhängigkeit von Build-Rechner-CA-Pfaden."""

import os
import ssl

import certifi


class MailTLSConfigurationError(Exception):
    """Der lokale CA-Speicher konnte nicht geladen werden."""


def create_mail_tls_context(*, public_cas: bool = True) -> ssl.SSLContext:
    """Systemvertrauen erhalten und öffentliche CAs auch im Sidecar bereitstellen.

    PyInstaller bündelt OpenSSL, dessen Default-Pfade auf die Python-Installation
    des Build-Rechners zeigen können. Das mitgelieferte certifi-Bundle wird
    deshalb zusätzlich geladen, nicht erst nach einem fehlgeschlagenen Handshake.
    Explizite SSL_CERT_FILE/SSL_CERT_DIR-Vorgaben werden nicht erweitert.
    Zertifikatsketten- und Hostnamenprüfung bleiben aktiv. Im ausdrücklich
    gewählten TOFU-Modus wird mit public_cas=False nur der bisherige
    Default-Kontext erstellt; die aufrufende Stelle übernimmt Pinning/Opt-in.
    """
    try:
        context = ssl.create_default_context()
        if (
            public_cas
            and "SSL_CERT_FILE" not in os.environ
            and "SSL_CERT_DIR" not in os.environ
        ):
            context.load_verify_locations(cafile=certifi.where())
    except OSError as error:
        raise MailTLSConfigurationError(
            "Der Zertifikatsspeicher von RechnungsFee konnte nicht geladen werden. "
            "Bitte prüfe die Installation und gegebenenfalls ausdrücklich konfigurierte CA-Pfade. "
            "Die Verbindung wurde vor der Anmeldung abgebrochen."
        ) from error
    return context


def certificate_verification_detail(
    protocol: str, host: str, error: ssl.SSLCertVerificationError
) -> str:
    """Fehlenden lokalen CA-Speicher nicht mit einem ungültigen Server verwechseln."""
    reason = getattr(error, "verify_message", None) or "Unbekannter Zertifikatsfehler"
    return (
        f"Zertifikatsprüfung fehlgeschlagen: RechnungsFee konnte das Zertifikat des "
        f"{protocol}-Servers „{host}“ nicht verifizieren. Ursache: {reason}. "
        "Prüfe Servername, Systemdatum und den Zertifikatsspeicher von RechnungsFee. "
        "Auch ein unvollständiges oder ungültiges Serverzertifikat kann die Ursache sein. "
        "Die Verbindung wurde vor der Anmeldung abgebrochen."
    )
