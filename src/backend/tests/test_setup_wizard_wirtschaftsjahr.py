"""
CLAUDE.md-Pflichtcheck: Änderungen an unternehmen-Schema/Endpoint/Formular erfordern einen
Setup-Wizard-Testlauf mit leerer Datenbank. Issue #404 fügt zwei neue unternehmen-Felder hinzu
(wirtschaftsjahr_abweichend_aktiv, geschaeftsjahr_beginn wird jetzt genutzt) - beide bewusst
NICHT im Wizard (SetupWizard.tsx/StepSteuern.tsx) sichtbar, analog zu den anderen Opt-in-Flags.

Dieser Test bildet exakt die Payload nach, die SetupWizard.tsx::saveMutation an
POST /api/unternehmen sendet (siehe createUnternehmen(...)-Aufruf dort) - ohne die beiden neuen
Felder, da der Wizard sie nicht kennt - und prüft, dass der Endpunkt trotzdem fehlerfrei
durchläuft und beide Felder korrekt auf ihren sicheren Default fallen.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.schemas import UnternehmenCreate
from api.unternehmen import create_unternehmen
from database.connection import Base


def test_wizard_payload_ohne_wirtschaftsjahr_felder_erzeugt_sichere_defaults(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'leer.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    # Exakte Payload-Form aus SetupWizard.tsx::saveMutation (formData + fixe Defaults),
    # keines der beiden neuen Wirtschaftsjahr-Felder wird vom Wizard gesendet.
    daten = UnternehmenCreate(
        firmenname="Testbetrieb", strasse="Musterweg", hausnummer="1",
        plz="12345", ort="Musterstadt", land="DE",
        ist_kleinunternehmer=False, bezieht_transferleistungen=False,
        versteuerungsart="ist", kontenrahmen="SKR03",
        taetigkeitsart="freiberuflich", rechtsform="Einzelunternehmer",
        iban="", bic="", bank_name="",
    )

    ergebnis = create_unternehmen(daten, db=db)

    assert ergebnis.geschaeftsjahr_beginn == 1
    assert ergebnis.wirtschaftsjahr_abweichend_aktiv is False
    db.close()
