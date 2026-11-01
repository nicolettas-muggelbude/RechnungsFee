"""Mail-TLS muss auch ohne die CA-Pfade des Build-Rechners sicher funktionieren."""

import socket
import ssl
import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from types import SimpleNamespace

import certifi
import pytest
from api import mail, postfach
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from database.models import Unternehmen
from fastapi import HTTPException
from utils.mail_tls import create_mail_tls_context


@pytest.fixture
def certificates(tmp_path):
    now = datetime.now(UTC)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Mail TLS Test CA")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(ca_name)
        .issuer_name(ca_name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(False, False, False, False, False, True, True, False, False),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    ca_path = tmp_path / "ca.pem"
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))

    def issue(host="localhost", expired=False):
        key = ec.generate_private_key(ec.SECP256R1())
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)]))
            .issuer_name(ca_name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=2))
            .not_valid_after(
                now - timedelta(days=1) if expired else now + timedelta(days=7)
            )
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None), critical=True
            )
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(host)]), critical=False
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                critical=False,
            )
            .sign(ca_key, hashes.SHA256())
        )
        cert_path = tmp_path / f"{host}-{expired}.pem"
        key_path = tmp_path / f"{host}-{expired}.key"
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        return cert_path, key_path

    return ca_path, issue


@contextmanager
def smtp_server(cert_path, key_path, implicit_tls):
    """Echter lokaler SMTP/TLS-Server; merkt, ob AUTH vor TLS-Prüfung ankommt."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(cert_path), str(key_path))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(5)
    state = SimpleNamespace(
        port=listener.getsockname()[1], authenticated=False, delivered=False, errors=[]
    )

    def serve():
        conn = None
        stream = None
        try:
            conn, _ = listener.accept()
            conn.settimeout(5)
            if implicit_tls:
                conn = context.wrap_socket(conn, server_side=True)
            stream = conn.makefile("rwb")
            stream.write(b"220 localhost test\r\n")
            stream.flush()
            while True:
                line = stream.readline()
                if not line:
                    break
                command = line.split(None, 1)[0].upper()
                if command == b"EHLO":
                    stream.write(b"250-localhost\r\n250-STARTTLS\r\n250 AUTH PLAIN\r\n")
                elif command == b"STARTTLS":
                    stream.write(b"220 Ready\r\n")
                    stream.flush()
                    stream.close()
                    conn = context.wrap_socket(conn, server_side=True)
                    stream = conn.makefile("rwb")
                    continue
                elif command == b"AUTH":
                    state.authenticated = True
                    stream.write(b"235 Authenticated\r\n")
                elif command == b"DATA":
                    stream.write(b"354 Continue\r\n")
                    stream.flush()
                    while True:
                        data_line = stream.readline()
                        if data_line in (b".\r\n", b""):
                            break
                    state.delivered = True
                    stream.write(b"250 Delivered\r\n")
                elif command == b"QUIT":
                    stream.write(b"221 Bye\r\n")
                    stream.flush()
                    break
                else:
                    stream.write(b"250 OK\r\n")
                stream.flush()
        except ssl.SSLError:
            # Erwartet, wenn der Client das Serverzertifikat ablehnt.
            pass
        except Exception as error:  # noqa: BLE001 - Threadfehler im Hauptthread prüfen.
            state.errors.append(error)
        finally:
            if stream is not None:
                stream.close()
            if conn is not None:
                conn.close()
            listener.close()

    worker = threading.Thread(target=serve, daemon=True)
    worker.start()
    try:
        yield state
    finally:
        worker.join(timeout=6)
        listener.close()
        assert not worker.is_alive(), "Lokaler SMTP-Testserver hängt"
        assert not state.errors, state.errors


def send(state, implicit_tls, settings=None, db=None):
    if settings is None:
        settings = Unternehmen(
            smtp_host="localhost",
            smtp_port=state.port,
            smtp_ssl=implicit_tls,
            smtp_user="test@example.invalid",
            smtp_passwort="synthetic-password",
            smtp_zertifikat_ignorieren=False,
        )
    else:
        settings.smtp_port = state.port
    message = MIMEMultipart()
    message.attach(MIMEText("Synthetic test message"))
    message["From"] = "test@example.invalid"
    mail._sende(settings, message, ["recipient@example.invalid"], db)


@pytest.mark.parametrize("implicit_tls", [False, True], ids=["starttls", "smtp_ssl"])
def test_public_bundle_works_without_build_machine_ca_paths(
    monkeypatch, certificates, implicit_tls
):
    ca_path, issue = certificates
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    # Simuliert fehlende OpenSSL-Default-Pfade, ohne lokale Zertifikate zu ändern.
    monkeypatch.setattr(
        ssl.SSLContext, "load_default_certs", lambda self, purpose: None
    )
    monkeypatch.setattr(certifi, "where", lambda: str(ca_path))
    with smtp_server(*issue(), implicit_tls=implicit_tls) as state:
        send(state, implicit_tls)
    assert state.authenticated
    assert state.delivered


@pytest.mark.parametrize("implicit_tls", [False, True], ids=["starttls", "smtp_ssl"])
@pytest.mark.parametrize("invalid", ["unknown_ca", "expired", "hostname"])
def test_invalid_certificates_are_rejected_before_authentication(
    monkeypatch, certificates, implicit_tls, invalid
):
    ca_path, issue = certificates
    monkeypatch.setenv(
        "SSL_CERT_FILE",
        str(ca_path) if invalid != "unknown_ca" else str(ca_path.parent / "absent.pem"),
    )
    monkeypatch.setenv("SSL_CERT_DIR", str(ca_path.parent / "absent-directory"))
    monkeypatch.setattr(certifi, "where", lambda: str(ca_path))
    with smtp_server(
        *issue(
            host="wrong.example.invalid" if invalid == "hostname" else "localhost",
            expired=invalid == "expired",
        ),
        implicit_tls=implicit_tls,
    ) as state, pytest.raises(
        HTTPException, match="Zertifikatsprüfung fehlgeschlagen"
    ) as error:
        send(state, implicit_tls)
    assert "Zertifikatsspeicher" in error.value.detail
    assert "Ursache:" in error.value.detail
    assert "synthetic-password" not in error.value.detail
    assert "verwendet ein nicht vertrauenswürdiges Zertifikat" not in error.value.detail
    assert not state.authenticated
    assert not state.delivered


@pytest.mark.parametrize("implicit_tls", [False, True], ids=["starttls", "smtp_ssl"])
def test_explicit_ca_file_remains_usable(monkeypatch, certificates, implicit_tls):
    ca_path, issue = certificates

    def no_bundle():
        raise AssertionError("Explizite CA-Konfiguration darf nicht erweitert werden")

    monkeypatch.setattr(certifi, "where", no_bundle)
    monkeypatch.setenv("SSL_CERT_FILE", str(ca_path))
    monkeypatch.setenv("SSL_CERT_DIR", str(ca_path.parent / "absent-directory"))
    with smtp_server(*issue(), implicit_tls=implicit_tls) as state:
        send(state, implicit_tls)
    assert state.delivered


@pytest.mark.parametrize(
    "implicit_tls", [False, True], ids=["imap_starttls", "imap_ssl"]
)
def test_imap_also_loads_public_bundle_without_default_ca_paths(
    monkeypatch, certificates, implicit_tls
):
    ca_path, _ = certificates
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    monkeypatch.setattr(
        ssl.SSLContext, "load_default_certs", lambda self, purpose: None
    )
    monkeypatch.setattr(certifi, "where", lambda: str(ca_path))

    class LocalIMAP:
        def __init__(self, host, port, ssl_context=None, timeout=None):
            self.context = ssl_context

        def starttls(self, ssl_context):
            self.context = ssl_context

        def login(self, user, password):
            pass

        def capability(self):
            return "OK", [b"IMAP4rev1"]

    monkeypatch.setattr(postfach.imaplib, "IMAP4_SSL", LocalIMAP)
    monkeypatch.setattr(postfach.imaplib, "IMAP4", LocalIMAP)
    settings = Unternehmen(
        imap_host="localhost",
        imap_port=993 if implicit_tls else 143,
        imap_ssl=implicit_tls,
        imap_user="test@example.invalid",
        imap_passwort="synthetic-password",
        imap_zertifikat_ignorieren=False,
    )
    connection = postfach._verbinde(settings, None)
    assert connection.context.cert_store_stats()["x509_ca"] == 1
    assert connection.context.verify_mode == ssl.CERT_REQUIRED
    assert connection.context.check_hostname is True


@pytest.mark.parametrize("implicit_tls", [False, True], ids=["starttls", "smtp_ssl"])
def test_system_trusted_internal_ca_is_retained(
    monkeypatch, certificates, implicit_tls
):
    ca_path, issue = certificates
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    monkeypatch.setattr(
        ssl.SSLContext,
        "load_default_certs",
        lambda self, purpose: self.load_verify_locations(cafile=str(ca_path)),
    )
    with smtp_server(*issue(), implicit_tls=implicit_tls) as state:
        send(state, implicit_tls)
    assert state.delivered


@pytest.mark.parametrize("variable", ["SSL_CERT_FILE", "SSL_CERT_DIR"])
@pytest.mark.parametrize("value", ["", "missing-custom-store"])
def test_explicit_ca_policy_is_not_silently_broadened(
    monkeypatch, certificates, variable, value
):
    ca_path, _ = certificates
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    monkeypatch.setenv(variable, value)
    monkeypatch.setattr(
        ssl.SSLContext, "load_default_certs", lambda self, purpose: None
    )
    monkeypatch.setattr(certifi, "where", lambda: str(ca_path))
    context = create_mail_tls_context()
    assert context.cert_store_stats()["x509_ca"] == 0
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.parametrize("protocol", ["smtp", "imap"])
@pytest.mark.parametrize("implicit_tls", [False, True])
@pytest.mark.parametrize("broken", ["missing", "invalid"])
def test_broken_public_bundle_is_reported_before_connecting(
    monkeypatch, tmp_path, protocol, implicit_tls, broken
):
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    bundle = tmp_path / "broken-public-cas.pem"
    if broken == "invalid":
        bundle.write_text("This is not a certificate bundle")
    monkeypatch.setattr(certifi, "where", lambda: str(bundle))
    with pytest.raises(HTTPException) as error:
        if protocol == "smtp":
            send(SimpleNamespace(port=1), implicit_tls)
        else:
            settings = Unternehmen(
                imap_host="localhost",
                imap_port=1,
                imap_ssl=implicit_tls,
                imap_user="test@example.invalid",
                imap_passwort="synthetic-password",
                imap_zertifikat_ignorieren=False,
            )
            postfach._verbinde(settings, None)
    assert error.value.status_code == 400
    assert "Zertifikatsspeicher" in error.value.detail
    assert "synthetic-password" not in error.value.detail
    assert str(bundle) not in error.value.detail


@pytest.mark.parametrize("implicit_tls", [False, True], ids=["starttls", "smtp_ssl"])
def test_smtp_tofu_remains_independent_of_public_bundle_and_checks_pin(
    monkeypatch, certificates, implicit_tls
):
    ca_path, issue = certificates
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    monkeypatch.setattr(
        certifi, "where", lambda: str(ca_path.parent / "missing-bundle.pem")
    )
    settings = Unternehmen(
        smtp_host="localhost",
        smtp_ssl=implicit_tls,
        smtp_user="test@example.invalid",
        smtp_passwort="synthetic-password",
        smtp_zertifikat_ignorieren=True,
        smtp_zertifikat_fingerprint=None,
    )
    commits = []
    db = SimpleNamespace(commit=lambda: commits.append("commit"))
    first_certificate = issue()
    with smtp_server(*first_certificate, implicit_tls=implicit_tls) as first:
        send(first, implicit_tls, settings, db)
    fingerprint = settings.smtp_zertifikat_fingerprint
    assert fingerprint
    assert first.authenticated
    assert len(commits) == 1
    with smtp_server(*first_certificate, implicit_tls=implicit_tls) as same:
        send(same, implicit_tls, settings, db)
    assert same.authenticated
    assert settings.smtp_zertifikat_fingerprint == fingerprint
    assert len(commits) == 1
    with smtp_server(
        *issue(host="changed.example.invalid"), implicit_tls=implicit_tls
    ) as changed, pytest.raises(HTTPException, match="Zertifikat.*geändert"):
        send(changed, implicit_tls, settings, db)
    assert not changed.authenticated
    assert not changed.delivered
    assert settings.smtp_zertifikat_fingerprint == fingerprint
    assert len(commits) == 1


@pytest.mark.parametrize(
    "implicit_tls", [False, True], ids=["imap_starttls", "imap_ssl"]
)
def test_imap_tofu_remains_independent_of_public_bundle_and_checks_pin(
    monkeypatch, certificates, implicit_tls
):
    ca_path, issue = certificates
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)
    monkeypatch.setattr(
        certifi, "where", lambda: str(ca_path.parent / "missing-bundle.pem")
    )
    first_certificate, _ = issue()
    current_der = x509.load_pem_x509_certificate(
        first_certificate.read_bytes()
    ).public_bytes(serialization.Encoding.DER)
    logins = []
    contexts = []

    class PinningIMAP:
        error = postfach.imaplib.IMAP4.error

        def __init__(self, host, port, ssl_context=None, timeout=None):
            self.sock = SimpleNamespace(
                getpeercert=lambda binary_form=False: current_der
            )
            if ssl_context is not None:
                contexts.append(ssl_context)

        def starttls(self, ssl_context):
            contexts.append(ssl_context)

        def login(self, user, password):
            logins.append("login")

        def capability(self):
            return "OK", [b"IMAP4rev1"]

    monkeypatch.setattr(postfach.imaplib, "IMAP4_SSL", PinningIMAP)
    monkeypatch.setattr(postfach.imaplib, "IMAP4", PinningIMAP)
    settings = Unternehmen(
        imap_host="localhost",
        imap_ssl=implicit_tls,
        imap_user="test@example.invalid",
        imap_passwort="synthetic-password",
        imap_zertifikat_ignorieren=True,
        imap_zertifikat_fingerprint=None,
    )
    commits = []
    db = SimpleNamespace(commit=lambda: commits.append("commit"))
    postfach._verbinde(settings, db)
    fingerprint = settings.imap_zertifikat_fingerprint
    assert fingerprint
    assert logins == ["login"]
    postfach._verbinde(settings, db)
    assert logins == ["login", "login"]
    changed_certificate, _ = issue(host="changed.example.invalid")
    current_der = x509.load_pem_x509_certificate(
        changed_certificate.read_bytes()
    ).public_bytes(serialization.Encoding.DER)
    with pytest.raises(HTTPException, match="Zertifikat.*geändert"):
        postfach._verbinde(settings, db)
    assert logins == ["login", "login"]
    assert settings.imap_zertifikat_fingerprint == fingerprint
    assert len(commits) == 1
    assert all(
        context.verify_mode == ssl.CERT_NONE and not context.check_hostname
        for context in contexts
    )
